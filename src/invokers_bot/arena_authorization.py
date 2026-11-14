"""Pure pre-start policy. ALLOW is a planning record, never input permission."""
from dataclasses import dataclass
from enum import Enum
from math import isfinite
import time
from .arena_ranking import RankingPolicy, PowerSource, rank
from .arena_attempt import create_attempt, ArenaBattleAttemptContext
from .resource_types import ResourceTypeId


class TokenPressure(str, Enum):
    UNKNOWN="UNKNOWN"
    NORMAL="NORMAL"
    HIGH="HIGH"
    AT_CAP="AT_CAP"


@dataclass(frozen=True, slots=True)
class ArenaTokenPolicy:
    token_cap: int = 10
    regeneration_seconds: int = 3600
    pressure_start: int = 8
    reserve: int = 0
    expected_battle_cost: int | None = 1
    max_balance_age: float = 2.0
    policy_version: str = "arena-token-v2"

    def __post_init__(self):
        if (any(type(x) is not int for x in (self.token_cap,self.regeneration_seconds,self.pressure_start,self.reserve))
                or self.token_cap<=0 or self.regeneration_seconds<=0
                or not 0<=self.pressure_start<=self.token_cap or self.reserve<0
                or (self.expected_battle_cost is not None and
                    (type(self.expected_battle_cost) is not int or self.expected_battle_cost<=0))
                or not 0<self.max_balance_age<=2 or not isfinite(self.max_balance_age)
                or not isinstance(self.policy_version,str) or not self.policy_version.strip()):
            raise ValueError("invalid arena token policy")


def balance(account,policy,now):
    item=account.sources.get("player") if account else None
    if not item or not item.digest or not item.fresh(policy.max_balance_age,now):
        return None
    value=item.model.resources.get(ResourceTypeId.Arena_Token)
    return value if type(value) is int and value>=0 else None


def pressure(value,policy=ArenaTokenPolicy()):
    if type(value) is not int or value<0:
        return TokenPressure.UNKNOWN
    if value>=policy.token_cap:
        return TokenPressure.AT_CAP
    return TokenPressure.HIGH if value>=policy.pressure_start else TokenPressure.NORMAL


@dataclass(frozen=True, slots=True)
class PreStartAuthorization:
    allowed: bool
    reason: str
    selected_opponent_id: str | None
    candidate_fingerprint: str | None
    candidate_version: int | None
    own_power_provenance: PowerSource | None
    own_power_version: int | None
    token_balance: int | None
    expected_cost: int | None
    reserve: int
    resulting_balance: int | None
    pressure: TokenPressure
    policy: ArenaTokenPolicy
    ranking_policy: RankingPolicy
    observed_at: float
    candidate: object
    power: object
    player_digest: str | None
    player_version: int | None
    attempt: ArenaBattleAttemptContext | None = None

    @property
    def attempt_id(self):
        return self.attempt.attempt_id if self.attempt else None

    @property
    def policy_version(self):
        return self.policy.policy_version

    @property
    def fight_authorized(self):
        return False


def _check(account,candidate,power,policy,ranking_policy,now):
    a=account.sources.get("arena") if account else None
    if not a or not a.digest or not a.fresh(2,now):
        return "BLOCK_ARENA_STALE"
    if power is None or power.source==PowerSource.UNKNOWN or not power.exact or not power.validated or type(power.value) is not int or power.value<=0 or power.confidence!=1:
        return "BLOCK_OWN_POWER_UNKNOWN"
    context=[]
    for name in ("arena","heroes","relics"):
        item=account.sources.get(name)
        if not item or not item.fresh(2,now) or not item.digest:
            return "BLOCK_OWN_POWER_STALE"
        context.append((name,item.digest,item.model.version))
    if not power.usable(now,ranking_policy.power_max_age,tuple(context)):
        return "BLOCK_OWN_POWER_STALE"
    if candidate is None:
        return "BLOCK_TARGET_MISSING"
    current=rank(account,power,ranking_policy,now=now,context=tuple(context))
    if current.selected!=candidate:
        return "BLOCK_TARGET_STALE"
    value=balance(account,policy,now)
    if value is None:
        return "BLOCK_TOKEN_BALANCE_STALE"
    cost=policy.expected_battle_cost
    if cost is None:
        return "BLOCK_TOKEN_COST_UNKNOWN"
    if value<cost:
        return "BLOCK_INSUFFICIENT_TOKENS"
    if value-cost<policy.reserve:
        return "BLOCK_RESERVE"
    return "ALLOW"


