"""Deterministic action contracts and evidence evaluation, independent of Windows."""
from dataclasses import dataclass
from enum import Enum
from math import isfinite

from .account_state import AccountObserver, AccountState
from .models import GameState
from .semantic_verification import ResourcePredicate, parse_predicates


class VerificationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    INCONCLUSIVE = "INCONCLUSIVE"


class SuccessMode(str, Enum):
    VISUAL_ONLY = "VISUAL_ONLY"
    STRUCTURED_ONLY = "STRUCTURED_ONLY"
    VISUAL_AND_STRUCTURED = "VISUAL_AND_STRUCTURED"
    VISUAL_OR_STRUCTURED = "VISUAL_OR_STRUCTURED"


@dataclass(frozen=True, slots=True)
class ActionExpectation:
    invalidates_sources: frozenset[str]
    expects_changed_sources: frozenset[str]
    expected_visual_states: frozenset[GameState]
    expects_visual_transition: bool
    timeout: float
    success_mode: SuccessMode
    legacy: bool = False
    semantic_predicates: tuple[ResourcePredicate, ...] = ()

    @classmethod
    def from_action(cls, action):
        def names(key):
            value = action.get(key, [])
            if not isinstance(value, (list, tuple, set, frozenset)) or any(
                not isinstance(x, str) for x in value
            ):
                raise ValueError(f"{key} must be a sequence of names")
            return frozenset(value)

        explicit = any(k in action for k in (
            "invalidates_sources", "expects_source_change", "expects_changed_sources",
            "expects_visual_transition", "expected_visual_states", "success_mode",
            "verification_timeout", "semantic_predicates",
        ))
        invalidates = names("invalidates_sources")
        changed = names("expects_source_change") | names("expects_changed_sources")
        if not (invalidates | changed) <= AccountObserver.source_names():
            raise ValueError("unknown snapshot source in action")
        if not changed <= invalidates:
            raise ValueError("expected changed sources must be invalidated")
        mode = SuccessMode(action.get("success_mode",
            "VISUAL_AND_STRUCTURED" if changed else "VISUAL_ONLY"))
        states = frozenset(GameState(x) for x in names(
            "expected_visual_states" if "expected_visual_states" in action else "expect"))
        if GameState.UNKNOWN in states:
            raise ValueError("UNKNOWN cannot verify a visual action")
        visual = action.get("expects_visual_transition", mode != SuccessMode.STRUCTURED_ONLY)
        if not isinstance(visual, bool):
            raise ValueError("expects_visual_transition must be bool")
        needs_visual = mode != SuccessMode.STRUCTURED_ONLY
        needs_structured = mode != SuccessMode.VISUAL_ONLY
        if visual != needs_visual or bool(changed) != needs_structured:
            raise ValueError("verification mode and required evidence disagree")
        if states and not visual:
            raise ValueError("visual states configured without visual verification")
        timeout = float(action.get("verification_timeout", action.get("transition_timeout", 1.5)))
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError("verification timeout must be finite and positive")
        predicates = parse_predicates(action.get("semantic_predicates", []))
        if any(p.source not in changed for p in predicates):
            raise ValueError("semantic predicate source must expect change")
        return cls(invalidates, changed, states, visual, timeout, mode, not explicit, predicates)


@dataclass(frozen=True, slots=True)
class ActionResult:
    success: bool
    reason: str
    visual_verified: bool = False
    changed_sources: frozenset[str] = frozenset()
    legacy: bool = False

    @property
    def status(self) -> VerificationStatus:
        if self.success:
            return VerificationStatus.SUCCESS
        if self.reason == "CANCELLED":
            return VerificationStatus.CANCELLED
        if self.reason.startswith("TIMEOUT:"):
            if self.visual_verified and self.reason in ("TIMEOUT:EXPECTED_EVIDENCE_MISSING", "TIMEOUT:SEMANTIC_EVIDENCE_MISSING"):
                return VerificationStatus.INCONCLUSIVE
            return VerificationStatus.TIMEOUT
        if self.reason in ("DRY_RUN", "WAIT_ONLY"):
            return VerificationStatus.INCONCLUSIVE
        return VerificationStatus.FAILURE


def baseline_valid(expectation: ActionExpectation, baseline: AccountState | None) -> bool:
    if not expectation.expects_changed_sources:
        return True
    return baseline is not None and all(p.value(baseline) is not None for p in expectation.semantic_predicates) and all(
        (item := baseline.sources.get(name)) is not None
        and item.digest is not None and item.fresh(2.0)
        for name in expectation.expects_changed_sources
    )


def evaluate(expectation: ActionExpectation, previous: GameState, observed: GameState,
             baseline: AccountState | None, current: AccountState | None) -> ActionResult:
    """Compare against the captured pre-input baseline, never a file mtime alone."""
    visual = (expectation.expects_visual_transition
              and observed not in (GameState.UNKNOWN, previous)
              and (not expectation.expected_visual_states
                   or observed in expectation.expected_visual_states))
    changed = set()
    bad_sources = set()
    for name in expectation.expects_changed_sources:
        before = baseline.sources.get(name) if baseline else None
        after = current.sources.get(name) if current else None
        if (before is None or before.digest is None or before.model is None
                or before.error is not None or before.awaiting_change
                or after is None or after.error is not None or after.model is None):
            bad_sources.add(name)
        elif (after.digest is not None and after.digest != before.digest
              and after.checked_at >= before.checked_at and after.fresh(2.0)):
            changed.add(name)
    structured = bool(expectation.expects_changed_sources) and (
        changed == expectation.expects_changed_sources)
    semantic = all(p.matches(baseline, current) for p in expectation.semantic_predicates)
    structured = structured and semantic
    mode = expectation.success_mode
    success = {
        SuccessMode.VISUAL_ONLY: visual,
        SuccessMode.STRUCTURED_ONLY: structured,
        SuccessMode.VISUAL_AND_STRUCTURED: visual and structured,
        SuccessMode.VISUAL_OR_STRUCTURED: visual or structured,
    }[mode]
    # Even OR cannot mask a corrupt or missing declared source.
    if bad_sources:
        success = False
        reason = "SOURCE_UNAVAILABLE:" + ",".join(sorted(bad_sources))
    elif not semantic:
        success = False
        reason = "SEMANTIC_EVIDENCE_MISSING"
    elif success:
        reason = "VERIFIED"
    else:
        reason = "EXPECTED_EVIDENCE_MISSING"
    return ActionResult(success, reason, visual, frozenset(changed), expectation.legacy)
