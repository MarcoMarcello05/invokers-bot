from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from arena_autopilot import ArenaAutopilot, ArenaError, ArenaFrame
from arena_simulation import SimulatedArena
from arena_actor import search_selected_candidate, locate_name
from arena_snapshot import ArenaSnapshotSource, SnapshotError
from arena_runner import validate_live_preflight
from arena_windows import DEFAULT_PROFILE, load_profile, profile_fingerprint
from failure_memory import FailureMemory
from user_config import UserConfig
from fixture_support import arena_source_samples


class Clock:
    def __init__(self):self.value=0
    def now(self):return self.value
    def sleep(self,seconds):self.value+=seconds


class ArenaSprintTests(unittest.TestCase):
    def setUp(self):
        self.temporary=TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.folder=Path(self.temporary.name)
        self.config=UserConfig(arena_combat_power=10000)
        self.fake=SimulatedArena()
        self.clock=Clock()

    def run_pilot(self,**overrides):
        arguments=dict(mode='simulation',cycles=2,ui_timeout=.5,battle_timeout=.5,
                       snapshot_timeout=.5,poll=.1,clock=self.clock.now,sleep=self.clock.sleep)
        arguments.update(overrides)
        self.pilot=ArenaAutopilot(self.fake,self.fake,self.config,FailureMemory(),self.folder,**arguments)
        return self.pilot.run()

    def test_two_complete_cycles_keep_priority_and_reobserve_after_each_battle(self):
        result=self.run_pilot()
        self.assertEqual((result['status'],result['completed_cycles']),('COMPLETED',2))
        self.assertEqual([r['target']['name'] for r in result['results']],['WeakTarget','NextTarget'])
        self.assertGreaterEqual(self.fake.reads,10)
        self.assertEqual(self.fake.commands.count('start_battle'),2)
        self.assertEqual(self.fake.commands.count('return_to_arena'),2)
        self.assertNotIn('auto_on',self.fake.commands)
        self.assertEqual(self.fake.state['resources']['value']['current']['values']['Gem'],10)
        self.assertTrue(all(any(e['phase']==phase for e in result['events']) for phase in ('OBSERVE','PLAN','ACT','VERIFY','REPLAN')))

    def test_defeat_is_verified_and_next_iteration_excludes_that_identity(self):
        self.fake=SimulatedArena(outcomes=('DEFEAT','VICTORY'))
        result=self.run_pilot()
        self.assertEqual([r['outcome'] for r in result['results']],['defeat','success'])
        self.assertNotEqual(result['results'][0]['target']['player_id_bytes'],result['results'][1]['target']['player_id_bytes'])

    def test_default_dry_run_has_no_input(self):
        result=self.run_pilot(mode='dry')
        self.assertEqual(result['status'],'DRY_RUN')
        self.assertEqual(self.fake.commands,[])
        self.assertFalse(result['preflight_passed'])

    def test_navigation_dry_run_reaches_formation_but_never_starts_battle(self):
        result=self.run_pilot(mode='dry',navigate=True)
        self.assertEqual(result['status'],'WOULD_START_BATTLE')
        self.assertTrue(result['preflight_passed'])
        self.assertNotIn('start_battle',self.fake.commands)
        self.assertEqual(self.fake.state['resources']['value']['current']['values']['Arena_Token'],10)

    def test_explicit_live_activation_required_before_any_input(self):
        result=self.run_pilot(mode='live',live_armed=False)
        self.assertEqual(result['code'],'LIVE_DISABLED')
        self.assertEqual(self.fake.commands,[])

    def test_unknown_screen_dialog_and_foreground_loss_never_get_confirmed(self):
        for frame,code in [(ArenaFrame('UNKNOWN'),'UNEXPECTED_SCREEN'),(ArenaFrame('DIALOG'),'UNKNOWN_DIALOG'),
                           (ArenaFrame('ARENA_LIST',safe_foreground=False),'FOREGROUND_LOST')]:
            with self.subTest(code=code):
                self.fake=SimulatedArena()
                with patch.object(self.fake,'observe',return_value=frame):result=self.run_pilot()
                self.assertEqual(result['code'],code)
                self.assertEqual(self.fake.commands,[])

    def test_identity_and_power_mismatches_stop_before_spending(self):
        for changes,code in [({'selected_name':'WrongTarget'},'FORMATION_IDENTITY_MISMATCH'),
                             ({'own_power':99999},'OWN_POWER_UNCONFIRMED'),
                             ({'token_cost':2},'COST_NOT_VERIFIED'),
                             ({'token_currency_verified':False},'COST_NOT_VERIFIED')]:
            with self.subTest(code=code):
                self.fake=SimulatedArena();original=self.fake.observe
                def observe():
                    frame=original()
                    return replace(frame,**changes) if frame.state=='FORMATION' else frame
                with patch.object(self.fake,'observe',side_effect=observe):result=self.run_pilot()
                self.assertEqual(result['code'],code)
                self.assertNotIn('start_battle',self.fake.commands)

    def test_missing_or_ambiguous_identity_never_falls_back_to_visible_stronger(self):
        with patch.object(self.fake,'locate',return_value=None):result=self.run_pilot()
        self.assertEqual(result['code'],'TARGET_NOT_FOUND')
        self.assertNotIn('start_battle',self.fake.commands)
        self.fake=SimulatedArena()
        self.fake.state['arena']['value']['opponents'].append({'name':'[CLAN] WeakTarget','player_id_bytes':'d'*32,'combat_power':2100,'arena_points':10,'level':1})
        result=self.run_pilot()
        self.assertEqual(result['code'],'AMBIGUOUS_IDENTITY')
        self.assertEqual(self.fake.commands,[])

    def test_auto_off_must_be_observed_and_is_never_enabled_by_bot(self):
        self.fake.auto_off=False
        result=self.run_pilot()
        self.assertEqual(result['code'],'AUTO_NOT_CONFIRMED_OFF')
        self.assertEqual(self.fake.commands.count('start_battle'),1)
        self.assertNotIn('auto_on',self.fake.commands)
        self.assertNotIn('return_to_arena',self.fake.commands)

    def test_battle_and_navigation_timeout_are_bounded(self):
        self.fake.phase='BATTLE_MENU'
        with patch.object(self.fake,'perform'):
            result=self.run_pilot()
        self.assertEqual(result['code'],'UI_TIMEOUT')
        self.assertLess(self.clock.value,3)
        self.fake=SimulatedArena();original=self.fake.observe
        def never_end():
            if self.fake.phase=='BATTLE':return ArenaFrame('BATTLE',auto_off=True)
            return original()
        with patch.object(self.fake,'observe',side_effect=never_end):result=self.run_pilot()
        self.assertEqual(result['code'],'BATTLE_TIMEOUT')
        self.assertEqual(self.fake.commands.count('start_battle'),1)

    def test_snapshot_result_lag_or_unexpected_premium_spend_never_counts_as_success(self):
        for premium in (False,True):
            with self.subTest(premium=premium):
                self.fake=SimulatedArena();original=self.fake.observe
                def observe():
                    frame=original()
                    if frame.state=='VICTORY':
                        if premium:self.fake.state['resources']['value']['current']['values']['Gem']=9
                        else:self.fake.state['arena']['value']['stats']['total_offense_battles']=0
                    return frame
                with patch.object(self.fake,'observe',side_effect=observe):result=self.run_pilot()
                self.assertEqual(result['code'],'RESULT_NOT_VERIFIED')
                self.assertEqual(result['completed_cycles'],0)
                self.assertNotIn('return_to_arena',self.fake.commands)
                if premium:self.assertIn('Gem',result['detail'])

    def test_result_disagreement_is_a_safe_stop(self):
        original=self.fake.observe
        def observe():
            frame=original()
            if frame.state=='VICTORY':self.fake.state['arena']['value']['stats']['total_offense_wins']=0
            return frame
        with patch.object(self.fake,'observe',side_effect=observe):result=self.run_pilot()
        self.assertEqual(result['code'],'RESULT_MISMATCH')

    def test_stop_and_backend_errors_are_logged_without_retries(self):
        self.fake.stop=True
        result=self.run_pilot()
        self.assertEqual(result['code'],'STOP_REQUESTED')
        self.assertEqual(self.fake.commands,[])
        self.fake=SimulatedArena()
        with patch.object(self.fake,'observe',side_effect=RuntimeError('OCR failed')):result=self.run_pilot()
        self.assertEqual(result['code'],'UI_BACKEND_ERROR')
        self.assertIn('SAFE_STOP',(self.folder/'events.jsonl').read_text())
        self.assertTrue((self.folder/'report.json').exists())

    def test_resource_unknown_and_changed_target_stop_before_click(self):
        del self.fake.state['resources']['value']['current']['values']['Gem']
        self.assertEqual(self.run_pilot()['code'],'RESOURCES_UNKNOWN')
        self.fake=SimulatedArena();original=self.fake.read
        def read():
            if self.fake.reads:
                self.fake.state['arena']['value']['opponents'][0]['combat_power']=2500
            return original()
        with patch.object(self.fake,'read',side_effect=read):result=self.run_pilot()
        self.assertEqual(result['code'],'STALE_TARGET')
        self.assertNotIn('start_battle',self.fake.commands)

    def test_bounded_search_returns_only_selected_identity_and_rejects_partial_ocr(self):
        observations=[ArenaFrame('ARENA_LIST',rows=[{'text':'VisibleStrong','conf':.99,'x':700,'y':400}])]*3
        observations += [ArenaFrame('ARENA_LIST',rows=[{'text':'WeakTarget','conf':.99,'x':700,'y':600}])]
        moves=[]
        found,meta=search_selected_candidate({'name':'WeakTarget'},lambda:observations.pop(0) if observations else ArenaFrame('ARENA_LIST'),moves.append,max_steps=3)
        self.assertEqual(found[1]['text'],'WeakTarget')
        self.assertLessEqual(len(moves),6)
        self.assertIsNone(locate_name('WeakTarget',[{'text':'Weak','conf':.99}]))
        self.assertIsNone(locate_name('WeakTarget',[{'text':'WeakTarget','conf':.99},{'text':'WeakTarget','conf':.99}]))
        result,meta=search_selected_candidate({'name':'Absent'},lambda:ArenaFrame('ARENA_LIST'),moves.append,max_steps=2)
        self.assertIsNone(result)
        self.assertLessEqual(meta['screens'],6)

    def test_snapshot_stale_future_missing_and_corruption_rejected(self):
        config=replace(self.config,game_root=str(self.folder))
        names=('PlayerArenaModel.dat','PlayerModel.dat')
        for name,data in arena_source_samples().items():(self.folder/name).write_bytes(data)
        source=ArenaSnapshotSource(config,max_age=5)
        self.assertEqual(len(source.read().state['arena']['value']['opponents']),1)
        for stamp in (time.time()-100,time.time()+100):
            os.utime(self.folder/names[0],(stamp,stamp))
            with self.assertRaises(SnapshotError) as context:source.read()
            self.assertEqual(context.exception.code,'STALE_SNAPSHOT')
        (self.folder/names[0]).write_bytes(b'bad')
        with self.assertRaises(SnapshotError):source.read()
        (self.folder/names[0]).unlink()
        with self.assertRaises(SnapshotError):source.read()

    def test_live_preflight_binds_recent_power_root_calibration_and_token_contract(self):
        profile=deepcopy(DEFAULT_PROFILE);profile['operator_confirmed_auto_off']=True
        path=self.folder/'profile.json';path.write_text(json.dumps(profile))
        report=self.folder/'audit.json'
        good={'mode':'dry','status':'WOULD_START_BATTLE','preflight_passed':True,'created_at_epoch':100,
              'own_power':10000,'game_root':str(Path(self.config.game_root).resolve()),
              'calibration_sha256':profile_fingerprint(path),'cost':{'Arena_Token':1}}
        report.write_text(json.dumps(good));validate_live_preflight(report,self.config,path,profile,now=101)
        for change in ({'created_at_epoch':-500},{'own_power':1},{'calibration_sha256':'wrong'},
                       {'cost':{'Gem':0}},{'preflight_passed':False}):
            report.write_text(json.dumps({**good,**change}))
            with self.assertRaises(ValueError):validate_live_preflight(report,self.config,path,profile,now=101)
        profile['token_reference']='gem.png';path.write_text(json.dumps(profile))
        with self.assertRaises(ValueError):load_profile(path)

    def test_recovery_is_bounded_and_never_confirms_dialogs(self):
        self.fake.phase='FORMATION';self.fake.selected={'name':'Unexpected'}
        result=self.run_pilot(max_recovery=1)
        self.assertEqual(result['status'],'SAFE_STOP')
        self.assertTrue(result['recovered'])
        self.assertEqual(self.fake.commands,['back'])
        self.assertEqual(result['completed_cycles'],0)

    def test_free_refresh_rereads_current_data_before_planning_and_never_spends_gems(self):
        self.fake.state['arena']['value']['opponents']=[{'name':'TooStrong','combat_power':20000,'player_id_bytes':'e'*32,'level':1,'arena_points':0}]
        self.fake.phase='ARENA_LIST'
        original_observe=self.fake.observe;original_perform=self.fake.perform
        def observe():return replace(original_observe(),free_refresh_verified=True)
        def perform(command,frame,target=None):
            if command=='refresh':
                self.fake.commands.append(command)
                self.fake.state['arena']['value']['opponents']=[{'name':'WeakTarget','combat_power':2000,'player_id_bytes':'a'*32,'level':1,'arena_points':0}]
            else:original_perform(command,frame,target)
        with patch.object(self.fake,'observe',side_effect=observe),patch.object(self.fake,'perform',side_effect=perform):
            result=self.run_pilot(cycles=1,max_refreshes=1)
        self.assertEqual(result['status'],'COMPLETED')
        self.assertEqual(self.fake.commands.count('refresh'),1)
        self.assertEqual(self.fake.state['resources']['value']['current']['values']['Gem'],10)
        self.assertEqual(result['results'][0]['target']['name'],'WeakTarget')

    def test_unverified_refresh_and_unchanged_lists_stop_without_repeating_click(self):
        self.fake.phase='ARENA_LIST'
        for target in self.fake.state['arena']['value']['opponents']:target['combat_power']=20000
        result=self.run_pilot(cycles=1,max_refreshes=3)
        self.assertEqual(result['code'],'REFRESH_COST_UNVERIFIED')
        self.assertNotIn('refresh',self.fake.commands)
        original=self.fake.observe
        with patch.object(self.fake,'observe',side_effect=lambda:replace(original(),free_refresh_verified=True)),patch.object(self.fake,'perform',side_effect=lambda command,*args:self.fake.commands.append(command)):
            result=self.run_pilot(cycles=1,max_refreshes=3)
        self.assertEqual(result['code'],'REFRESH_NOT_VERIFIED')
        self.assertEqual(self.fake.commands.count('refresh'),1)

    def test_simulated_backend_cannot_produce_a_live_claim(self):
        result=self.run_pilot(mode='live',live_armed=True)
        self.assertEqual(result['code'],'SIMULATION_CANNOT_BE_LIVE')
        self.assertEqual(self.fake.commands,[])

    def test_navigation_dry_run_never_refreshes_even_when_refresh_budget_is_set(self):
        for target in self.fake.state['arena']['value']['opponents']:target['combat_power']=20000
        result=self.run_pilot(mode='dry',navigate=True,max_refreshes=3)
        self.assertEqual(result['code'],'NO_ELIGIBLE_OPPONENT')
        self.assertEqual(self.fake.commands,[])


if __name__=='__main__':unittest.main()
