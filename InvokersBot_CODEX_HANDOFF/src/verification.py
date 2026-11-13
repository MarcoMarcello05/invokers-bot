"""Verify explicit structured effects, never a click, screenshot or hash alone."""
from dataclasses import dataclass, field
from collections import Counter
from bot_actions import hero_values, resource_values, section_value


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    outcome: str
    reason: str
    evidence: dict = field(default_factory=dict)


def arena_signature(state):
    arena = section_value(state, 'arena')
    if arena is None:
        return None
    return tuple(sorted((str(o.get('player_id_bytes', o.get('player_id', ''))),
                         o.get('name', ''), o.get('combat_power'), o.get('arena_points'))
                        for o in arena.get('opponents', [])))


def _costs_observed(action, before, after):
    if action.resource_costs is None:
        return False
    old, new = resource_values(before), resource_values(after)
    for currency, cost in action.resource_costs.items():
        key = {'ArenaToken': 'Arena_Token', 'WildStar': 'SI_WildStar'}.get(currency, currency)
        if type(old.get(key)) is not int or type(new.get(key)) is not int or old[key] - new[key] != cost:
            return False
    return True


def _level_row(state, target):
    campaign = section_value(state, 'campaign')
    if campaign is None:
        return None, False
    rows = campaign.get('level_stats', [])
    keys = ('area', 'region', 'difficulty', 'number')
    return next((r for r in rows if all(r.get(k) == target.get(k) for k in keys)), None), True


