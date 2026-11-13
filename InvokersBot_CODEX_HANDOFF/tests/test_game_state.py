from pathlib import Path
import json,struct,sys,unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from memorypack import DecodeError,Span,model
from structured_state import read_arena_collections,read_battle_state,read_events,dotnet_time
from game_state import build_game_state
import invokers_core as core
import autonomy_bridge as bridge
from user_config import UserConfig
FIXTURES=ROOT/'tests/fixtures'
STATIC=ROOT/'raw/static/static-data.0.62.1655(1).dat'

def pack_object(fields):
    lengths=b''.join(bytes([len(f)]) if len(f)<=127 else b'\x82'+struct.pack('<i',len(f)) for f in fields)
    return bytes([len(fields)])+lengths+b''.join(fields)

def envelope(tag,fields):
    return bytes([tag])+pack_object([b'\0'*8,b'\0'*8,pack_object(fields)])

class StructuredStateTests(unittest.TestCase):
    def test_arena_collections_stay_separate_and_preserve_unicode(self):
        collections=read_arena_collections(FIXTURES/'PlayerArenaModel.dat')
        self.assertEqual([len(c['records']) for c in collections],[10,21])
        self.assertEqual([c['role'] for c in collections],['current','other_stored'])
        records=[r for c in collections for r in c['records']]
        self.assertEqual(next(r['combat_power'] for r in records if r['name']=='Vinescia98'),2522)
        self.assertEqual(next(r['combat_power'] for r in records if r['name']=='Lótus Master'),9592)
        player_id=model((FIXTURES/'PlayerModel.dat').read_bytes(),1)[0].data.hex()
        self.assertFalse(any(r['player_id_bytes']==player_id for r in records))

    def test_arena_preset_links_to_actual_inventory(self):
        preset=read_battle_state(FIXTURES/'PlayerBattleModel.dat')['attack_preset']
        self.assertEqual((preset['formation_id'],preset['lead_position']),(2,21))
        self.assertEqual([s['position'] for s in preset['slots']],[11,21,31,32])
        self.assertEqual([s['hero_inventory_id'] for s in preset['slots']],[166,5,167,2])
        self.assertEqual([s['anima_inventory_id'] for s in preset['slots']],[2,None,None,1])
        heroes={h['inventory_id']:h for h in core.decode_heroes(FIXTURES/'PlayerHeroesModel.dat')}
        for slot in preset['slots']:
            self.assertEqual(heroes[slot['hero_inventory_id']]['config_id'],slot['hero_config_id'])

    def test_null_setup_has_unknown_current_power(self):
        battle=read_battle_state(FIXTURES/'PlayerBattleModel.dat')
        self.assertFalse(battle['last_meta_battle_setup_present'])
        self.assertIsNone(battle['own_combat_power']['value'])
        self.assertIn('null',battle['own_combat_power']['reason'])

    def test_historical_setup_never_becomes_current_arena_power(self):
        fields=[f.data for f in model((FIXTURES/'PlayerBattleModel.dat').read_bytes(),7)]
        fields[2]=pack_object([struct.pack('<i',9368)])
        with TemporaryDirectory() as directory:
            path=Path(directory)/'battle.dat'; path.write_bytes(envelope(7,fields))
            battle=read_battle_state(path)
        self.assertTrue(battle['last_meta_battle_setup_present'])
        self.assertIsNone(battle['own_combat_power']['value'])

    def test_all_captured_participations(self):
        events=read_events(FIXTURES/'PlayerGlobalEventsModel.dat')
        records={r['tournament_id']:r for r in events['tournaments']}
        self.assertEqual(set(records),{935,939,991,1000,1006,1007})
        self.assertEqual({k:v['points'] for k,v in records.items() if 'points' in v},{935:50700,939:86550,1000:352,1006:240,1007:8})
        self.assertEqual(records[991]['points_by_source_type_id'],{6:5034,12:101400,14:3660,5:2200,9:480,4:520,7:210,13:10000,8:16})
        self.assertEqual(records[991]['purchased_shop_items_by_id'],{})
        self.assertTrue(records[1006]['scoring_completed'])
        self.assertEqual(records[1006]['final_bracket_rank'],32)
        self.assertEqual(records[1006]['final_global_rank'],0)
        self.assertIsNone(records[1007]['bracket_id'])
        self.assertEqual(records[1006]['unlocked_milestone_reward_ids'],[303])
        self.assertEqual(records[935]['claimed_personal_reward_ids'],list(range(1,11)))
        self.assertLess(records[939]['bracket_started_at_utc']['ticks'],records[939]['scoring_ends_at_utc']['ticks'])
        self.assertFalse(events['finished_novice_tournament'])
        self.assertEqual(events['completed_novice_tournament_group_ids'],[])
        for record in records.values():
            self.assertEqual(record['validation'],'captured_fixture')
            self.assertIsNone(record['definition'])
            self.assertEqual(record['unknown_fields'],[])

    def test_daily_schema_only_not_claimed_as_fixture_validation(self):
        # Synthetic profile: no captured DailyBestScore fixture exists yet.
        i=lambda n:struct.pack('<i',n)
        q=lambda n:struct.pack('<q',n)
        ni=lambda n:b'\1\0\0\0'+i(n)
        nq=lambda n:b'\1'+b'\0'*7+q(n)
        reward=pack_object([ni(2),ni(3),b'\1',b'\0',q(9876543210)])
        fields=[b'']*50
        fields[0],fields[2],fields[3],fields[4]=q(123),q(1),b'\0',i(0)
        fields += [nq(8),q(9876543210),ni(4),q(1234567890),i(1)+i(4)+reward,reward,ni(5),i(0),i(1)+i(301),i(0),i(0)]
        dictionary=i(1)+q(123)+b'\4'+pack_object(fields)
        with TemporaryDirectory() as directory:
            path=Path(directory)/'events.dat';path.write_bytes(envelope(10,[dictionary,b'\0',i(0)]))
            record=read_events(path)['tournaments'][0]
        self.assertEqual(record['validation'],'schema_only')
        self.assertEqual(record['period_score'],9876543210)
        self.assertEqual(record['daily_reward_states'][4]['final_global_rank'],3)
        self.assertEqual(record['period_reward_state']['score'],9876543210)

    def test_bad_tournament_identity_and_union_fail_closed(self):
        original=[f.data for f in model((FIXTURES/'PlayerGlobalEventsModel.dat').read_bytes(),10)]
        for position,byte in [(4,0),(12,99)]:
            with self.subTest(position=position),TemporaryDirectory() as directory:
                fields=list(original);data=bytearray(fields[0]);data[position]=byte;fields[0]=bytes(data)
                path=Path(directory)/'events.dat';path.write_bytes(envelope(10,fields))
                with self.assertRaises(DecodeError):read_events(path)

    def test_truncated_fixtures_rejected(self):
        for name,read in [('PlayerBattleModel.dat',read_battle_state),('PlayerGlobalEventsModel.dat',read_events)]:
            data=(FIXTURES/name).read_bytes()
            for cut in (0,1,10,len(data)-1):
                with self.subTest(name=name,cut=cut),TemporaryDirectory() as directory:
                    path=Path(directory)/name;path.write_bytes(data[:cut])
                    with self.assertRaises(DecodeError):read(path)

    def test_bounds_padding_and_time(self):
        for data in (b'\1\x82\xff\xff\xff\xff',pack_object([b'ab'])[:-1],pack_object([])+b'extra'):
            with self.assertRaises(DecodeError):Span(data).object()
        self.assertIsNone(Span(b'\0\x67\x93\x43\xff\xff\xff\xff').nullable())
        self.assertEqual(Span(b'\1\x67\x93\x43\x20\0\0\0').nullable(),32)
        self.assertEqual(dotnet_time(Span(struct.pack('<Q',1<<62)))['iso'],'0001-01-01T00:00:00+00:00')

class GameStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.state=build_game_state(FIXTURES,static_path=STATIC)

    def test_unified_readers_provenance_and_unknowns(self):
        state=self.state
        self.assertEqual(len(state.sources),10)
        for name in ('resources','campaign','arena','events','heroes','quests','relics'):
            observation=getattr(state,name)
            self.assertEqual(observation.status,'available',(name,observation.reason))
            self.assertTrue(observation.sources)
        self.assertEqual((len(state.heroes.value),len(state.quests.value),len(state.relics.value)),(30,524,313))
        self.assertEqual(len(state.arena.value['opponents']),10)
        self.assertEqual(state.arena.value['unresolved_hero_inventory_ids'],[])
        self.assertEqual(state.heroes.method,'structured')
        self.assertEqual(state.resources.method,'structured')
        self.assertIsNone(state.arena.value['own_combat_power']['value'])
        for name in ('actor_enabled','gems_allowed','premium_spend_allowed'):self.assertFalse(state.safety[name])
        self.assertEqual(state.hero_internal_names.value[166],'CAM007')
        self.assertTrue(any(q.get('action')=='BattleFinish' for q in state.quests.value))
        self.assertIn('static_data',state.quests.sources)
        json.dumps(state.to_dict())

    def test_missing_and_corrupt_inputs_unknown_not_zero(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);state=build_game_state(root)
            self.assertEqual(state.resources.status,'unknown');self.assertIsNone(state.resources.value)
            self.assertIsNone(state.heroes.value)
            (root/'PlayerBattleModel.dat').write_bytes(b'bad');state=build_game_state(root)
            self.assertEqual(state.campaign.status,'unknown');self.assertIn('tag',state.campaign.reason)

    def test_changed_capture_rejected(self):
        original=Path.read_bytes;reads={}
        def read(path):
            data=original(path)
            if path==FIXTURES/'PlayerModel.dat':
                reads[path]=reads.get(path,0)+1
                if reads[path]>1:return data+b'changed'
            return data
        with patch.object(Path,'read_bytes',read),self.assertRaisesRegex(DecodeError,'changed during capture'):
            build_game_state(FIXTURES)

    def test_invalid_static_data_is_unknown(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'static.dat';path.write_bytes(b'broken')
            state=build_game_state(FIXTURES,static_path=path)
        self.assertEqual(state.hero_internal_names.status,'unknown')
        self.assertEqual(state.quest_prototypes.status,'unknown')
        self.assertIsNone(state.hero_internal_names.value)
        self.assertNotIn('static_data',state.quests.sources)

    def test_unknown_inventory_blocks_bridge_commands(self):
        from copy import deepcopy
        state=deepcopy(self.state)
        state.heroes.value=None;state.heroes.status='unknown';state.heroes.reason='corrupt fixture'
        with TemporaryDirectory() as directory,patch.object(bridge,'PLAN_FILE',Path(directory)/'plan.json'),patch.object(bridge,'build_game_state',return_value=state):
            plan=bridge.build_plan()
        self.assertFalse(plan['input_state_ready'])
        self.assertEqual(plan['executable_queue'],[])
        self.assertIsNone(plan['next_executable'])

    def test_bridge_uses_unified_state_and_keeps_spending_locked(self):
        config=UserConfig(game_root=str(FIXTURES),arena_combat_power=9368)
        state=build_game_state(FIXTURES,user_config=config)
        with TemporaryDirectory() as directory:
            output=Path(directory)/'plan.json'
            with patch.object(bridge,'GAME_ROOT',FIXTURES),patch.object(bridge,'PLAN_FILE',output),patch.object(bridge,'build_game_state',return_value=state) as build:
                plan=bridge.build_plan(config=config)
            build.assert_called_once_with(FIXTURES,static_path=None,user_config=config);saved=json.loads(output.read_text())
        self.assertEqual(saved['game_state']['resources']['value']['current']['values']['Gem'],310)
        self.assertEqual(plan['game_state']['arena']['value']['attack_preset']['slots'][0]['hero_inventory_id'],166)
        self.assertFalse(plan['actor_enabled'])
        for job in plan['executable_queue']:
            self.assertNotIn(job['kind'],{'SHOP_PURCHASE','RELIC_SELL','RELIC_DESTROY','RELIC_UPGRADE'})
            self.assertNotEqual(job['kind'],'ARENA_BATTLE')
        arena_jobs=[job for job in plan['queue'] if job.get('kind')=='ARENA_BATTLE']
        self.assertTrue(arena_jobs)
        self.assertTrue(all(not job['execution_ready'] and job['safety_reasons'] for job in arena_jobs))

if __name__=='__main__':unittest.main()
