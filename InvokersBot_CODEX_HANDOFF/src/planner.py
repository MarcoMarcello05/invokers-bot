"""Pure account planner: GameState + UserConfig + failure memory -> concrete intent.

No filesystem, screen capture, OCR, clicking or resource mutation belongs here.
Category priority is lexicographic; lower-tier synergy cannot outrank Daily.
Execution readiness is a separate Safety/Actor concern.
"""
from dataclasses import dataclass, field, replace
import hashlib
import json

from bot_actions import Action
from safety import Safety

QUEST_PRIORITY = {'Daily': 0, 'Advance': 1, 'Progress': 1, 'Weekly': 2,
                  'Monthly': 3, 'Clan': 4, 'Achievements': 5}
BATTLE_AREAS = {'CAMPAIGN_BATTLE': 1, 'BOSS_BATTLE': 2, 'ARENA_BATTLE': 4, 'CLAN_BOSS_BATTLE': 6}


def available(state, name, default=None):
    observation = getattr(state, name, None)
    return observation.value if observation is not None and observation.status == 'available' else default


def campaign_target(row):
    return {key: row[key] for key in ('area', 'region', 'difficulty', 'number')}


def make_action(kind, module, target=None, costs=None, effects=None, reasons=(), preconditions=None):
    target = target or {}
    identity = kind + '|' + json.dumps(target, sort_keys=True, separators=(',', ':'))
    return Action(hashlib.sha256(identity.encode()).hexdigest()[:20], kind, module,
                  target=target, resource_costs=costs, preconditions=preconditions or {},
                  expected_effects=effects or {}, reasons=tuple(reasons))


@dataclass
class PlannedAction:
    action: Action
    priority: int = 6
    synergy_score: int = 0
    covered_quest_ids: list[int] = field(default_factory=list)
    blocked_reasons: list[str] = field(default_factory=list)
    safety_reasons: list[str] = field(default_factory=list)

    def to_dict(self):
        result = self.action.to_dict()
        result.update(priority=self.priority, synergy_score=self.synergy_score,
                      covered_quest_ids=self.covered_quest_ids,
                      blocked=bool(self.blocked_reasons), block_reasons=self.blocked_reasons,
                      safety_reasons=self.safety_reasons, execution_ready=False)
        return result


@dataclass
class Plan:
    generated_at: float
    queue: list[PlannedAction]
    main_team_ids: list[int]
    mode: str = 'DRY_RUN'
    actor_enabled: bool = False

    @property
    def next_action(self):
        return next((job for job in self.queue if not job.blocked_reasons), None)

    def to_dict(self):
        return {'schema_version': 2, 'generated_at': self.generated_at, 'mode': self.mode,
                'actor_enabled': False, 'main_team_ids': self.main_team_ids,
                'next_action': self.next_action.to_dict() if self.next_action else None,
                'queue': [job.to_dict() for job in self.queue],
                'executable_queue': [], 'next_executable': None,
                'safety': {'gems_allowed': False, 'premium_spend_allowed': False,
                           'live_handlers_enabled': False}}


def quest_group(quest):
    return quest.get('group') or 'Achievements'


def quest_matches(action, quest):
    """Count only overlaps proven by structured objectives and exact constraints."""
    if quest.get('state') not in ('New', 'InProgress', 'Completed'):
        return False
    if quest.get('state') == 'Completed':
        return action.kind == 'QUEST_CLAIM' and action.target.get('quest_id') == quest['quest_id']
    objective = quest.get('action')
    if action.kind == 'HERO_LEVEL':
        # Hero-specific constraints are not decoded yet; do not assume their overlap.
        return objective == 'HeroLevelUp' and quest.get('conditions_decoded') is True and not quest.get('conditions')
    if action.kind == 'SUMMON_WILDSTAR':
        return objective in ('HeroSummon', 'HeroOrAnimaSummon') and quest.get('conditions_decoded') is True and not quest.get('conditions')
    if objective != 'BattleFinish' or action.kind not in BATTLE_AREAS or not quest.get('conditions_decoded'):
        return False
    conditions = quest.get('conditions')
    if not conditions:
        return False
    for condition in conditions:
        if condition.get('type') != 'Battle':
            return False
        target = action.target
        if condition.get('area_id') is not None and condition['area_id'] != BATTLE_AREAS[action.kind]:
            return False
        for source, key in [('region_id', 'region'), ('difficulty_id', 'difficulty'), ('number', 'number')]:
            if condition.get(source) is not None and condition[source] != target.get(key):
                return False
        for source, key in [('region_ids', 'region'), ('numbers', 'number')]:
            if condition.get(source) and target.get(key) not in condition[source]:
                return False
        if condition.get('min_number') is not None and target.get('number', -1) < condition['min_number']:
            return False
        if any(condition.get(key) is not None for key in
               ('auto_battle', 'animas_count', 'collect_stars', 'clan_boss_damage_difficulty_id')):
            return False
    return True


