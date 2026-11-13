from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from bot_actions import Action
from failure_memory import FailureMemory
from game_state import build_game_state
from planner import Planner, quest_matches
from runtime import seed_campaign_defeats, tick
from user_config import UserConfig, ModuleConfig

FIXTURES = ROOT/'tests/fixtures'
STATIC = ROOT/'raw/static/static-data.0.62.1655(1).dat'
MAIN = [1, 2, 3, 5, 9, 17]  # Explicit test configuration, never a production UI-order guess.
NOW = 10000.0


def quest(qid, group, area=1, **extra):
    return {'quest_id': qid, 'group': group, 'state': 'New', 'action': 'BattleFinish',
            'progress': 0, 'conditions_decoded': True,
            'conditions': [{'type': 'Battle', 'area_id': area}], **extra}


class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = UserConfig(game_root=str(FIXTURES), static_path=str(STATIC),
                                arena_combat_power=9368, main_six_ids=MAIN,
                                modules=ModuleConfig(automation=True))
        cls.original = build_game_state(FIXTURES, static_path=STATIC, user_config=cls.config)

    def setUp(self):
        self.state = deepcopy(self.original)
        self.cfg = deepcopy(self.config)
        self.memory = FailureMemory()
        # Most tests inspect normal quest ranking after a recent verified development.
        self.memory.record_success(Action('test-development', 'HERO_LEVEL', 'invokers'), now=NOW-1)

    def plan(self):
        return Planner().plan(self.state, self.cfg, self.memory, NOW)

    def test_manual_arena_power_is_authoritative_with_snapshot_evidence_retained(self):
        power = self.state.arena.value['own_combat_power']
        self.assertEqual(power['value'], 9368)
        self.assertEqual(power['source'], 'UserConfig.arena_combat_power')
        self.assertIsNone(self.state.arena.value['snapshot_own_combat_power']['value'])
        arena = next(job.action for job in self.plan().queue if job.action.kind == 'ARENA_BATTLE')
        self.assertEqual((arena.target['name'], arena.target['combat_power']), ('TomTomson', 3567))
        self.assertNotEqual(arena.target['name'], 'Vinescia98')
        self.assertTrue(any('cost' in reason.lower() for job in self.plan().queue if job.action.kind == 'ARENA_BATTLE' for reason in job.safety_reasons))

    def test_daily_beats_progress_and_many_weekly_synergies(self):
        self.state.quests.value = [quest(1, 'Daily', state='Completed')]
        self.state.quests.value += [quest(i, 'Weekly', area=4) for i in range(2, 80)]
        self.state.quests.value += [quest(99, 'Advance', state='Completed')]
        plan = self.plan()
        self.assertEqual(plan.next_action.action.target['quest_id'], 1)
        progress = next(j for j in plan.queue if j.action.target.get('quest_id') == 99)
        arena = next(j for j in plan.queue if j.action.kind == 'ARENA_BATTLE')
        self.assertEqual((progress.priority, arena.priority), (1, 2))
        self.assertGreater(arena.synergy_score, progress.synergy_score)

    def test_campaign_overlap_combines_daily_monthly_and_clan(self):
        self.state.quests.value = [quest(1, 'Daily'), quest(2, 'Monthly'), quest(3, 'Clan')]
        farm = next(j for j in self.plan().queue if j.action.kind == 'CAMPAIGN_BATTLE' and j.action.preconditions.get('purpose') == 'safe_farm')
        self.assertEqual(farm.covered_quest_ids, [1, 2, 3])
        self.assertEqual(farm.priority, 0)
        wrong = quest(4, 'Daily')
        wrong['conditions'][0]['region_id'] = 6
        self.assertFalse(quest_matches(farm.action, wrong))
        wrong['conditions'][0] = {'type': 'Battle', 'area_id': 1, 'animas_count': 0}
        self.assertFalse(quest_matches(farm.action, wrong))

    def test_main_six_development_is_periodic_without_any_quests(self):
        self.state.quests.value = []
        self.memory = FailureMemory()
        first = self.plan().next_action
        self.assertEqual(first.action.kind, 'HERO_LEVEL')
        self.assertIn(first.action.target['hero_inventory_id'], MAIN)
        self.assertEqual(first.priority, -1)
        self.memory.record_success(first.action, now=NOW)
        recent = next(j for j in self.plan().queue if j.action.kind == 'HERO_LEVEL')
        self.assertEqual(recent.priority, 6)
        future = Planner().plan(self.state, self.cfg, self.memory, NOW+self.cfg.main_team_interval_seconds)
        self.assertEqual(future.next_action.action.kind, 'HERO_LEVEL')
        self.assertEqual(future.next_action.priority, -1)

    def test_main_six_never_guessed_from_sorted_hero_ids(self):
        self.cfg.main_six_ids = []
        plan = self.plan()
        self.assertEqual(plan.main_team_ids, [])
        self.assertTrue(any(j.action.kind == 'MAIN_TEAM_REVIEW' for j in plan.queue))
        self.assertFalse(any(j.action.kind == 'HERO_LEVEL' for j in plan.queue))

    def test_known_campaign_defeat_needs_persisted_relevant_improvement(self):
        def progress(plan):
            return next(j for j in plan.queue if j.action.kind == 'CAMPAIGN_BATTLE' and j.action.preconditions.get('purpose') == 'progress')
        self.assertTrue(progress(self.plan()).blocked_reasons)
        with TemporaryDirectory() as directory:
            path = Path(directory)/'memory.json'
            self.memory = FailureMemory(path)
            seed_campaign_defeats(self.state, self.cfg, self.memory, NOW)
            baseline = deepcopy(self.memory.data['campaign_defeats'])
            self.assertTrue(progress(self.plan()).blocked_reasons)
            self.state.resources.value['current']['values']['Gold'] += 1000000
            self.state.arena.value['own_combat_power']['value'] = 999999
            self.assertTrue(progress(self.plan()).blocked_reasons)
            next(h for h in self.state.heroes.value if h['inventory_id'] == MAIN[0])['level'] += 1
            seed_campaign_defeats(self.state, self.cfg, self.memory, NOW+1)
            self.assertEqual(self.memory.data['campaign_defeats'], baseline)
            self.memory = FailureMemory(path)
            self.assertFalse(progress(self.plan()).blocked_reasons)

    def test_campaign_safe_farming_remains_available_after_progress_defeat(self):
        seed_campaign_defeats(self.state, self.cfg, self.memory, NOW)
        jobs = [j for j in self.plan().queue if j.action.kind == 'CAMPAIGN_BATTLE']
        farm = next(j for j in jobs if j.action.preconditions.get('purpose') == 'safe_farm')
        progress = next(j for j in jobs if j.action.preconditions.get('purpose') == 'progress')
        self.assertEqual((farm.action.target['region'], farm.action.target['number']), (7, 5))
        self.assertFalse(farm.blocked_reasons)
        self.assertTrue(progress.blocked_reasons)

    def test_failure_memory_skips_current_arena_target_and_selects_next_weakest(self):
        first = next(j.action for j in self.plan().queue if j.action.kind == 'ARENA_BATTLE')
        self.memory.record_failure(first, 'target failed', now=NOW)
        self.memory.record_failure(first, 'target failed', now=NOW)
        second = next(j.action for j in self.plan().queue if j.action.kind == 'ARENA_BATTLE')
        self.assertNotEqual(first.target['player_id_bytes'], second.target['player_id_bytes'])
        self.assertEqual(second.target['combat_power'], 6066)

    def test_no_premium_fallback_when_no_weaker_arena_opponent(self):
        self.state.arena.value['own_combat_power']['value'] = 1
        jobs = self.plan().queue
        self.assertFalse(any(j.action.kind == 'ARENA_BATTLE' for j in jobs))
        refresh = next(j for j in jobs if j.action.kind == 'ARENA_REFRESH')
        self.assertTrue(refresh.safety_reasons)
        self.assertIsNone(refresh.action.resource_costs)

    def test_green_star_reserve_and_premium_quest_are_hard_limited(self):
        stars = self.state.resources.value['current']['values']['SI_WildStar']
        self.cfg.resource_reserves['SI_WildStar'] = stars
        self.assertFalse(any(j.action.kind == 'SUMMON_WILDSTAR' for j in self.plan().queue))
        self.cfg.resource_reserves['SI_WildStar'] = stars-1
        summon = next(j for j in self.plan().queue if j.action.kind == 'SUMMON_WILDSTAR')
        self.assertEqual(summon.action.resource_costs, {'SI_WildStar': 1})
        self.state.quests.value = [quest(1, 'Daily', action='ShopPurchase')]
        purchase = next(j for j in self.plan().queue if j.action.kind == 'SHOP_PURCHASE')
        self.assertTrue(purchase.blocked_reasons)
        self.assertTrue(purchase.safety_reasons)
        self.assertEqual(self.plan().to_dict()['executable_queue'], [])

    def test_module_toggles_suppress_module_and_quest_synergies(self):
        self.cfg.modules.arena = False
        arena = next(j for j in self.plan().queue if j.action.kind == 'ARENA_BATTLE')
        self.assertTrue(arena.blocked_reasons)
        self.cfg.modules.quests = False
        self.assertTrue(all(not j.covered_quest_ids for j in self.plan().queue))

    def test_monthly_review_is_occasional_after_verified_success(self):
        self.state.quests.value = [quest(10, 'Monthly', state='Completed')]
        self.assertTrue(any(j.action.kind == 'QUEST_CLAIM' for j in self.plan().queue))
        self.memory.record_success(Action('monthly', 'QUEST_CLAIM', 'quests', preconditions={'quest_group': 'Monthly'}), now=NOW)
        self.assertFalse(any(j.action.kind == 'QUEST_CLAIM' for j in self.plan().queue))
        future = Planner().plan(self.state, self.cfg, self.memory, NOW+1801)
        self.assertTrue(any(j.action.kind == 'QUEST_CLAIM' for j in future.queue))

    def test_event_bonus_requires_validated_active_definitions_and_cannot_change_category(self):
        self.state.quests.value = [quest(1, 'Weekly')]
        def score():
            return next(j for j in self.plan().queue if j.action.kind == 'CAMPAIGN_BATTLE' and j.action.preconditions.get('purpose') == 'safe_farm')
        initial = score().synergy_score
        event = self.state.events.value['tournaments'][0]
        event['definition'] = {'validated': False, 'action_kind': 'CAMPAIGN_BATTLE',
                               'starts_at_epoch': NOW-10, 'scoring_ends_at_epoch': NOW+10}
        self.assertEqual(score().synergy_score, initial)
        event['definition']['validated'] = True
        self.assertEqual(score().synergy_score, initial+75)
        self.assertEqual(score().priority, 2)
        event['definition']['scoring_ends_at_epoch'] = NOW-1
        self.assertEqual(score().synergy_score, initial)

    def test_bosses_events_and_relics_are_separate_modules_not_arena_aliases(self):
        jobs = self.plan().queue
        for module, kind in [('bosses', 'BOSS_REVIEW'), ('events', 'EVENT_REVIEW'), ('relics', 'RELIC_REVIEW')]:
            self.assertTrue(any(j.action.module == module and j.action.kind == kind for j in jobs))
        self.assertFalse(any(j.action.kind in ('RELIC_SELL', 'RELIC_DESTROY', 'RELIC_UPGRADE') for j in jobs))

    def test_boss_farming_uses_known_wins_and_decoded_cross_quest_synergy(self):
        clan = quest(2, 'Clan', area=2)
        clan['conditions'][0] = {'type': 'Battle', 'region_ids': [24, 25]}
        self.state.quests.value = [quest(1, 'Daily', area=2), clan]
        bosses = [j for j in self.plan().queue if j.action.kind == 'BOSS_BATTLE'
                  and j.action.preconditions.get('purpose') == 'safe_boss_farm']
        self.assertEqual(len(bosses), 3)
        selected = next(j for j in bosses if j.action.target['region'] == 24)
        self.assertEqual(selected.action.target['number'], 3)  # 24-4 is a recorded defeat.
        self.assertEqual(selected.covered_quest_ids, [1, 2])
        self.assertEqual(selected.priority, 0)
        self.assertTrue(selected.safety_reasons)  # Exact cost contract remains unverified.

    def test_passive_achievements_do_not_flood_the_operational_queue(self):
        self.assertEqual(len(self.state.quests.value), 524)
        plan = self.plan()
        self.assertLess(len(plan.queue), 60)
        self.assertFalse(any(j.action.kind == 'QUEST_REVIEW' and j.action.target.get('quest_id') in
                             {q['quest_id'] for q in self.state.quests.value if q['group'] == 'Achievements'}
                             for j in plan.queue))

    def test_unknown_quest_state_never_adds_priority_or_authorizes_a_claim(self):
        known = quest(1, 'Daily', state='Unknown(99)')
        self.state.quests.value = [known]
        plan = self.plan()
        self.assertTrue(all(not j.covered_quest_ids for j in plan.queue))
        self.assertFalse(any(j.action.kind == 'QUEST_CLAIM' for j in plan.queue))

    def test_runtime_rereads_and_honors_config_changes_without_live_calls(self):
        calls = []
        def reader(root, **kwargs):
            calls.append(kwargs['user_config'].arena_combat_power)
            return build_game_state(root, **kwargs)
        first, state = tick(self.cfg, self.memory, now=NOW, reader=reader)
        self.cfg.arena_combat_power = 1
        second, state = tick(self.cfg, self.memory, now=NOW+1, reader=reader)
        self.assertEqual(calls, [9368, 1])
        self.assertTrue(any(j['kind'] == 'ARENA_BATTLE' for j in first['queue']))
        self.assertFalse(any(j['kind'] == 'ARENA_BATTLE' for j in second['queue']))
        self.assertFalse(second['actor_enabled'])
        self.assertEqual(second['executable_queue'], [])


if __name__ == '__main__':
    unittest.main()
