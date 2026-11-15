"""Single-use, input-free shadow coordinator. All clocks supplied by caller."""
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from math import isfinite
from .arena_authorization import ArenaTokenPolicy, authorize, still_valid
from .arena_ranking import RankingPolicy, rank
from .arena_attempt import AttemptReconciliation, AttemptObservation, TerminalRecord
from .arena_outcome import Outcome, capture, exact_spend


class Phase(str,Enum):
    IDLE="IDLE"
    NEED_ARENA_STATE="NEED_ARENA_STATE"
    NEED_TRAVERSAL="NEED_TRAVERSAL"
    NEED_OWN_POWER="NEED_OWN_POWER"
    NEED_RANKING="NEED_RANKING"
    NEED_AUTHORIZATION="NEED_AUTHORIZATION"
    PREPARED="PREPARED"
    START_OBSERVED="START_OBSERVED"
    START_UNRESOLVED="START_UNRESOLVED"
    BATTLE_RUNNING="BATTLE_RUNNING"
    RESULT_PENDING="RESULT_PENDING"
    TERMINAL="TERMINAL"
    BLOCKED="BLOCKED"
    CANCELLED="CANCELLED"


STOP={Phase.TERMINAL,Phase.BLOCKED,Phase.CANCELLED}


@dataclass(frozen=True,slots=True)
class StartIntent:
    attempt_id: str
    opponent_id: str
    expected_token_cost: int
    expected_visual: str
    resource_id: int
    resource_delta: int
    authorization_digest: str
    created_at: float
    deadline: float
    retry_allowed: bool=False


@dataclass(frozen=True,slots=True)
class Transition:
    phase: Phase
    reason: str
    at: float