def authorize(account,candidate,power,policy=ArenaTokenPolicy(),ranking_policy=RankingPolicy(),*,now=None):
    now=time.monotonic() if now is None else now
    reason=_check(account,candidate,power,policy,ranking_policy,now)
    value=balance(account,policy,now)
    cost=policy.expected_battle_cost
    item=account.sources.get("player") if account else None
    attempt=None
    if reason=="ALLOW":
        try:
            attempt=create_attempt(account,candidate.player_id,expected_token_cost=cost,now=now)
        except ValueError:
            reason="BLOCK_ATTEMPT_BASELINE"
    return PreStartAuthorization(reason=="ALLOW",reason,getattr(candidate,"player_id",None),
        getattr(candidate,"fingerprint",None),getattr(candidate,"arena_version",None),
        getattr(power,"source",None),getattr(power,"version",None),value,cost,policy.reserve,
        value-cost if value is not None and cost is not None else None,pressure(value,policy),
        policy,ranking_policy,now,candidate,power,getattr(item,"digest",None),
        getattr(getattr(item,"model",None),"version",None),attempt)


def from_config(raw):
    """Invalid configuration is a blocked policy, not a default substitution."""
    try:
        return ArenaTokenPolicy(**raw["planner"]["arena_token"]),None
    except (KeyError,TypeError,ValueError):
        return None,"BLOCK_POLICY"


def still_valid(auth,account,candidate,power,policy,ranking_policy,*,now=None):
    now=time.monotonic() if now is None else now
    if not auth.allowed or not auth.attempt or not 0<=now-auth.observed_at<=2:
        return False
    if (auth.policy,auth.ranking_policy,auth.candidate,auth.power)!=(policy,ranking_policy,candidate,power):
        return False
    if _check(account,candidate,power,policy,ranking_policy,now)!="ALLOW":
        return False
    item=account.sources["player"]
    return (item.digest,item.model.version,balance(account,policy,now))==(auth.player_digest,auth.player_version,auth.token_balance)


def spend_expectation(auth):
    if not auth.allowed or auth.attempt is None:
        raise ValueError("blocked authorization")
    return {"invalidates_sources":["player"],"expects_source_change":["player"],
            "expect":["battle"],"expects_visual_transition":True,
            "success_mode":"VISUAL_AND_STRUCTURED","semantic_predicates":[
                {"kind":"resource_delta","source":"player","resource_id":21,"delta":-auth.expected_cost}]}


@dataclass(frozen=True,slots=True)
class SpendObservation:
    status: str
    retry_allowed: bool = False


def verify_spend(auth,account,*,visual_battle=False,now=None,timeout=5):
    now=time.monotonic() if now is None else now
    if not auth.allowed or auth.attempt is None:
        return SpendObservation("BLOCKED")
    if not isfinite(timeout) or not 0<timeout<=120:
        raise ValueError("invalid spend window")
    if now<auth.observed_at or now-auth.observed_at>=timeout:
        return SpendObservation("INCONCLUSIVE")
    value=balance(account,auth.policy,now)
    item=account.sources.get("player") if account else None
    if value is None or item.digest==auth.player_digest:
        return SpendObservation("PENDING")
    if item.model.version<auth.player_version:
        return SpendObservation("CONFLICTED")
    delta=value-auth.token_balance
    if delta==-auth.expected_cost and visual_battle:
        return SpendObservation("CONFIRMED")
    if delta not in (0,-auth.expected_cost):
        return SpendObservation("CONFLICTED")
    return SpendObservation("PENDING")