class Planner:
    def __init__(self, safety=None):
        self.safety = safety or Safety()

    def plan(self, state, config, memory, now):
        jobs = []
        heroes = available(state, 'heroes', [])
        quests = available(state, 'quests', [])
        by_id = {hero['inventory_id']: hero for hero in heroes}
        main_ids = list(config.main_six_ids)
        main_valid = len(main_ids) == 6 and all(i in by_id for i in main_ids)

        def add(action, priority=6, blocked=None):
            job = PlannedAction(action, priority, blocked_reasons=list(blocked or []))
            if not getattr(config.modules, action.module, True):
                job.blocked_reasons.append(f'Module {action.module} disabled in UserConfig')
            if memory.blocked(action, now=now):
                job.blocked_reasons.append('Failure-memory cooldown: avoid repeating the same failed action')
            jobs.append(job)
            return job

        # Regular account development is independent of the existence of any quest.
        due = memory.last_development_at is None or now - memory.last_development_at >= config.main_team_interval_seconds
        if main_valid:
            weakest = min((by_id[i] for i in main_ids), key=lambda h: (h['level'], h['rank'], h['inventory_id']))
            add(make_action('HERO_LEVEL', 'invokers', {'hero_inventory_id': weakest['inventory_id']},
                            effects={'type': 'hero_level'}, reasons=('Regular development of confirmed Main Six',),
                            preconditions={'main_team_ids': main_ids, 'costs_verified': False}),
                -1 if due else 6)
        else:
            add(make_action('MAIN_TEAM_REVIEW', 'invokers', reasons=('Confirm the six UI hero IDs in UserConfig; serialized order is not UI order',)),
                -1 if due else 6)

        campaign = available(state, 'campaign', {})
        rows = campaign.get('level_stats', [])
        normal = [row for row in rows if row['area'] == 1 and row['difficulty'] == 1]
        safe = sorted((r for r in normal if r['victories'] > 0), key=lambda r: (r['region'], r['number']))
        failed = sorted((r for r in normal if r['victories'] == 0 and r['defeats'] > 0), key=lambda r: (r['region'], r['number']))
        if safe:
            add(make_action('CAMPAIGN_BATTLE', 'campaign', campaign_target(safe[-1]),
                            effects={'type': 'campaign_battle'}, reasons=('Farm a structurally proven won stage',),
                            preconditions={'purpose': 'safe_farm', 'costs_verified': False}), 6)
        if failed:
            target = campaign_target(failed[0])
            allowed = main_valid and memory.has_campaign_defeat(target) and memory.campaign_can_retry(target, state, main_ids)
            add(make_action('CAMPAIGN_BATTLE', 'campaign', target,
                            effects={'type': 'campaign_battle'}, reasons=('Progress target with known defeat; require relevant account improvement',),
                            preconditions={'purpose': 'progress', 'main_team_ids': main_ids, 'costs_verified': False}),
                6, [] if allowed else ['Known campaign defeat: no verified relevant Main Six improvement since the failure baseline'])
        elif not normal:
            add(make_action('QUEST_REVIEW', 'campaign', reasons=('Campaign state unavailable; do not guess a stage',)), 6)
        else:
            unbeaten = [r for r in normal if r['victories'] == 0 and r['defeats'] == 0]
            if unbeaten:
                target = campaign_target(min(unbeaten, key=lambda r: (r['region'], r['number'])))
                add(make_action('CAMPAIGN_BATTLE', 'campaign', target, effects={'type': 'campaign_battle'},
                                preconditions={'purpose': 'progress', 'costs_verified': False}))
            else:
                add(make_action('CAMPAIGN_REVIEW', 'campaign', reasons=('Next unlocked campaign stage is not decoded; never invent stage/chapter bounds',)), 7)

        # Dungeon rows are in the same structured LevelStats collection. Farm only
        # proven wins, independently from quests; never push a recorded failed boss.
        dungeon_safe = {}
        for row in rows:
            if row['area'] == 2 and row['victories'] > 0:
                key = (row['region'], row['difficulty'])
                if key not in dungeon_safe or row['number'] > dungeon_safe[key]['number']:
                    dungeon_safe[key] = row
        for row in dungeon_safe.values():
            add(make_action('BOSS_BATTLE', 'bosses', campaign_target(row),
                            effects={'type': 'campaign_battle'},
                            preconditions={'purpose': 'safe_boss_farm', 'costs_verified': False},
                            reasons=('Farm exact structurally won dungeon stage; no blind push into known defeat',)), 6)

        arena = available(state, 'arena', {})
        power = arena.get('own_combat_power', {})
        own_power = power.get('value') if power.get('source') == 'UserConfig.arena_combat_power' else None
        current = arena.get('opponents', [])
        candidates = sorted((r for r in current if own_power is not None and r['combat_power'] < own_power),
                            key=lambda r: (r['combat_power'], r['arena_points'], r['name']))
        eligible = []
        for opponent in candidates:
            target = {'name': opponent['name'], 'player_id_bytes': opponent['player_id_bytes'],
                      'combat_power': opponent['combat_power'], 'area': 4}
            action = make_action('ARENA_BATTLE', 'arena', target, effects={'type': 'arena_battle'},
                                 preconditions={'costs_verified': False, 'reread_after_action': True},
                                 reasons=('Lowest structured current opponent below authoritative UserConfig power',))
            if not memory.blocked(action, now=now):
                eligible.append(action)
        if eligible:
            add(eligible[0])
        elif own_power is None:
            add(make_action('QUEST_REVIEW', 'arena', reasons=('Set authoritative arena_combat_power in UserConfig; OCR cannot override it',)))
        else:
            add(make_action('ARENA_REFRESH', 'arena', effects={'type': 'arena_refresh'},
                            preconditions={'costs_verified': False, 'reread_after_action': True},
                            reasons=('No eligible current opponent below configured power; refresh requires verified nonpremium cost',)))

        balances = (available(state, 'resources', {}).get('current') or {}).get('values', {})
        if balances.get('SI_WildStar', 0) > config.resource_reserves.get('SI_WildStar', 0):
            add(make_action('SUMMON_WILDSTAR', 'invokers', {'count': 1, 'currency': 'SI_WildStar'},
                            costs={'SI_WildStar': 1}, effects={'type': 'wildstar_summon'},
                            preconditions={'costs_verified': True, 'cost_source': 'single green WildStar action contract'},
                            reasons=('Green Wild Star only; single summon, no premium substitute',)), 6)
        add(make_action('RESOURCE_REVIEW', 'invokers', reasons=('Resource reserves apply to every spending intent; unknown costs remain locked',)), 8)

        # Concrete claims and specific battle intents originate in quest data, never OCR.
        monthly_due = memory.last_success_at('MONTHLY_REVIEW') is None or now - memory.last_success_at('MONTHLY_REVIEW') >= 1800
        for quest in quests:
            group = quest_group(quest)
            priority = QUEST_PRIORITY.get(group, 5)
            if group == 'Monthly' and not monthly_due:
                continue
            if quest.get('state') not in ('New', 'InProgress', 'Completed'):
                continue
            if quest.get('state') == 'Completed':
                add(make_action('QUEST_CLAIM', 'quests', {'quest_id': quest['quest_id']}, costs={},
                                effects={'type': 'quest_claim'}, reasons=(f'{group} completed objective; require exact ANNEHMEN confirmation',),
                                preconditions={'costs_verified': True, 'reward_button_text': 'ANNEHMEN', 'quest_group': group}), priority)
                continue
            if quest.get('action') == 'ShopPurchase':
                add(make_action('SHOP_PURCHASE', 'quests', {'quest_id': quest['quest_id']},
                                reasons=('Premium/shop actions are hard blocked regardless of quest score',)), priority,
                    ['Purchases are not allowed by account policy'])
                continue
            if quest.get('action') == 'BattleFinish' and quest.get('conditions_decoded'):
                for condition in quest.get('conditions', []):
                    if condition.get('type') != 'Battle':
                        continue
                    area = condition.get('area_id')
                    if area == 1 and condition.get('region_id') is not None and condition.get('number') is not None:
                        target = {'area': 1, 'region': condition['region_id'], 'difficulty': condition.get('difficulty_id') or 1,
                                  'number': condition['number']}
                        if not any(j.action.kind == 'CAMPAIGN_BATTLE' and j.action.target == target for j in jobs):
                            known = next((r for r in rows if campaign_target(r) == target), None)
                            blocked = []
                            if known is None:
                                blocked.append('Quest stage availability is not known')
                            elif known['defeats'] > 0 and known['victories'] == 0 and not (main_valid and memory.has_campaign_defeat(target) and memory.campaign_can_retry(target, state, main_ids)):
                                blocked.append('Known campaign defeat requires relevant Main Six improvement')
                            add(make_action('CAMPAIGN_BATTLE', 'campaign', target, effects={'type': 'campaign_battle'},
                                            preconditions={'costs_verified': False}, reasons=('Exact structured campaign quest target',)), priority, blocked)
                    elif area in (2, 6):
                        target = {'area': area, 'region': condition.get('region_id'), 'difficulty': condition.get('difficulty_id'),
                                  'number': condition.get('number')}
                        exact = target['region'] is not None and target['difficulty'] is not None and target['number'] is not None
                        kind = 'BOSS_BATTLE' if area == 2 else 'CLAN_BOSS_BATTLE'
                        add(make_action(kind, 'bosses', target, effects={'type': 'campaign_battle'},
                                        preconditions={'costs_verified': False}, reasons=('Structured boss objective; resolve exact stage and costs before execution',)),
                            priority, [] if exact else ['Boss target/difficulty/cost contract is incomplete'])
            if quest_group(quest) not in ('Achievements', 'Book') and (not quest.get('action') or not quest.get('conditions_decoded')):
                add(make_action('QUEST_REVIEW', 'quests', {'quest_id': quest['quest_id']},
                                reasons=('Quest objective/conditions are not sufficiently decoded',)), priority)

        # Synergy augments a category; it never changes the category ordering.
        for job in jobs:
            matches = [q for q in quests if quest_matches(job.action, q)
                       and (quest_group(q) != 'Monthly' or monthly_due)] if config.modules.quests else []
            if matches:
                job.covered_quest_ids = sorted({q['quest_id'] for q in matches})
                job.priority = min(job.priority, *(QUEST_PRIORITY.get(quest_group(q), 5) for q in matches))
                job.synergy_score = 100 * len(job.covered_quest_ids) + sum(min(99, q.get('progress', 0)) for q in matches)
            if job.action.module == 'quests' and not config.modules.quests:
                job.blocked_reasons.append('Quest module disabled')

        events = available(state, 'events', {})
        event_records = events.get('tournaments', [])
        for job in jobs:
            # Runtime definition must be validated and in its scoring window.
            # Historical participation or a source score alone is not a live event rule.
            for event in event_records if config.modules.events else []:
                definition = event.get('definition') or {}
                if definition.get('validated') is not True or event.get('scoring_completed'):
                    continue
                if not (definition.get('starts_at_epoch', float('inf')) <= now < definition.get('scoring_ends_at_epoch', float('-inf'))):
                    continue
                if definition.get('action_kind') == job.action.kind:
                    constraints = definition.get('target', {})
                    if all(job.action.target.get(k) == v for k, v in constraints.items()):
                        job.synergy_score += 75
        add(make_action('EVENT_REVIEW', 'events', reasons=('Use validated active event definitions for bonuses; unknown runtime catalog never invents priorities',)), 8)
        add(make_action('RELIC_REVIEW', 'relics', reasons=('Protect equipped/rare relics; raw bonus values do not establish sale/upgrade value or costs',)), 8)
        add(make_action('BOSS_REVIEW', 'bosses', reasons=('Boss snapshots inform availability; missing exact battle conditions remain unknown',)), 8)

        # Merge the same concrete intent while retaining all primary objectives.
        merged = {}
        for job in jobs:
            key = job.action.key
            if key in merged:
                previous = merged[key]
                previous.priority = min(previous.priority, job.priority)
                previous.synergy_score = max(previous.synergy_score, job.synergy_score)
                previous.covered_quest_ids = sorted(set(previous.covered_quest_ids + job.covered_quest_ids))
                previous.blocked_reasons = sorted(set(previous.blocked_reasons + job.blocked_reasons))
            else:
                merged[key] = job
        jobs = list(merged.values())
        for job in jobs:
            decision = self.safety.evaluate(job.action, state, config)
            job.safety_reasons = list(decision.reasons)
            job.action = replace(job.action, score=job.synergy_score)
        jobs.sort(key=lambda job: (bool(job.blocked_reasons), job.priority, -job.synergy_score, job.action.action_id))
        return Plan(now, jobs, main_ids if main_valid else [])
