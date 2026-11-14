"""Small AccountState-driven eligibility slice; no UI input or file parsing."""
from dataclasses import dataclass, asdict
from math import isfinite
import time

from .goals import Goal
from .resource_types import ResourceTypeId
from .scheduler import TaskScheduler

ARENA = "G-RES-001"
REFRESH = "G-MAINT-001"


@dataclass(frozen=True, slots=True)
class GoalEvaluation:
    candidate_id: str
    eligible: bool
    blocked_reasons: tuple[str, ...]
    source_age: float | None
    source_fresh: bool
    source_version: int | None
    source_digest: str | None
    token_balance: int | None
    threshold: int | None
    reserve: int | None
    cap: int | None
    cost: int | None


@dataclass(frozen=True, slots=True)
class DecisionTrace:
    timestamp: float
    selected: str | None
    evaluations: tuple[GoalEvaluation, ...]

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ArenaPolicy:
    threshold: int
    reserve: int
    cap: int | None
    cost: int | None
    max_age: float

    @classmethod
    def from_config(cls, raw):
        threshold, reserve = raw["threshold"], raw["reserve"]
        cap, cost = raw.get("cap"), raw.get("cost")
        values = (threshold, reserve, cap, cost)
        if type(threshold) is not int or type(reserve) is not int or any(
            v is not None and type(v) is not int for v in (cap, cost)
        ):
            raise ValueError("arena policy values must be integers or optional null")
        age = float(raw.get("max_age", 2.0))
        if not (reserve >= 0 and threshold > 0 and (cap is None or cap >= max(threshold, reserve + 1))
                and (cost is None or (cost > 0 and (cap is None or reserve + cost <= cap)))
                and isfinite(age) and age > 0):
            raise ValueError("invalid arena resource policy")
        return cls(*values, age)


def decide(account, raw, *, observer_available, now=None, timestamp=None):
    now = time.monotonic() if now is None else now
    timestamp = time.time() if timestamp is None else timestamp
    item = account.sources.get("player") if account else None
    age = max(0.0, now - item.checked_at) if item else None
    reasons = []
    policy = None
    try:
        policy = ArenaPolicy.from_config(raw.get("planner", {}).get("arena", {}))
    except (KeyError, ValueError, TypeError):
        reasons.append("POLICY_MISSING_OR_INVALID")
    fresh = bool(item and item.fresh(policy.max_age if policy else 2.0, now))
    if item is None or item.model is None:
        reasons.append("PLAYER_MISSING")
    elif not fresh:
        reasons.append("PLAYER_STALE_OR_INVALID")
    balance = None
    if fresh:
        value = getattr(item.model, "resources", {}).get(int(ResourceTypeId.Arena_Token))
        if type(value) is int and value >= 0:
            balance = value
        else:
            reasons.append("ARENA_TOKEN_MISSING_OR_INVALID")
    # Require the configured navigation path, not a speculative opponent capability.
    flows = raw.get("flows", {})
    states = raw.get("states", {})
    required = ("main", "arena_list", "formation")
    if not all(flows.get(s, {}).get("actions") and states.get(s, {}).get("template")
               and states[s].get("enabled", True) for s in (*required,)) or not states.get("battle", {}).get("template"):
        reasons.append("ARENA_NAVIGATION_UNAVAILABLE")
    if not observer_available:
        reasons.append("SNAPSHOT_SOURCE_UNCONFIGURED")
    if policy and balance is not None:
        if balance < policy.threshold:
            reasons.append("BELOW_THRESHOLD")
        if balance <= policy.reserve or (policy.cost is not None and balance - policy.cost < policy.reserve):
            reasons.append("RESOURCE_RESERVE")
    info = dict(source_age=age, source_fresh=fresh,
                source_version=getattr(item.model, "version", None) if item else None,
                source_digest=item.digest if item else None, token_balance=balance,
                threshold=policy.threshold if policy else None,
                reserve=policy.reserve if policy else None, cap=policy.cap if policy else None,
                cost=policy.cost if policy else None)
    arena = GoalEvaluation(ARENA, not reasons, tuple(reasons), **info)
    needs_refresh = not fresh or balance is None
    refresh_reasons = () if observer_available and needs_refresh else (
        "SNAPSHOT_SOURCE_UNCONFIGURED" if not observer_available else "REFRESH_NOT_NEEDED",)
    refresh = GoalEvaluation(REFRESH, not refresh_reasons, refresh_reasons, **info)
    evaluations = (refresh, arena)
    eligible = [Goal(e.candidate_id, 10 if e.candidate_id == REFRESH else 5)
                for e in evaluations if e.eligible]
    selected = TaskScheduler().choose_goal(eligible)
    return DecisionTrace(timestamp, selected.name if selected else None, evaluations)



def authorize_action(action, trace, raw):
    """Gate spending flows separately from ordinary opportunity/navigation."""
    required = action.get("required_goal")
    if trace.selected != required:
        return "GOAL_BLOCKED"
    if not action.get("requires_spend_authorization"):
        return None
    policy = raw.get("planner", {}).get("arena", {})
    if policy.get("allow_test_battle_start") is not True:
        return "GOAL_BLOCKED:TEST_FLOW_NOT_ENABLED"
    cost = policy.get("cost")
    if type(cost) is not int or cost <= 0:
        return "GOAL_BLOCKED:DENY_UNKNOWN_COST"
    # Any configured spending action must preserve the same budget as the goal.
    candidate = next(e for e in trace.evaluations if e.candidate_id == required)
    if candidate.token_balance is None or candidate.token_balance - cost < policy["reserve"]:
        return "GOAL_BLOCKED:RESOURCE_RESERVE"
    if action.get("spends_resource"):
        predicates = action.get("semantic_predicates", [])
        if not any(p.get("kind") == "resource_delta" and p.get("resource_id") == int(ResourceTypeId.Arena_Token)
                   and p.get("source", "player") == "player" and p.get("delta") == -cost
                   for p in predicates):
            return "GOAL_BLOCKED:COST_PREDICATE_MISMATCH"
    return None
