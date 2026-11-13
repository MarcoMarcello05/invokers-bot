"""Non-configurable safety gates, evaluated again immediately before execution."""
from dataclasses import dataclass
from bot_actions import Action, hero_values, resource_values, section_value


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reasons: tuple[str, ...] = ()


READ_ONLY_KINDS = frozenset({'OBSERVE', 'MAIN_TEAM_REVIEW', 'EVENT_REVIEW', 'RELIC_REVIEW',
                            'QUEST_REVIEW', 'RESOURCE_REVIEW', 'BOSS_REVIEW',
                            'CAMPAIGN_REVIEW', 'ARENA_REVIEW'})
SPENDING_KINDS = frozenset({'HERO_LEVEL', 'HERO_AWAKE', 'HERO_ASCEND', 'ARENA_BATTLE',
                           'ARENA_REFRESH', 'CAMPAIGN_BATTLE', 'CAMPAIGN_FARM',
                           'CAMPAIGN_PROGRESS', 'BOSS_BATTLE', 'SUMMON_WILDSTAR'})
KNOWN_KINDS = READ_ONLY_KINDS | SPENDING_KINDS | {'QUEST_CLAIM'}
SAFE_CURRENCIES = frozenset({'Gold', 'Energy', 'Memorium', 'Arena_Token', 'ArenaToken',
                             'SI_WildStar', 'WildStar', 'ClanBossKey', 'ClanBoss1Key', 'ClanBoss2Key'})
PREMIUM_NAMES = frozenset({'gem', 'gems', 'premium', 'diamond', 'diamonds', '1'})
ACTION_MODULES = {'HERO_LEVEL': 'invokers', 'HERO_AWAKE': 'invokers', 'HERO_ASCEND': 'invokers',
                  'SUMMON_WILDSTAR': 'invokers', 'ARENA_BATTLE': 'arena', 'ARENA_REFRESH': 'arena',
                  'CAMPAIGN_BATTLE': 'campaign', 'CAMPAIGN_FARM': 'campaign', 'CAMPAIGN_PROGRESS': 'campaign',
                  'BOSS_BATTLE': 'bosses', 'QUEST_CLAIM': 'quests'}


def _config_value(config, name, default):
    if config is None:
        return default
    return config.get(name, default) if isinstance(config, dict) else getattr(config, name, default)


def _canonical_currency(name):
    return {'ArenaToken': 'Arena_Token', 'WildStar': 'SI_WildStar'}.get(name, name)


