from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from actor import Actor
from bot_actions import Action
from failure_memory import FailureMemory, FailureMemoryError
from game_state import Observation, build_game_state
from safety import Safety
from verification import verify
from vision import LocatedTarget, locate_intended_label


class ExecutionLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = build_game_state(ROOT/'tests/fixtures')
        cls.ids = [h['inventory_id'] for h in cls.base.heroes.value[:6]]

    def action(self, kind='HERO_LEVEL', target=None, costs=None, effect='hero_level'):
        module = 'arena' if kind.startswith('ARENA_') else 'campaign' if kind.startswith('CAMPAIGN_') else 'invokers'
        return Action('test-action', kind, module, target or {'hero_inventory_id': self.ids[0]},
                      costs, {'costs_verified': True}, {'type': effect})

    def test_premium_and_destructive_actions_cannot_be_enabled_by_config(self):
        safety = Safety()
        for action in (self.action(costs={'Gem': 0}), self.action(costs={'Gems': 1}),
                       self.action(costs={'premium': 1}), self.action(kind='SHOP_PURCHASE', costs={}),
                       self.action(kind='RELIC_SELL', costs={}), self.action(kind='HERO_SEND_AWAY', costs={})):
            with self.subTest(action=action.kind, costs=action.resource_costs):
                self.assertFalse(safety.evaluate(action, self.base, {'allow_gems': True, 'actor_enabled': True}).allowed)

    def test_unknown_cost_balance_reserve_and_currency_aliases_block(self):
        self.assertFalse(Safety().evaluate(self.action(), self.base).allowed)
        state = deepcopy(self.base); state.resources.status = 'unknown'
        self.assertFalse(Safety().evaluate(self.action(costs={'Gold': 1}), state).allowed)
        gold = self.base.resources.value['current']['values']['Gold']
        self.assertFalse(Safety().evaluate(self.action(costs={'Gold': 1}), self.base, {'resource_reserves': {'Gold': gold}}).allowed)
        token_count = self.base.resources.value['current']['values']['Arena_Token']
        self.assertFalse(Safety().evaluate(self.action(costs={'ArenaToken': token_count, 'Arena_Token': 1}), self.base).allowed)
        self.assertTrue(Safety().evaluate(self.action(costs={'Gold': 1}), self.base).allowed)

    def test_arena_uses_current_structured_candidates_and_authoritative_manual_power(self):
        state = deepcopy(self.base)
        target = min(state.arena.value['opponents'], key=lambda r: r['combat_power'])
        action = self.action('ARENA_BATTLE', target, {'Arena_Token': 1}, 'arena_battle')
        self.assertFalse(Safety().evaluate(action, state).allowed)
        state.arena.value['own_combat_power'] = {'value': 9368, 'source': 'UserConfig.arena_combat_power'}
        self.assertTrue(Safety().evaluate(action, state).allowed)
        stale = self.action('ARENA_BATTLE', {'name': 'Vinescia98', 'combat_power': 2522}, {'Arena_Token': 1}, 'arena_battle')
        self.assertFalse(Safety().evaluate(stale, state).allowed)
        state.arena.value['own_combat_power']['value'] = target['combat_power']
        self.assertFalse(Safety().evaluate(action, state).allowed)

    def test_dry_run_and_live_request_never_call_handlers(self):
        called = []
        action = self.action(costs={'Gold': 1})
        actor = Actor()
        self.assertEqual(actor.execute(action, self.base, lambda: self.base, lambda _: called.append(1)).status, 'planned')
        self.assertEqual(actor.execute(action, self.base, lambda: self.base, lambda _: called.append(1), live=True).status, 'blocked')
        self.assertEqual(called, [])
        self.assertEqual(actor.LIVE_CAPABILITIES, frozenset())

    def test_disabled_module_and_mismatched_module_fail_before_handler(self):
        action = self.action(costs={'Gold': 1})
        called = []
        actor = Actor(config={'modules': {'invokers': False}})
        result = actor.simulate(action, self.base, lambda: self.base, lambda _: called.append(1))
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(called, [])
        forged = Action('forged', 'ARENA_REFRESH', 'invokers', resource_costs={},
                        preconditions={'costs_verified': True}, expected_effects={'type': 'arena_refresh'})
        self.assertFalse(Safety().evaluate(forged, self.base).allowed)

    def test_stale_arena_target_is_rechecked_from_fresh_state(self):
        planned = deepcopy(self.base)
        planned.arena.value['own_combat_power'] = {'value': 9368, 'source': 'UserConfig.arena_combat_power'}
        target = min(planned.arena.value['opponents'], key=lambda r: r['combat_power'])
        action = self.action('ARENA_BATTLE', target, {'Arena_Token': 1}, 'arena_battle')
        fresh = deepcopy(planned)
        fresh.arena.value['opponents'] = [r for r in fresh.arena.value['opponents'] if r['name'] != target['name']]
        called = []
        result = Actor().simulate(action, planned, lambda: fresh, lambda _: called.append(1))
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(called, [])

    def test_click_or_hash_change_is_not_a_verified_hero_upgrade(self):
        after = deepcopy(self.base)
        after.sources['PlayerHeroesModel.dat']['sha256'] = 'changed'
        self.assertFalse(verify(self.action(costs={'Gold': 1}), self.base, after).verified)

    def test_unexpected_gem_spend_prevents_success_even_if_level_increases(self):
        after = deepcopy(self.base)
        after.heroes.value[0]['level'] += 1
        after.resources.value['current']['values']['Gold'] -= 1
        after.resources.value['current']['values']['Gem'] -= 1
        result = verify(self.action(costs={'Gold': 1}), self.base, after)
        self.assertFalse(result.verified)
        self.assertIn('Gem', result.reason)

    def test_verified_hero_upgrade_updates_persistent_development_time(self):
        after = deepcopy(self.base)
        after.heroes.value[0]['level'] += 1
        after.resources.value['current']['values']['Gold'] -= 10
        action = self.action(costs={'Gold': 10})
        with TemporaryDirectory() as directory:
            path = Path(directory)/'memory.json'
            memory = FailureMemory(path)
            reads = iter([self.base, after])
            called = []
            result = Actor(memory=memory).simulate(action, self.base, lambda: next(reads), lambda a: called.append(a.action_id), now=100)
            self.assertEqual(result.status, 'verified')
            self.assertEqual(called, ['test-action'])
            reloaded = FailureMemory(path)
            self.assertEqual(reloaded.last_development_at, 100)
            self.assertEqual(reloaded.last_success_at('HERO_LEVEL'), 100)

    def test_arena_refresh_rereads_and_requires_current_list_change(self):
        after = deepcopy(self.base)
        after.arena.value['opponents'][0]['combat_power'] += 1
        action = self.action('ARENA_REFRESH', {}, {}, 'arena_refresh')
        reads = iter([self.base, self.base, after])
        observed = []
        def read():
            observed.append(1)
            return next(reads)
        result = Actor().simulate(action, self.base, read, lambda _: None)
        self.assertEqual(result.status, 'verified')
        self.assertEqual(len(observed), 3)
        cached_only = deepcopy(self.base)
        cached_only.arena.value['opponent_collections'][1]['records'][0]['combat_power'] += 1
        self.assertFalse(verify(action, self.base, cached_only).verified)

    def test_arena_battle_needs_counters_and_exact_token_change(self):
        before = deepcopy(self.base)
        before.arena.value['stats'] = {'total_offense_battles': 5, 'total_offense_wins': 4}
        after = deepcopy(before)
        after.arena.value['stats'] = {'total_offense_battles': 6, 'total_offense_wins': 5}
        action = self.action('ARENA_BATTLE', before.arena.value['opponents'][0], {'Arena_Token': 1}, 'arena_battle')
        self.assertFalse(verify(action, before, after).verified)
        after.resources.value['current']['values']['Arena_Token'] -= 1
        self.assertEqual(verify(action, before, after).outcome, 'success')
        after.arena.value['stats']['total_offense_wins'] = 4
        self.assertEqual(verify(action, before, after).outcome, 'defeat')

    def test_campaign_exact_target_defeat_updates_failure_baseline(self):
        target = {'area': 1, 'region': 7, 'difficulty': 1, 'number': 6}
        after = deepcopy(self.base)
        row = next(r for r in after.campaign.value['level_stats'] if all(r[k] == v for k, v in target.items()))
        row['defeats'] += 1
        after.resources.value['current']['values']['Energy'] -= 2
        action = self.action('CAMPAIGN_BATTLE', target, {'Energy': 2}, 'campaign_battle')
        memory = FailureMemory()
        reads = iter([self.base, after])
        result = Actor(memory=memory, config={'main_six_ids': self.ids}).simulate(action, self.base, lambda: next(reads), lambda _: None, now=100)
        self.assertEqual(result.status, 'defeat')
        self.assertTrue(memory.has_campaign_defeat(target))
        self.assertFalse(memory.campaign_can_retry(target, after, self.ids, now=9999999))

    def test_campaign_retry_only_after_relevant_main_team_or_equipped_upgrade(self):
        target = {'area': 1, 'region': 7, 'difficulty': 1, 'number': 6}
        with TemporaryDirectory() as directory:
            path = Path(directory)/'memory.json'
            memory = FailureMemory(path)
            memory.record_campaign_defeat(target, self.base, self.ids, now=10)
            changed = deepcopy(self.base)
            changed.resources.value['current']['values']['Gold'] += 10000
            changed.heroes.value[0]['experience'] += 100
            changed.arena.value['own_combat_power'] = {'value': 100000, 'source': 'UserConfig.arena_combat_power'}
            self.assertFalse(FailureMemory(path).campaign_can_retry(target, changed, self.ids))
            changed.heroes.value[0]['level'] += 1
            self.assertTrue(memory.campaign_can_retry(target, changed, self.ids))
            changed = deepcopy(self.base)
            relic = next(r for r in changed.relics.value if r['equipped_hero_id'] in self.ids)
            relic['level'] += 1
            self.assertTrue(memory.campaign_can_retry(target, changed, self.ids))
            self.assertFalse(memory.campaign_can_retry(target, changed, []))

    def test_failure_cooldown_persists_by_target_and_success_clears_it(self):
        action = self.action(costs={'Gold': 1})
        with TemporaryDirectory() as directory:
            path = Path(directory)/'memory.json'
            memory = FailureMemory(path, cooldown_seconds=30)
            memory.record_failure(action, 'no state change', now=10)
            memory.record_failure(action, 'no state change', now=11)
            self.assertTrue(FailureMemory(path).blocked(action, now=20))
            self.assertFalse(memory.blocked(action, now=42))
            memory.record_success(action, now=43)
            self.assertFalse(FailureMemory(path).blocked(action, now=44))

    def test_arena_cooldown_tracks_identity_when_power_name_or_area_changes(self):
        original = self.action('ARENA_BATTLE', {'player_id_bytes': 'same-id', 'name': 'Old', 'combat_power': 2000, 'area': 4}, {'Arena_Token': 1}, 'arena_battle')
        refreshed = self.action('ARENA_BATTLE', {'player_id': 'same-id', 'name': 'New', 'combat_power': 3000, 'area': 101}, {'Arena_Token': 1}, 'arena_battle')
        self.assertEqual(original.key, refreshed.key)
        memory = FailureMemory()
        memory.record_failure(original, 'failed', now=10)
        memory.record_failure(original, 'failed', now=11)
        self.assertTrue(memory.blocked(refreshed, now=20))
        fallback = self.action('ARENA_BATTLE', {'name': 'No-ID', 'combat_power': 2000}, {}, 'arena_battle')
        fallback_refresh = self.action('ARENA_BATTLE', {'name': 'No-ID', 'combat_power': 3000}, {}, 'arena_battle')
        self.assertEqual(fallback.key, fallback_refresh.key)

    def test_apparent_upgrade_cannot_hide_team_or_equipment_regression(self):
        target = {'area': 1, 'region': 7, 'difficulty': 1, 'number': 6}
        memory = FailureMemory()
        memory.record_campaign_defeat(target, self.base, self.ids, now=10)
        for regression in ('hero_level', 'hero_rank', 'unequip', 'reassign', 'relic_level'):
            with self.subTest(regression=regression):
                changed = deepcopy(self.base)
                changed.heroes.value[0]['level'] += 1
                if regression == 'hero_level':
                    changed.heroes.value[1]['level'] -= 1
                elif regression == 'hero_rank':
                    changed.heroes.value[1]['rank'] -= 1
                else:
                    relic = next(r for r in changed.relics.value if r['equipped_hero_id'] in self.ids)
                    if regression == 'unequip':
                        relic['equipped_hero_id'] = None
                    elif regression == 'reassign':
                        relic['equipped_hero_id'] = next(i for i in self.ids if i != relic['equipped_hero_id'])
                    else:
                        relic['level'] -= 1
                self.assertFalse(memory.campaign_can_retry(target, changed, self.ids))

    def test_hero_development_requires_confirmed_main_six_and_nonstorage_target(self):
        target = self.ids[0]
        action = self.action(costs={'Gold': 1})
        self.assertTrue(Safety().evaluate(action, self.base, {'main_six_ids': self.ids}).allowed)
        self.assertFalse(Safety().evaluate(action, self.base, {'main_six_ids': []}).allowed)
        stored = deepcopy(self.base)
        next(h for h in stored.heroes.value if h['inventory_id'] == target)['in_storage'] = True
        self.assertFalse(Safety().evaluate(action, stored, {'main_six_ids': self.ids}).allowed)
        missing = self.action(target={'hero_inventory_id': 99999999}, costs={'Gold': 1})
        self.assertFalse(Safety().evaluate(missing, self.base, {'main_six_ids': self.ids}).allowed)

    def test_corrupt_memory_is_preserved_not_reset(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'memory.json'; original = '{not valid JSON'
            path.write_text(original)
            with self.assertRaises(FailureMemoryError):
                FailureMemory(path)
            self.assertEqual(path.read_text(), original)

    def test_reward_claim_needs_button_and_structured_claim_state(self):
        before = deepcopy(self.base)
        completed = next(q for q in before.quests.value if q['state'] == 'Completed')
        action = Action('claim', 'QUEST_CLAIM', 'quests', {'quest_id': completed['quest_id']},
                        preconditions={'reward_button_text': 'ANNEHMEN', 'quest_group': 'Monthly'},
                        expected_effects={'type': 'quest_claim'})
        self.assertTrue(Safety().evaluate(action, before).allowed)
        missing = deepcopy(before)
        missing.quests.value = [q for q in missing.quests.value if q['quest_id'] != completed['quest_id']]
        self.assertFalse(verify(action, before, missing).verified)
        after = deepcopy(before)
        next(q for q in after.quests.value if q['quest_id'] == completed['quest_id'])['state'] = 'Claimed'
        memory = FailureMemory(); reads = iter([before, after])
        self.assertEqual(Actor(memory=memory).simulate(action, before, lambda: next(reads), lambda _: None, now=200,
                                                     vision_evidence=LocatedTarget('ANNEHMEN', 10, 20, .99, observed_at=200)).status, 'verified')
        self.assertEqual(memory.last_success_at('MONTHLY_REVIEW'), 200)

    def test_claim_requires_independent_fresh_vision_not_planner_button_string(self):
        completed = next(q for q in self.base.quests.value if q['state'] == 'Completed')
        action = Action('claim', 'QUEST_CLAIM', 'quests', {'quest_id': completed['quest_id']},
                        preconditions={'reward_button_text': 'ANNEHMEN'}, expected_effects={'type': 'quest_claim'})
        called = []
        for evidence in (None, LocatedTarget('ANNEHMEN', 10, 20, .99, observed_at=100),
                         LocatedTarget('Belohnung', 10, 20, .99, observed_at=200)):
            result = Actor().simulate(action, self.base, lambda: self.base, lambda _: called.append(1),
                                      now=200, vision_evidence=evidence)
            self.assertEqual(result.status, 'blocked')
        self.assertEqual(called, [])

    def quest_claim_counter_states(self):
        # A synthetic transition layered over real quest records. Raw Windows
        # reward-claim transitions have not yet validated this effect contract.
        before = deepcopy(self.base)
        completed = next(q for q in before.quests.value if q['state'] == 'Completed')
        prototype = completed['prototype_id']
        before.quest_log = Observation({'completed_prototype_ids': [prototype, prototype, 999],
                                        'total_completed_quests': 100}, 'available', 'structured', ['PlayerQuestsModel.dat'])
        after = deepcopy(before)
        after.quests.value = [q for q in after.quests.value if q['quest_id'] != completed['quest_id']]
        after.quest_log.value['completed_prototype_ids'].append(prototype)
        after.quest_log.value['total_completed_quests'] += 1
        action = Action('claim', 'QUEST_CLAIM', 'quests', {'quest_id': completed['quest_id']},
                        preconditions={'reward_button_text': 'ANNEHMEN'}, expected_effects={'type': 'quest_claim'})
        return before, after, action

    def test_quest_claim_target_removal_requires_exact_repeated_prototype_accounting(self):
        before, after, action = self.quest_claim_counter_states()
        result = verify(action, before, after)
        self.assertTrue(result.verified)
        self.assertEqual(result.evidence['completed_total_delta'], 1)
        self.assertIn('synthetic', result.evidence['validation'])
        reads = iter([before, after])
        outcome = Actor().simulate(action, before, lambda: next(reads), lambda _: None, now=200,
                                   vision_evidence=LocatedTarget('ANNEHMEN', 10, 20, .99, observed_at=200))
        self.assertEqual(outcome.status, 'verified')

    def test_quest_claim_accounting_rejects_wrong_delta_or_unrelated_removal(self):
        for fault in ('missing_log', 'wrong_prototype', 'missing_total', 'total_jump', 'removed_history', 'other_quest_removed'):
            with self.subTest(fault=fault):
                before, after, action = self.quest_claim_counter_states()
                if fault == 'missing_log':
                    after.quest_log.status = 'unknown'
                elif fault == 'wrong_prototype':
                    after.quest_log.value['completed_prototype_ids'][-1] = 888
                elif fault == 'missing_total':
                    after.quest_log.value['total_completed_quests'] -= 1
                elif fault == 'total_jump':
                    after.quest_log.value['total_completed_quests'] += 1
                elif fault == 'removed_history':
                    after.quest_log.value['completed_prototype_ids'].remove(999)
                elif fault == 'other_quest_removed':
                    after.quests.value.pop()
                self.assertFalse(verify(action, before, after).verified)

    def test_vision_locates_intended_identity_and_rejects_ambiguity(self):
        rows = [{'text': 'Ellesher', 'conf': .99, 'x': 10, 'y': 20},
                {'text': 'TomTomson', 'conf': .95, 'x': 30, 'y': 40}]
        self.assertEqual(locate_intended_label('TomTomson', rows).x, 30)
        self.assertIsNone(locate_intended_label('TomTomson', rows + [rows[1]]))
        self.assertIsNone(locate_intended_label('unknown', rows))


if __name__ == '__main__':
    unittest.main()
