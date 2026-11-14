"""Deterministic diagnostic matchup ranking. Never authorizes game input."""
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from math import isfinite
import time


class PowerSource(str, Enum):
    STRUCTURED_LAST_META_BATTLE_SETUP = "STRUCTURED_LAST_META_BATTLE_SETUP"
    EXACT_LOCAL_CALCULATOR = "EXACT_LOCAL_CALCULATOR"
    PREBATTLE_NUMERIC_ROI = "PREBATTLE_NUMERIC_ROI"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class OwnPower:
    value: int | None
    source: PowerSource
    observed_at: float
    digest: str | None = None
    version: int | None = None
    confidence: float = 0.0
    exact: bool = False
    validated: bool = False
    context: tuple = ()

    def usable(self, now, max_age, context):
        return (type(self.value) is int and self.value > 0 and self.exact and self.validated
                and self.source != PowerSource.UNKNOWN and self.confidence == 1.0
                and 0 <= now-self.observed_at <= max_age and self.context == context
                and bool(context)
                and (self.source != PowerSource.STRUCTURED_LAST_META_BATTLE_SETUP
                     or (bool(self.digest) and self.version is not None)))


@dataclass(frozen=True, slots=True)
class RankingPolicy:
    version: str = "arena-ranking-v1"
    max_power_ratio: float = 1.0
    prefer_lower_power: bool = True
    points_preference: str = "higher"
    points_bound: int = 10000
    minimum_candidates: int = 1
    power_max_age: float = 15.0

    def __post_init__(self):
        if not self.version or not isfinite(self.max_power_ratio) or self.max_power_ratio <= 0:
            raise ValueError("invalid ranking policy")
        if type(self.prefer_lower_power) is not bool or self.points_preference not in ("higher","lower","none"):
            raise ValueError("invalid ranking preferences")
        if type(self.points_bound) is not int or self.points_bound <= 0 or type(self.minimum_candidates) is not int or self.minimum_candidates <= 0:
            raise ValueError("invalid ranking bounds")
        if not isfinite(self.power_max_age) or self.power_max_age <= 0:
            raise ValueError("invalid power freshness")


@dataclass(frozen=True, slots=True)
class Candidate:
    player_id: str
    name: str
    level: int
    arena_points: int
    combat_power: int
    own_power: int
    power_ratio: Fraction
    points_component: Fraction
    arena_digest: str
    arena_version: int
    fingerprint: str
    policy: RankingPolicy
    power: OwnPower


@dataclass(frozen=True, slots=True)
class Ranking:
    candidates: tuple[Candidate, ...]
    selected: Candidate | None
    reason: str
    # This package deliberately cannot authorize a fight.
    fight_authorized: bool = False


def team_context(account):
    """Conservative dependency key, not a calculated team power."""
    if account is None:
        return ()
    items=[]
    for name in ("arena","heroes","relics"):
        item=account.sources.get(name)
        if not item or not item.fresh(2) or not item.digest:
            return ()
        items.append((name,item.digest,item.model.version))
    return tuple(items)


def rank(account, power, policy=RankingPolicy(), *, now=None, context=None):
    now=time.monotonic() if now is None else now
    context=team_context(account) if context is None else context
    item=account.sources.get("arena") if account else None
    if not item or not item.fresh(2,now) or not item.digest:
        return Ranking((),None,"ARENA_STALE")
    if power is None or not power.usable(now,policy.power_max_age,context):
        return Ranking((),None,"OWN_POWER_UNAVAILABLE")
    model=item.model
    rows=[]
    for o in model.current_opponents:
        ratio=Fraction(o.combat_power,power.value)
        if ratio>Fraction(str(policy.max_power_ratio)):
            continue
        points=Fraction(max(0,min(policy.points_bound,o.arena_points)),policy.points_bound)
        if policy.points_preference=="lower":
            points=1-points
        elif policy.points_preference=="none":
            points=Fraction(0)
        rows.append(Candidate(o.identity,o.name,o.level,o.arena_points,o.combat_power,power.value,
            ratio,points,item.digest,model.version,model.opponent_set_fingerprint,policy,power))
    rows.sort(key=lambda c:(c.power_ratio if policy.prefer_lower_power else -c.power_ratio,
                            -c.points_component,c.player_id))
    candidates=tuple(rows)
    return Ranking(candidates,candidates[0] if len(candidates)>=policy.minimum_candidates else None,
                   "DIAGNOSTIC_ONLY" if len(candidates)>=policy.minimum_candidates else "INSUFFICIENT_CANDIDATES")


def update_ranking(facts,account,raw):
    try:
        policy=RankingPolicy(**raw.get("planner",{}).get("arena_ranking",{}))
    except (TypeError,ValueError):
        facts.pop("arena_ranking",None)
        facts.pop("arena_selected_target",None)
        return
    result=rank(account,facts.get("arena_own_power"),policy)
    previous=facts.get("arena_ranking")
    if previous!=result:
        facts.pop("arena_selected_target",None)
    facts["arena_ranking"]=result
    if result.selected is not None:
        facts["arena_selected_target"]=result.selected
    else:
        facts.pop("arena_selected_target",None)