class Safety:
    def evaluate(self, action: Action, state, config=None) -> SafetyDecision:
        reasons = []
        upper = action.kind.upper()
        modules = _config_value(config, 'modules', None)
        if modules is not None:
            enabled = modules.get(action.module) if isinstance(modules, dict) else getattr(modules, action.module, None)
            if enabled is not True:
                reasons.append('Action module is disabled or unknown in UserConfig')
        if action.kind in ACTION_MODULES and action.module != ACTION_MODULES[action.kind]:
            reasons.append('Action kind does not belong to its declared module')
        if any(word in upper for word in ('PURCHASE', 'SHOP', 'PREMIUM', 'GEM', 'SEND_AWAY', 'RELIC_SELL', 'RELIC_DESTROY', 'RELIC_UPGRADE')):
            reasons.append('Premium purchases and unvalidated destructive/value actions are hard blocked')
        if action.kind not in KNOWN_KINDS:
            reasons.append('No validated policy contract for this action kind')
        if action.preconditions.get('premium') or action.target.get('premium'):
            reasons.append('Premium actions are forbidden')
        if action.kind in ('HERO_LEVEL', 'HERO_AWAKE', 'HERO_ASCEND'):
            inventory_id = action.target.get('hero_inventory_id', action.target.get('inventory_id'))
            hero = next((h for h in hero_values(state) or [] if h.get('inventory_id') == inventory_id), None)
            if hero is None or hero.get('in_storage') is not False:
                reasons.append('Development target must be an existing non-storage Invoker')
            if config is not None and inventory_id not in _config_value(config, 'main_six_ids', []):
                reasons.append('Development target is outside the confirmed Main Six')
        costs = action.resource_costs
        if action.kind in SPENDING_KINDS and (costs is None or action.preconditions.get('costs_verified') is not True):
            reasons.append('Exact resource costs are unknown or unverified')
        if costs is not None:
            if not isinstance(costs, dict):
                reasons.append('Resource costs must be a validated dictionary')
            else:
                balances = resource_values(state)
                reserves = _config_value(config, 'resource_reserves', {})
                if not isinstance(reserves, dict):
                    reasons.append('Invalid resource reserve configuration')
                    reserves = {}
                totals = {}
                for currency, amount in costs.items():
                    if not isinstance(currency, str):
                        reasons.append('Unknown currency identity')
                        continue
                    if currency.lower() in PREMIUM_NAMES or 'premium' in currency.lower() or 'gem' in currency.lower():
                        reasons.append('Gems and premium currency are forbidden, including zero-cost claims')
                        continue
                    if currency not in SAFE_CURRENCIES:
                        reasons.append('Unknown/unapproved spending currency: ' + currency)
                        continue
                    if type(amount) is not int or amount < 0:
                        reasons.append('Cost must be a nonnegative exact integer')
                        continue
                    canonical = _canonical_currency(currency)
                    totals[canonical] = totals.get(canonical, 0) + amount
                for canonical, amount in totals.items():
                    currency = canonical
                    balance = balances.get(canonical, balances.get(currency))
                    reserve_values = [v for k, v in reserves.items() if _canonical_currency(k) == canonical]
                    reserve = max(reserve_values or [0]) if all(type(v) is int for v in reserve_values) else None
                    if type(reserve) is not int or reserve < 0:
                        reasons.append('Resource reserve is invalid: ' + currency)
                    elif type(balance) is not int:
                        reasons.append('Resource balance unknown: ' + currency)
                    elif balance - amount < reserve:
                        reasons.append('Insufficient resource above reserve: ' + currency)
        if action.kind == 'ARENA_BATTLE':
            arena = section_value(state, 'arena') or {}
            opponents = arena.get('opponents', [])
            target = next((o for o in opponents if _same_opponent(o, action.target)), None)
            power_info = arena.get('own_combat_power', {})
            power = power_info.get('value')
            if power_info.get('source') not in ('UserConfig.arena_combat_power', 'user_config.arena_combat_power'):
                reasons.append('Own Arena strength must come from authoritative UserConfig')
            if type(power) is not int or power <= 0:
                reasons.append('Own Arena strength is unknown')
            if target is None:
                reasons.append('Target is absent from the current structured Arena list')
            elif type(power) is int and target.get('combat_power', power) >= power:
                reasons.append('Opponent must be strictly weaker than own configured strength')
        if action.kind == 'QUEST_CLAIM':
            quests = section_value(state, 'quests')
            quest = next((q for q in quests or [] if q.get('quest_id') == action.target.get('quest_id')), None)
            if quest is None or quest.get('state') != 'Completed':
                reasons.append('Quest reward requires structured completed quest state')
            if action.preconditions.get('reward_button_text') != 'ANNEHMEN':
                reasons.append('Reward action requires an explicit ANNEHMEN button precondition')
        if action.kind == 'SUMMON_WILDSTAR':
            if not costs or any(_canonical_currency(c) != 'SI_WildStar' for c in costs):
                reasons.append('Summoning may spend green WildStar only')
        # The guard stays explicit even though send-away is not a registered action.
        if 'SEND_AWAY' in upper:
            heroes = hero_values(state)
            count = action.target.get('count')
            if heroes is None or type(count) is not int or len(heroes) - count < 30:
                reasons.append('At least 30 Invokers must remain')
        return SafetyDecision(not reasons, tuple(dict.fromkeys(reasons)))


def _same_opponent(record, target):
    target_id = target.get('player_id_bytes', target.get('player_id'))
    if target_id is not None:
        return record.get('player_id_bytes', record.get('player_id')) == target_id
    return record.get('name') == target.get('name') and record.get('combat_power') == target.get('combat_power')
