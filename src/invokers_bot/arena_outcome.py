"""Read-only evidence and bounded reconciliation. No actor or replay path."""
from dataclasses import dataclass
from enum import Enum
from collections import Counter
from math import isfinite
import time
from .arena_stats import ArenaBattleStats
from .arena_opponent import parse_opponent
from .arena_finished import parse_finished_opponent
from .snapshot_envelope import SnapshotFormatError
from .resource_types import ResourceTypeId


class Outcome(str,Enum):
    WIN_CONFIRMED="WIN_CONFIRMED"
    LOSS_CONFIRMED="LOSS_CONFIRMED"
    BATTLE_COMPLETED_RESULT_UNKNOWN="BATTLE_COMPLETED_RESULT_UNKNOWN"
    BATTLE_START_ONLY="BATTLE_START_ONLY"
    INCONCLUSIVE="INCONCLUSIVE"
    CONFLICTED="CONFLICTED"


@dataclass(frozen=True,slots=True)
class Sample:
    observed_at: float
    arena_digest: str | None = None
    arena_version: int | None = None
    player_digest: str | None = None
    player_version: int | None = None
    stats: ArenaBattleStats | None = None
    week_ticks: int | None = None
    points: int | None = None
    tokens: int | None = None
    coins: int | None = None
    finished_ids: tuple[str,...] | None = None
    current_id: str | None = None
    tokens_spent: int | None = None


def _identity(raw):
    return parse_opponent(raw).identity


def capture(account, *, now=None):
    now=time.monotonic() if now is None else now
    a=account.sources.get("arena") if account else None
    p=account.sources.get("player") if account else None
    def usable(item):
        return item and item.digest and item.fresh(2,now)
    values={}
    if usable(a):
        m=a.model
        values.update(arena_digest=a.digest,arena_version=m.version,stats=m.stats,
                      week_ticks=m.last_week_process_ticks,points=m.points)
        try:
            values["finished_ids"]=tuple(parse_finished_opponent(x).identity for x in m.finished_opponents.entries)
        except SnapshotFormatError:
            pass
        if m.current_battle_opponent_raw is not None:
            try:
                values["current_id"]=_identity(m.current_battle_opponent_raw)
            except SnapshotFormatError:
                pass
    if usable(p):
        m=p.model
        values.update(player_digest=p.digest,player_version=m.version,
                      tokens=m.resources.get(ResourceTypeId.Arena_Token),
                      coins=m.resources.get(ResourceTypeId.Arena_Coin),
                      tokens_spent=getattr(m,'resources_spent',{}).get(ResourceTypeId.Arena_Token))
    return Sample(now,**values)


def delta(a,b):
    return b-a if type(a) is int and type(b) is int else None


@dataclass(frozen=True,slots=True)
class ExactSpend:
    status: str
    balance_delta: int | None
    spent_delta: int | None
    source: str | None = None


def exact_spend(before,after,cost):
    """Counter preferred; wallet-only fallback when the counter is unavailable.

    Known unchanged counter with decreased wallet is unresolved, not proof.
    A counter-confirmed spend can coexist with regeneration/rewards.
    """
    wallet=delta(before.tokens,after.tokens)
    spent=delta(before.tokens_spent,after.tokens_spent)
    if type(cost) is not int or cost<=0:
        return ExactSpend("PENDING",wallet,spent)
    if not before.player_digest or not after.player_digest or before.player_version is None or after.player_version is None:
        return ExactSpend("PENDING",wallet,spent)
    if after.player_version<before.player_version or (
        before.player_digest==after.player_digest and (wallet not in (None,0) or spent not in (None,0))):
        return ExactSpend("CONFLICTED",wallet,spent)
    if spent is not None and spent not in (0,cost):
        return ExactSpend("CONFLICTED",wallet,spent)
    if wallet is not None and wallet < -cost:
        return ExactSpend("CONFLICTED",wallet,spent)
    if spent==cost:
        return ExactSpend("CONFIRMED",wallet,spent,"RESOURCES_SPENT")
    if spent is None and wallet==-cost:
        return ExactSpend("CONFIRMED",wallet,spent,"BALANCE")
    return ExactSpend("PENDING",wallet,spent)


def arena_token_spent_exactly(before,after,cost):
    return exact_spend(before,after,cost).status=="CONFIRMED"


def finished_opponent_added(before,after,identity):
    if not identity or before.finished_ids is None or after.finished_ids is None:
        return False
    return Counter(after.finished_ids)[identity]==1 and Counter(before.finished_ids)[identity]==0


@dataclass(frozen=True,slots=True)
class ArenaBattleOutcomeEvidence:
    offense_battles_delta: int | None
    offense_wins_delta: int | None
    defense_battles_delta: int | None
    points_delta: int | None
    token_delta: int | None
    coin_delta: int | None
    exact_token_spend: bool
    finished_added: bool
    current_opponent_matched: bool
    visual_result: str | None
    reset_or_rollback: bool
    source_conflict: bool
    tokens_spent_delta: int | None = None
    spend_source: str | None = None
    spend_conflict: bool = False

    @property
    def arena_offense_battles_increased(self):
        return self.offense_battles_delta is not None and self.offense_battles_delta>0

    @property
    def arena_offense_wins_increased(self):
        return self.offense_wins_delta is not None and self.offense_wins_delta>0

    @property
    def arena_points_changed(self):
        return self.points_delta is not None and self.points_delta!=0

    @property
    def arena_coin_increased(self):
        return self.coin_delta is not None and self.coin_delta>0


