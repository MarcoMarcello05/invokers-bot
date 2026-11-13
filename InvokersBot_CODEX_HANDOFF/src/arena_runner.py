"""Arena integration sprint runner. Dry-run by default; no GUI or implicit live mode."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import time

from user_config import UserConfig, default_config_path
from failure_memory import FailureMemory
from arena_autopilot import ArenaAutopilot
from arena_snapshot import ArenaSnapshotSource


def validate_live_preflight(report_path, config, profile_path, profile, now=None):
    from arena_windows import profile_fingerprint
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    now = time.time() if now is None else now
    if report.get('mode') != 'dry' or report.get('status') != 'WOULD_START_BATTLE' or report.get('preflight_passed') is not True:
        raise ValueError('A successful navigation-only dry-run report is required')
    age = now-report.get('created_at_epoch', 0)
    if not 0 <= age <= 300:
        raise ValueError('Preflight is expired (maximum five minutes)')
    if report.get('calibration_sha256') != profile_fingerprint(profile_path):
        raise ValueError('Calibration changed since preflight')
    if report.get('own_power') != config.arena_combat_power or report.get('game_root') != str(Path(config.game_root).resolve()):
        raise ValueError('Power/game root changed since preflight')
    if profile.get('operator_confirmed_auto_off') is not True:
        raise ValueError('Operator must confirm AUTO is OFF; bot never enables AUTO')
    if report.get('cost') != {'Arena_Token': 1}:
        raise ValueError('Arena token-only contract is unverified')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=default_config_path())
    parser.add_argument('--policy',type=Path,default=Path(__file__).with_name('autonomy_policy.json'))
    parser.add_argument('--root',type=Path)
    parser.add_argument('--arena-power',type=int)
    parser.add_argument('--calibration',type=Path)
    parser.add_argument('--write-calibration',type=Path)
    parser.add_argument('--init-config',action='store_true')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--live',action='store_true')
    mode.add_argument('--simulate',action='store_true')
    parser.add_argument('--navigate',action='store_true',help='Dry-run navigation/scroll/open-formation only; never start battle')
    parser.add_argument('--activate-arena-live',action='store_true')
    parser.add_argument('--preflight',type=Path)
    parser.add_argument('--cycles',type=int,default=1)
    parser.add_argument('--once',action='store_true',help='Compatibility alias for one bounded cycle')
    parser.add_argument('--max-snapshot-age',type=int,default=300)
    parser.add_argument('--free-refreshes',type=int,default=0)
    parser.add_argument('--output-dir',type=Path,default=default_config_path().parent/'arena_runs')
    args=parser.parse_args(argv)
    if args.live and (not args.activate_arena_live or not args.preflight):
        print('Live disabled: explicit --activate-arena-live and a fresh successful --preflight report are required.')
        return 2
    desktop=None; lock=None; owned_lock=False
    try:
        policy=json.loads(args.policy.read_text(encoding='utf-8'))
        if not isinstance(policy,dict):raise ValueError('Policy must be an object')
        resources=policy.get('resources',{})
        if not isinstance(resources,dict):raise ValueError('Resource policy must be an object')
        if resources.get('allow_gems') is not False or resources.get('allow_premium_spend') is not False:
            raise ValueError('Policy must explicitly keep gems and premium spending disabled')
        limits=policy.get('arena_autopilot',{})
        if not isinstance(limits,dict):raise ValueError('Arena limits must be an object')
        for name,default,maximum in [('ui_timeout',10,30),('battle_timeout',180,600),('snapshot_timeout',10,30)]:
            value=limits.get(name,default)
            if type(value) not in (int,float) or not 0 < value <= maximum:
                raise ValueError('Invalid bounded policy timeout: '+name)
        for name,default,maximum in [('max_cycles',10,10),('max_recovery',1,2),('max_free_refreshes',3,3),('max_scroll_steps',14,30)]:
            value=limits.get(name,default)
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError('Invalid bounded policy budget: '+name)
        if not 1 <= args.cycles <= 10 or not 0 <= args.free_refreshes <= 3:
            raise ValueError('Cycles must be 1..10; free refreshes 0..3')
        if args.cycles > limits.get('max_cycles',10) or args.free_refreshes > limits.get('max_free_refreshes',3):
            raise ValueError('Requested cycle/refresh count exceeds policy budget')
        if args.write_calibration:
            from arena_windows import DEFAULT_PROFILE
            with args.write_calibration.open('x',encoding='utf-8') as stream:
                json.dump(DEFAULT_PROFILE,stream,ensure_ascii=False,indent=2)
            print('Calibration example written; verify geometry/ROIs and AUTO-off observation on your PC.')
            return 0
        config=UserConfig.load(args.config)
        if args.root:config=replace(config,game_root=str(args.root))
        if args.arena_power is not None:config=replace(config,arena_combat_power=args.arena_power)
        if args.init_config:
            if args.config.exists():raise ValueError('Refusing to overwrite an existing UserConfig; edit it explicitly')
            config.save(args.config);print('UserConfig saved. No live action enabled.');return 0
        if args.simulate:
            from arena_simulation import SimulatedArena
            if config.arena_combat_power is None:config=replace(config,arena_combat_power=10000)
            desktop=SimulatedArena(config.arena_combat_power)
            source=desktop
            mode_name='simulation';armed=False
            memory=FailureMemory()
            profile=None
        else:
            if not args.calibration:raise ValueError('--calibration JSON is required for any real Windows screen access')
            from arena_windows import WindowsArenaDesktop, load_profile
            profile=load_profile(args.calibration)
            if profile['max_scroll_steps'] > limits.get('max_scroll_steps',14):
                raise ValueError('Calibration scroll budget exceeds policy')
            config.validate()
            armed=False
            if args.live:
                validate_live_preflight(args.preflight,config,args.calibration,profile)
                armed=True
            # One physical input session per account; crash locks are never removed blindly.
            args.output_dir.mkdir(parents=True,exist_ok=True)
            lock=args.output_dir/'arena.lock'
            descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            owned_lock=True
            with os.fdopen(descriptor,'w') as stream:stream.write(str(os.getpid()))
            desktop=WindowsArenaDesktop(profile,allow_navigation=args.navigate or args.live,
                                         allow_battle=args.live and armed,stop_file=args.output_dir/'STOP')
            source=ArenaSnapshotSource(config,args.max_snapshot_age)
            mode_name='live' if args.live else 'dry'
            memory=FailureMemory(args.output_dir/'failure_memory.json')
        config.validate()
        run_dir=args.output_dir/('run-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns())[-6:])
        pilot=ArenaAutopilot(source,desktop,config,memory,run_dir,mode=mode_name,
                             navigate=args.navigate,live_armed=armed,cycles=1 if args.once else args.cycles,
                             max_refreshes=args.free_refreshes,
                             max_recovery=limits.get('max_recovery',1),
                             ui_timeout=limits.get('ui_timeout',10),
                             battle_timeout=limits.get('battle_timeout',180),
                             snapshot_timeout=limits.get('snapshot_timeout',10))
        report=pilot.run()
        report.update(created_at_epoch=time.time(),game_root=str(Path(config.game_root).resolve()))
        if args.calibration:
            from arena_windows import profile_fingerprint
            report['calibration_sha256']=profile_fingerprint(args.calibration)
        (run_dir/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'status':report['status'],'completed_cycles':report['completed_cycles'],
                          'code':report.get('code'),'report':str(run_dir/'report.json')},ensure_ascii=False))
        return 0 if report['status'] in ('COMPLETED','DRY_RUN','WOULD_START_BATTLE') else 1
    except (OSError,ValueError,RuntimeError) as error:
        print('Arena stopped without enabling other actors: '+str(error),file=sys.stderr)
        return 2
    finally:
        if desktop is not None and hasattr(desktop,'close'):desktop.close()
        if owned_lock and lock is not None:lock.unlink(missing_ok=True)


if __name__=='__main__':raise SystemExit(main())