def verify(action, before, after):
    effect = action.expected_effects.get('type')
    unknown = lambda reason: VerificationResult(False, 'unknown', reason)
    old_resources, new_resources = resource_values(before), resource_values(after)
    declared = {{'ArenaToken': 'Arena_Token', 'WildStar': 'SI_WildStar'}.get(k, k)
                for k in action.resource_costs or {}}
    for currency, amount in old_resources.items():
        current = new_resources.get(currency)
        if type(amount) is int and type(current) is int and current < amount and currency not in declared:
            return unknown('Unexpected resource decrease outside the declared contract: ' + currency)
    if effect == 'arena_refresh':
        old, new = arena_signature(before), arena_signature(after)
        if old is None or new is None:
            return unknown('Current structured Arena list unavailable')
        if old == new:
            return unknown('Current Arena list has not semantically changed')
        if not _costs_observed(action, before, after):
            return unknown('Refresh resource delta not confirmed')
        return VerificationResult(True, 'success', 'Current Arena list changed after reread', {'before': old, 'after': new})
    if effect == 'arena_battle':
        old, new = section_value(before, 'arena'), section_value(after, 'arena')
        old_stats, new_stats = (old or {}).get('stats', {}), (new or {}).get('stats', {})
        battles = 'total_offense_battles'
        wins = 'total_offense_wins'
        if any(type(s.get(k)) is not int for s in (old_stats, new_stats) for k in (battles, wins)):
            return unknown('Structured Arena battle/win counters unavailable')
        if new_stats[battles] - old_stats[battles] != 1 or not _costs_observed(action, before, after):
            return unknown('Exactly one Arena battle and its resource delta must be confirmed')
        win_delta = new_stats[wins] - old_stats[wins]
        if win_delta not in (0, 1):
            return unknown('Arena win counters are inconsistent')
        # Reading these signatures is deliberate: callers supply fresh GameState
        # after action; pooled/cache records are never used to verify result.
        if arena_signature(after) is None:
            return unknown('Current Arena list was not reread')
        return VerificationResult(True, 'success' if win_delta else 'defeat',
                                  'Arena result confirmed by structured counters and resources',
                                  {'battle_delta': 1, 'win_delta': win_delta})
    if effect == 'campaign_battle':
        old, old_known = _level_row(before, action.target)
        new, new_known = _level_row(after, action.target)
        if not old_known or not new_known or new is None:
            return unknown('Exact campaign target statistics unavailable')
        old = old or {'victories': 0, 'defeats': 0}
        wins = new.get('victories', 0) - old.get('victories', 0)
        losses = new.get('defeats', 0) - old.get('defeats', 0)
        if (wins, losses) not in ((1, 0), (0, 1)):
            return unknown('No unambiguous single result for the intended campaign level')
        if not _costs_observed(action, before, after):
            return unknown('Campaign resource delta not confirmed')
        return VerificationResult(True, 'success' if wins else 'defeat',
                                  'Exact campaign level result confirmed', {'victory_delta': wins, 'defeat_delta': losses})
    if effect == 'hero_level':
        target = action.target.get('hero_inventory_id', action.target.get('inventory_id'))
        old = next((h for h in hero_values(before) or [] if h.get('inventory_id') == target), None)
        new = next((h for h in hero_values(after) or [] if h.get('inventory_id') == target), None)
        if old is None or new is None or new.get('level', -1) <= old.get('level', -1):
            return unknown('Target hero level increase not confirmed')
        if not _costs_observed(action, before, after):
            return unknown('Hero development resource delta not confirmed')
        return VerificationResult(True, 'success', 'Intended hero level increased', {'before_level': old['level'], 'after_level': new['level']})
    if effect == 'quest_claim':
        target = action.target.get('quest_id')
        old_quests, new_quests = section_value(before, 'quests'), section_value(after, 'quests')
        if old_quests is None or new_quests is None:
            return unknown('Structured active quest inventories are unavailable')
        old = next((q for q in old_quests if q.get('quest_id') == target), None)
        new = next((q for q in new_quests if q.get('quest_id') == target), None)
        if not old or old.get('state') != 'Completed':
            return unknown('Quest claim requires the intended quest to be completed before the action')
        if new is None:
            old_log, new_log = section_value(before, 'quest_log'), section_value(after, 'quest_log')
            prototype = old.get('prototype_id')
            if old_log is None or new_log is None or type(prototype) is not int:
                return unknown('Disappearance alone cannot confirm a quest claim; structured completion accounting is unavailable')
            old_completed, new_completed = old_log.get('completed_prototype_ids'), new_log.get('completed_prototype_ids')
            old_total, new_total = old_log.get('total_completed_quests'), new_log.get('total_completed_quests')
            if not isinstance(old_completed, list) or not isinstance(new_completed, list) or any(type(p) is not int for p in old_completed + new_completed):
                return unknown('Completion history must retain the full prototype-ID list, including repeats')
            if type(old_total) is not int or type(new_total) is not int or new_total != old_total + 1:
                return unknown('Exactly one structured quest completion counter increment is required')
            old_counts, new_counts = Counter(old_completed), Counter(new_completed)
            if old_counts - new_counts or new_counts - old_counts != Counter({prototype: 1}):
                return unknown('Completion history delta does not account for exactly the intended prototype')
            old_ids = {q.get('quest_id') for q in old_quests}
            new_ids = {q.get('quest_id') for q in new_quests}
            if old_ids - new_ids != {target}:
                return unknown('An unrelated active quest disappeared during the claim')
            return VerificationResult(True, 'success', 'Intended quest removal and exact structured completion accounting agree',
                                      {'quest_id': target, 'prototype_id': prototype, 'completed_total_delta': 1,
                                       'completion_prototype_delta': {prototype: 1},
                                       'validation': 'synthetic_transition_contract; Windows transition capture still required'})
        if new.get('state') not in ('Claimed', 'Rewarded') and new.get('reward_claimed') is not True:
            return unknown('Structured reward-claimed state is not confirmed; disappearance alone is insufficient')
        return VerificationResult(True, 'success', 'Intended quest reward state confirmed')
    if effect == 'wildstar_summon':
        old, new = hero_values(before), hero_values(after)
        if old is None or new is None or len(new) <= len(old) or not _costs_observed(action, before, after):
            return unknown('New inventory hero and exact green-star spend are both required')
        if {h['inventory_id'] for h in old} >= {h['inventory_id'] for h in new}:
            return unknown('No new hero inventory ID confirmed')
        return VerificationResult(True, 'success', 'New hero inventory and WildStar delta confirmed')
    return unknown('No tested verification contract for this expected effect')