def evidence(before,after,*,cost=None,identity=None,visual=None):
    a,b=before.stats,after.stats
    stats_ok=bool(a and b and before.arena_digest and after.arena_digest)
    player_ok=bool(before.player_digest and after.player_digest)
    def sd(name):
        return delta(getattr(a,name),getattr(b,name)) if stats_ok else None
    ob,ow,db=map(sd,("total_offense_battles","total_offense_wins","total_defense_battles"))
    reset=False
    if stats_ok:
        # Archived timestamp-label conflict: never rely on it alone; reject
        # week rollover-like counters or timestamp change conservatively.
        reset=(before.week_ticks!=after.week_ticks or
               any(sd(n)<0 for n in ("total_offense_battles","total_offense_wins",
                  "total_defense_battles","total_defense_wins","attack_battles_this_week",
                  "attack_wins_this_week","defense_battles_this_week","defense_wins_this_week")) or
               any(sd(n)!=0 for n in ("attack_battles_last_week","attack_wins_last_week",
                  "defense_battles_last_week","defense_wins_last_week")))
    conflict=(after.observed_at<before.observed_at or
              (stats_ok and before.arena_version>after.arena_version) or
              (player_ok and before.player_version>after.player_version) or
              (stats_ok and before.arena_digest==after.arena_digest and a!=b) or
              (player_ok and before.player_digest==after.player_digest and
               (before.tokens,before.coins)!=(after.tokens,after.coins)) or
              (stats_ok and identity is not None and after.current_id is not None and after.current_id!=identity))
    spend=exact_spend(before,after,cost)
    return ArenaBattleOutcomeEvidence(ob,ow,db,
        delta(before.points,after.points) if stats_ok else None,
        delta(before.tokens,after.tokens) if player_ok else None,
        delta(before.coins,after.coins) if player_ok else None,
        player_ok and spend.status=="CONFIRMED",
        stats_ok and finished_opponent_added(before,after,identity),
        stats_ok and identity is not None and after.current_id==identity,
        visual,reset,bool(conflict),spend.spent_delta,spend.source,spend.status=="CONFLICTED")


@dataclass(frozen=True,slots=True)
class Result:
    outcome: Outcome
    evidence: ArenaBattleOutcomeEvidence
    pending: bool
    reason: str
    replay_allowed: bool = False


class Reconciliation:
    """One explicit attempt baseline; caller may poll observations only.

    visual must be tied to this attempt by the future live caller. No input
    capability here. Terminal results latch, timeout never retries combat.
    """
    def __init__(self,baseline,*,identity=None,cost=None,timeout=15):
        if not isfinite(timeout) or not 0<timeout<=120:
            raise ValueError("invalid reconciliation timeout")
        self.baseline=baseline
        self.identity=identity
        self.cost=cost
        self.deadline=baseline.observed_at+timeout
        self.latest_at=baseline.observed_at
        self.visual=None
        self.terminal=None

    def observe(self,after,*,visual=None):
        if self.terminal is not None:
            return self.terminal
        if visual not in (None,"victory","defeat","completed","battle"):
            raise ValueError("invalid visual evidence")
        visual_conflict=(self.visual in ("victory","defeat") and
                         visual in ("victory","defeat") and visual!=self.visual)
        if visual in ("victory","defeat") or self.visual is None or (
                visual=="completed" and self.visual=="battle"):
            self.visual=visual
        e=evidence(self.baseline,after,cost=self.cost,identity=self.identity,visual=self.visual)
        expired=after.observed_at>=self.deadline
        ob,ow=e.offense_battles_delta,e.offense_wins_delta
        if visual_conflict or e.source_conflict or after.observed_at<self.latest_at:
            result=Result(Outcome.CONFLICTED,e,False,"CONTRADICTORY_PROVENANCE_OR_VISUAL")
        elif expired:
            result=Result(Outcome.INCONCLUSIVE,e,False,"OBSERVATION_TIMEOUT")
        elif e.spend_conflict:
            result=Result(Outcome.CONFLICTED,e,False,"TOKEN_SPEND_CONFLICT")
        elif e.reset_or_rollback:
            result=Result(Outcome.CONFLICTED,e,False,"RESET_OR_COUNTER_ROLLBACK")
        elif ob is not None and (ob>1 or ow>ob):
            result=Result(Outcome.CONFLICTED,e,False,"AMBIGUOUS_OFFENSE_COUNTERS")
        elif ob==1 and ow in (0,1):
            expected="victory" if ow==1 else "defeat"
            if self.visual in ("victory","defeat") and self.visual!=expected:
                result=Result(Outcome.CONFLICTED,e,False,"VISUAL_COUNTER_CONFLICT")
            elif e.exact_token_spend and (self.visual==expected or e.finished_added):
                result=Result(Outcome.WIN_CONFIRMED if ow else Outcome.LOSS_CONFIRMED,e,False,"OFFENSE_AND_SUPPORT")
            else:
                result=Result(Outcome.BATTLE_COMPLETED_RESULT_UNKNOWN,e,True,"AWAITING_CORROBORATION")
        elif e.finished_added and self.visual in ("victory","defeat","completed"):
            result=Result(Outcome.BATTLE_COMPLETED_RESULT_UNKNOWN,e,True,"AWAITING_OFFENSE_COUNTERS")
        elif e.exact_token_spend or self.visual=="battle":
            result=Result(Outcome.BATTLE_START_ONLY,e,True,"AWAITING_RESULT")
        else:
            result=Result(Outcome.INCONCLUSIVE,e,True,"AWAITING_PERSISTENCE")
        self.latest_at=max(self.latest_at,after.observed_at)
        if not result.pending:
            self.terminal=result
        return result