class ArenaRunCoordinator:
    """One attempt per instance. Explicit fresh planning required for another.

    begin_observation_window is a synthetic/external boundary, NOT a start
    command. It freezes the baseline before any spend or visual evidence.
    """
    def __init__(self,*,start_timeout=5.,result_timeout=60.):
        if any(not isfinite(v) or not 0<v<=120 for v in (start_timeout,result_timeout)):
            raise ValueError("invalid deadlines")
        self.start_timeout=start_timeout
        self.result_timeout=result_timeout
        self.phase=Phase.IDLE
        self.reason="IDLE"
        self.trace=[]
        self.auth=None
        self.intent=None
        self.reconciliation=None
        self.record=None
        self.last_time=float("-inf")
        self.visual_battle=False
        self.started_at=None
        self.retry_allowed=False
        self.spend_confirmed=False
        self.last_spend=None
        self.last_status=None

    def _clock(self,now):
        if not isfinite(now) or now<self.last_time:
            raise ValueError("nonmonotonic observation")
        self.last_time=now

    def _set(self,phase,reason,now):
        self.phase,self.reason=phase,reason
        if not self.trace or (self.trace[-1].phase,self.trace[-1].reason)!=(phase,reason):
            self.trace.append(Transition(phase,reason,now))
            if len(self.trace)>64:
                self.trace.pop(0)
        return phase

    def cancel(self,*,now):
        self._clock(now)
        if self.phase not in STOP:
            if self.intent is not None:
                self.record=self.reconciliation.close(Outcome.INCONCLUSIVE,"CANCELLED_NO_RETRY",now=now)
            self._set(Phase.CANCELLED,"CANCELLED_NO_RETRY",now)
        return self.phase

    def prepare(self,account,inventory,power,policy=ArenaTokenPolicy(),ranking_policy=RankingPolicy(),*,now):
        self._clock(now)
        if self.phase in STOP or self.auth is not None:
            raise ValueError("coordinator already owns or closed an attempt")
        a=account.sources.get("arena") if account else None
        self._set(Phase.NEED_ARENA_STATE,"CHECK_ARENA",now)
        if not a or not a.digest or not a.fresh(2,now):
            return self._set(Phase.BLOCKED,"BLOCK_ARENA_STALE",now)
        self._set(Phase.NEED_TRAVERSAL,"CHECK_TRAVERSAL",now)
        for failed,reason in (
            (inventory is None,"TRAVERSAL_MISSING"),
            (inventory is not None and inventory.digest!=a.digest,"TRAVERSAL_DIGEST_MISMATCH"),
            (inventory is not None and inventory.version!=a.model.version,"TRAVERSAL_VERSION_MISMATCH"),
            (inventory is not None and inventory.reason not in ("END_UNCHANGED","NO_NEW_ROWS","COUNT_REACHED"),"TRAVERSAL_INCOMPLETE"),
            (inventory is not None and (inventory.unique_count!=a.model.opponents.count or inventory.structured_count!=a.model.opponents.count),"TRAVERSAL_COUNT_MISMATCH")):
            if failed:
                return self._set(Phase.NEED_TRAVERSAL,reason,now)
        self._set(Phase.NEED_OWN_POWER,"CHECK_POWER",now)
        context=[]
        for name in ("arena","heroes","relics"):
            item=account.sources.get(name)
            if not item or not item.digest or not item.fresh(2,now):
                return self._set(Phase.NEED_OWN_POWER,"OWN_POWER_CONTEXT_STALE",now)
            context.append((name,item.digest,item.model.version))
        if power is None or not power.exact or not power.validated or power.value is None:
            return self._set(Phase.NEED_OWN_POWER,"OWN_POWER_UNAVAILABLE",now)
        if not power.usable(now,ranking_policy.power_max_age,tuple(context)):
            return self._set(Phase.NEED_OWN_POWER,"OWN_POWER_STALE_OR_CONTEXT_MISMATCH",now)
        self._set(Phase.NEED_RANKING,"RANK",now)
        ranking=rank(account,power,ranking_policy,now=now,context=tuple(context))
        self._set(Phase.NEED_AUTHORIZATION,"AUTHORIZE",now)
        auth=authorize(account,ranking.selected,power,policy,ranking_policy,now=now)
        if not auth.allowed:
            return self._set(Phase.BLOCKED,auth.reason,now)
        self.auth=auth
        return self._set(Phase.PREPARED,"AUTHORIZED_SHADOW_ONLY",now)

    def begin_observation_window(self,account,candidate,power,policy,ranking_policy,*,now):
        self._clock(now)
        if self.phase!=Phase.PREPARED or self.intent is not None:
            raise ValueError("no unused prepared attempt")
        auth=self.auth
        if not still_valid(auth,account,candidate,power,policy,ranking_policy,now=now):
            self._set(Phase.BLOCKED,"PRESTART_INVALIDATED",now)
            return None
        # Existing reconciliation requires the unchanged PRE snapshot here.
        self.reconciliation=AttemptReconciliation(auth.attempt,timeout=self.result_timeout)
        self.reconciliation.mark_started(account,now=now)
        self.started_at=now
        self.result_deadline=now+self.start_timeout+self.result_timeout
        self.reconciliation.core.deadline=self.result_deadline
        key=(auth.attempt_id,auth.player_digest,auth.player_version,
             candidate.arena_digest,candidate.arena_version,candidate.fingerprint,
             repr(power),repr(policy),repr(ranking_policy))
        self.intent=StartIntent(auth.attempt_id,auth.selected_opponent_id,auth.expected_cost,
            "battle",21,-auth.expected_cost,sha256(repr(key).encode()).hexdigest(),
            now,now+self.start_timeout)
        # Start window is distinct from verified battle start. Never emit twice.
        self._set(Phase.START_OBSERVED,"AWAITING_START_EVIDENCE",now)
        return self.intent

    def _runtime_sample(self,attempt_id,now):
        # All supplied timestamps must share the caller's monotonic epoch.
        if self.auth is None or attempt_id!=self.auth.attempt_id:
            self.last_status="WRONG_ATTEMPT"
            return False
        if not isfinite(now) or now<self.last_time or (self.intent and now<self.intent.created_at):
            self.last_status="IGNORED_STALE"
            return False
        self._clock(now)
        return True

    def _close(self,outcome,reason,now,sample=None):
        self.record=self.reconciliation.close(outcome,reason,now=now,sample=sample)
        self._set(Phase.TERMINAL,reason,now)
        self.last_status=outcome.value
        return self.record

    def _spend(self,sample):
        self.last_spend=exact_spend(self.auth.attempt.baseline,sample,self.auth.expected_cost)
        self.spend_confirmed=self.last_spend.status=="CONFIRMED"
        return self.last_spend.status

    def observe_start(self,attempt_id,account,*,visual_battle=False,now):
        if not self._runtime_sample(attempt_id,now):
            return self.last_status
        if self.phase in STOP:
            return self.phase
        if self.phase not in (Phase.START_OBSERVED,Phase.START_UNRESOLVED,Phase.BATTLE_RUNNING,Phase.RESULT_PENDING):
            self.last_status="PENDING"
            return self.phase
        sample=capture(account,now=now)
        if now>=self.result_deadline:
            self._close(Outcome.INCONCLUSIVE,"RESULT_INCONCLUSIVE_TIMEOUT",now,sample)
            return self.phase
        if self._spend(sample)=="CONFLICTED":
            self._close(Outcome.CONFLICTED,"START_SPEND_CONFLICT",now,sample)
            return self.phase
        self.visual_battle=self.visual_battle or visual_battle is True
        self.last_status="CONFIRMED" if self.spend_confirmed else "PENDING"
        if self.phase==Phase.RESULT_PENDING:
            return self.phase
        if self.visual_battle:
            return self._set(Phase.BATTLE_RUNNING,"START_CONFIRMED" if self.spend_confirmed else "BATTLE_VISUAL_SPEND_PENDING",now)
        if now>=self.intent.deadline:
            return self._set(Phase.START_UNRESOLVED,"START_EVIDENCE_INCONCLUSIVE_OWNED",now)
        return self._set(Phase.START_OBSERVED,"START_PENDING",now)

    def observe_result(self,observation):
        if self.auth is None or observation.attempt_id!=self.auth.attempt_id:
            self.last_status="WRONG_ATTEMPT"
            return self.last_status
        if self.record is not None:
            return self.record
        if not self._runtime_sample(observation.attempt_id,observation.sample.observed_at):
            return self.last_status
        if self.phase in STOP or self.intent is None:
            self.last_status="PENDING"
            return None
        sample=observation.sample
        now=sample.observed_at
        if now>=self.result_deadline:
            return self._close(Outcome.INCONCLUSIVE,"RESULT_INCONCLUSIVE_TIMEOUT",now,sample)
        if self._spend(sample)=="CONFLICTED":
            return self._close(Outcome.CONFLICTED,"RESULT_SPEND_CONFLICT",now,sample)
        # An attempt-bound result can arrive even if battle visuals were missed.
        result=self.reconciliation.observe(observation)
        if isinstance(result,TerminalRecord):
            self.record=result
            self._set(Phase.TERMINAL,result.outcome.value,now)
            self.last_status=result.outcome.value
        elif result is not None:
            self.last_status="PENDING"
            if observation.visual in ("victory","defeat","completed") or result.outcome==Outcome.BATTLE_COMPLETED_RESULT_UNKNOWN or self.phase==Phase.RESULT_PENDING:
                self._set(Phase.RESULT_PENDING,result.reason,now)
            elif observation.visual=="battle":
                self.visual_battle=True
                self._set(Phase.BATTLE_RUNNING,"BATTLE_VISUAL_SPEND_PENDING",now)
        return result

    def tick(self,*,now):
        if not isfinite(now) or now<self.last_time:
            self.last_status="IGNORED_STALE"
            return self.last_status
        self._clock(now)
        if self.phase in STOP:
            return self.phase
        if self.phase==Phase.PREPARED and now-self.auth.observed_at>2:
            self._set(Phase.BLOCKED,"AUTHORIZATION_EXPIRED",now)
        elif self.intent is not None:
            if now>=self.result_deadline:
                self._close(Outcome.INCONCLUSIVE,"RESULT_INCONCLUSIVE_TIMEOUT",now)
            elif self.phase==Phase.START_OBSERVED and now>=self.intent.deadline:
                self._set(Phase.START_UNRESOLVED,"START_EVIDENCE_INCONCLUSIVE_OWNED",now)
        return self.phase
