"""Execution boundary. No production game-action handlers are activated yet."""
from dataclasses import dataclass, field
import time

from safety import Safety
from verification import verify
from vision import LocatedTarget


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    action_id: str
    reason: str
    verification: object = None
    live: bool = False


class Actor:
    # Tests of simulation contracts do not certify Windows click coordinates,
    # emergency stops or runtime state transitions. GUI configuration cannot
    # modify this empty production capability registry.
    LIVE_CAPABILITIES = frozenset()

    def __init__(self, *, safety=None, memory=None, config=None):
        self.safety = safety or Safety()
        self.memory, self.config = memory, config

    def execute(self, action, before, read_state, handler=None, *, live=False):
        del read_state, handler  # Dry-run cannot trigger externally supplied code.
        decision = self.safety.evaluate(action, before, self.config)
        if not decision.allowed:
            return ExecutionResult('blocked', action.action_id, '; '.join(decision.reasons))
        if live:
            return ExecutionResult('blocked', action.action_id, 'No Windows-verified live action capability is enabled')
        return ExecutionResult('planned', action.action_id, 'Dry-run only; no handler was called')

    def simulate(self, action, before, read_state, handler, *, poll_attempts=3, poll_interval=0, now=None, vision_evidence=None):
        """Explicit fake-handler test harness, never used by execute or GUI live mode.

        Refresh/battle reread the complete GameState before and after the action.
        This API can test adapters with fake readers without certifying live UI.
        """
        del before
        if type(poll_attempts) is not int or not 1 <= poll_attempts <= 20 or not 0 <= poll_interval <= 1:
            raise ValueError('Invalid bounded verification polling configuration')
        fresh = read_state()
        decision = self.safety.evaluate(action, fresh, self.config)
        if not decision.allowed:
            return ExecutionResult('blocked', action.action_id, '; '.join(decision.reasons))
        if action.kind == 'QUEST_CLAIM':
            # A planner's desired button label is not an observation. Require
            # separate targeted vision evidence immediately before the action.
            instant = time.time() if now is None else now
            if not isinstance(vision_evidence, LocatedTarget) or vision_evidence.label != 'ANNEHMEN' or vision_evidence.confidence < .85 or not 0 <= instant - vision_evidence.observed_at <= 5:
                return ExecutionResult('blocked', action.action_id, 'Fresh targeted ANNEHMEN button observation is required')
        if self.memory is not None and self.memory.blocked(action, now):
            return ExecutionResult('blocked', action.action_id, 'Persistent per-target failure cooldown')
        try:
            handler(action)
            result = None
            latest = fresh
            for attempt in range(poll_attempts):
                if attempt and poll_interval:
                    time.sleep(poll_interval)
                latest = read_state()
                result = verify(action, fresh, latest)
                if result.verified:
                    break
        except Exception as error:
            if self.memory is not None:
                self.memory.record_failure(action, f'Handler/reader exception: {type(error).__name__}', now)
            return ExecutionResult('unverified', action.action_id, f'Simulation interrupted: {type(error).__name__}')
        if result.verified and result.outcome == 'success':
            if self.memory is not None:
                self.memory.record_success(action, now)
                if action.expected_effects.get('type') == 'campaign_battle':
                    self.memory.clear_campaign_defeat_after_verified_win(action.target)
            return ExecutionResult('verified', action.action_id, result.reason, result)
        if self.memory is not None:
            self.memory.record_failure(action, result.reason, now)
            if result.verified and result.outcome == 'defeat' and action.expected_effects.get('type') == 'campaign_battle':
                main_ids = self.config.get('main_six_ids', []) if isinstance(self.config, dict) else getattr(self.config, 'main_six_ids', [])
                self.memory.record_campaign_defeat(action.target, latest, main_ids, now)
        return ExecutionResult('defeat' if result.verified else 'unverified', action.action_id, result.reason, result)
