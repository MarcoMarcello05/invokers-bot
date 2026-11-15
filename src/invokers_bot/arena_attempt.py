"""Immutable attempt binding and metadata-only terminal history.

No input or permission to start combat. mark_started observes an externally
initiated transition; it never performs one.
"""
from dataclasses import dataclass, replace
from math import isfinite
from types import MappingProxyType
from uuid import uuid4
from .arena_outcome import Sample, Reconciliation, Outcome, Result, capture


@dataclass(frozen=True, slots=True)
class ArenaBattleAttemptContext:
    attempt_id: str
    opponent_id: str
    opponent_set_fingerprint: str
    created_at: float
    baseline: Sample
    expected_token_cost: int | None


def create_attempt(account, opponent_id, *, expected_token_cost=None, now=None):
    sample=capture(account,now=now)
    arena=account.sources["arena"].model if account and sample.arena_digest else None
    if (arena is None or not sample.player_digest or sample.stats is None
            or sample.tokens is None or sample.points is None
            or sample.finished_ids is None):
        raise ValueError("fresh complete attempt baseline required")
    if opponent_id not in {o.identity for o in arena.current_opponents}:
        raise ValueError("target absent")
    if expected_token_cost is not None and (type(expected_token_cost) is not int or expected_token_cost<=0):
        raise ValueError("invalid configured cost")
    # Retain numeric stats and immutable mappings only, never unknown raw slots.
    stats=replace(sample.stats, opaque_slots=MappingProxyType({}))
    sample=replace(sample,stats=stats)
    return ArenaBattleAttemptContext(uuid4().hex,opponent_id,arena.opponent_set_fingerprint,
                                     sample.observed_at,sample,expected_token_cost)


@dataclass(frozen=True,slots=True)
class AttemptObservation:
    attempt_id: str
    sample: Sample
    visual: str | None = None


@dataclass(frozen=True,slots=True)
class TerminalRecord:
    attempt_id: str
    opponent_id: str
    outcome: Outcome
    start_observed_at: float
    end_observed_at: float
    result: Result
    baseline_arena_digest: str
    baseline_player_digest: str
    final_arena_digest: str | None
    final_player_digest: str | None
    baseline_arena_version: int
    baseline_player_version: int
    final_arena_version: int | None
    final_player_version: int | None

    @property
    def recovery_required(self):
        return self.result.reason.startswith("RECOVERY_REQUIRED_")

    @property
    def retry_allowed(self):
        return False


class AttemptReconciliation:
    def __init__(self,context,*,timeout=15):
        if not isfinite(timeout) or not 0<timeout<=120:
            raise ValueError("invalid timeout")
        self.context=context
        self.timeout=timeout
        self.started_at=None
        self.record=None
        self.core=None

    def mark_started(self,account,*,now=None):
        """Bind an observed start to a still-valid pre-start account baseline."""
        if self.core is not None:
            raise ValueError("attempt already started")
        current=capture(account,now=now)
        b=self.context.baseline
        arena=account.sources["arena"].model if account and current.arena_digest else None
        if (arena is None or current.observed_at<b.observed_at
                or current.observed_at-b.observed_at>2
                or arena.opponent_set_fingerprint!=self.context.opponent_set_fingerprint
                or (current.arena_digest,current.arena_version,current.player_digest,current.player_version)
                !=(b.arena_digest,b.arena_version,b.player_digest,b.player_version)):
            raise ValueError("stale pre-start attempt")
        self.started_at=current.observed_at
        self.core=Reconciliation(b,identity=self.context.opponent_id,
                                 cost=self.context.expected_token_cost,timeout=self.timeout)
        self.core.deadline=self.started_at+self.timeout
        self.core.latest_at=self.started_at

    def close(self, outcome, reason, *, now, sample=None):
        """Explicit metadata-only closure, even without a fresh sample."""
        if self.record is not None:
            return self.record
        from .arena_outcome import evidence
        b=self.context.baseline
        sample=sample if sample is not None else Sample(now)
        e=evidence(b,sample,cost=self.context.expected_token_cost,
                   identity=self.context.opponent_id,visual=self.core.visual)
        result=Result(outcome,e,False,reason)
        self.core.terminal=result
        self.record=TerminalRecord(self.context.attempt_id,self.context.opponent_id,outcome,
            self.started_at,now,result,b.arena_digest,b.player_digest,
            sample.arena_digest,sample.player_digest,b.arena_version,b.player_version,
            sample.arena_version,sample.player_version)
        return self.record

    def observe(self,observation):
        if observation.attempt_id!=self.context.attempt_id:
            raise ValueError("wrong attempt")
        if self.core is None:
            raise ValueError("attempt not started")
        if self.record is not None:
            return self.record
        sample=observation.sample
        if sample.observed_at<=self.started_at or sample.observed_at<self.core.latest_at:
            return None
        # Multiple matching history entries are not unique result evidence.
        identity=self.context.opponent_id
        before=self.context.baseline.finished_ids
        after=sample.finished_ids
        ambiguous=(after is not None and after.count(identity)>1)
        if ambiguous:
            sample=replace(sample,finished_ids=None)
        result=self.core.observe(sample,visual=observation.visual)
        if result.pending:
            return result
        b=self.context.baseline
        self.record=TerminalRecord(self.context.attempt_id,identity,result.outcome,
            self.started_at,sample.observed_at,result,b.arena_digest,b.player_digest,
            sample.arena_digest,sample.player_digest,b.arena_version,b.player_version,
            sample.arena_version,sample.player_version)
        return self.record
