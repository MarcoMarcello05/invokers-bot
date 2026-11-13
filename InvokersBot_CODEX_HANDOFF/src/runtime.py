"""Read-only orchestration: capture -> GameState -> Planner -> reviewable plan.

All production action handlers are disabled. Simulation belongs to Actor.simulate
and the regression harness; --once/automation never grants click permission.
"""
import argparse
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from failure_memory import FailureMemory, FailureMemoryError
from actor import Actor
from game_state import build_game_state
from memorypack import DecodeError
from planner import Planner, available, campaign_target
from user_config import ConfigError, UserConfig, default_config_path


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name+'.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def seed_campaign_defeats(state, config, memory, now):
    """Record an observed defeat once. Reading it again must not reset its baseline."""
    heroes = available(state, 'heroes', [])
    known = {hero['inventory_id'] for hero in heroes}
    if len(config.main_six_ids) != 6 or not set(config.main_six_ids) <= known:
        return
    for row in available(state, 'campaign', {}).get('level_stats', []):
        if row['area'] == 1 and row['victories'] == 0 and row['defeats'] > 0:
            target = campaign_target(row)
            if not memory.has_campaign_defeat(target):
                memory.record_campaign_defeat(target, state, config.main_six_ids, now=now)


def tick(config, memory, now=None, reader=None):
    now = time.time() if now is None else now
    config.validate()
    reader = reader or build_game_state
    state = reader(Path(config.game_root), static_path=Path(config.static_path) if config.static_path else None,
                   user_config=config)
    seed_campaign_defeats(state, config, memory, now)
    plan = Planner().plan(state, config, memory, now)
    output = plan.to_dict()
    if config.modules.automation and plan.next_action is not None:
        result = Actor(memory=memory, config=config).execute(plan.next_action.action, state, reader, live=False)
        output['execution_preview'] = asdict(result)
    else:
        output['execution_preview'] = {'status': 'paused', 'reason': 'Automation disabled or no eligible decision; no game action executed'}
    output.update(game_state=state.to_dict(), automation_requested=config.modules.automation,
                  input_state_ready=all(available(state, name) is not None for name in ('heroes', 'quests', 'relics')),
                  runtime_gates={'mode': 'DRY_RUN', 'production_handlers_enabled': False,
                                 'note': 'Automation schedules decisions only; no live action has a verified Windows handler'})
    return output, state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=default_config_path())
    parser.add_argument('--memory', type=Path)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--static', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--state-output', type=Path)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=float, default=1.0)
    args = parser.parse_args(argv)
    if args.interval < .2:
        parser.error('--interval must be at least 0.2 seconds')
    memory_path = args.memory or args.config.with_name('failure_memory.json')
    try:
        memory = FailureMemory(memory_path)
        while True:
            config = UserConfig.load(args.config)
            if args.root:
                config = replace(config, game_root=str(args.root))
            if args.static:
                config = replace(config, static_path=str(args.static))
            try:
                output, state = tick(config, memory)
                if args.output:
                    atomic_json(args.output, output)
                elif args.once:
                    print(json.dumps(output, ensure_ascii=False, indent=2))
                if args.state_output:
                    atomic_json(args.state_output, state.to_dict())
                summary = {name: len(available(state, name, [])) for name in ('heroes', 'quests', 'relics')}
                print(f'DRY_RUN actor=False heroes={summary["heroes"]} quests={summary["quests"]} relics={summary["relics"]} decisions={len(output["queue"])}', file=sys.stderr, flush=True)
                if args.once:
                    return 0 if state.sources else 1
            except (DecodeError, OSError) as error:
                if args.once:
                    raise
                print(f'Waiting for stable readable snapshots: {error}', file=sys.stderr, flush=True)
            time.sleep(args.interval)
    except (ConfigError, FailureMemoryError, DecodeError, OSError) as error:
        print(f'Runtime stopped without live actions: {error}', file=sys.stderr)
        if args.output and not args.output.exists():
            try:
                atomic_json(args.output, {'status': 'failed', 'error': str(error), 'actor_enabled': False})
            except OSError:
                pass
        return 2
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
