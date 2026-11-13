"""Bounded integration of the existing Arena planner, navigation and verifiers."""
from dataclasses import dataclass, field, replace
import json
import math
from pathlib import Path
import time

from autonomy_bridge import plan_arena
from bot_actions import resource_values, section_value
from safety import Safety
from verification import verify
from arena_snapshot import SnapshotError


@dataclass
class ArenaFrame:
    state: str
    rows: list = field(default_factory=list)
    selected_name: str | None = None
    own_power: int | None = None
    token_cost: int | None = None
    token_currency_verified: bool = False
    auto_off: bool = False
    controls: dict = field(default_factory=dict)
    safe_foreground: bool = True
    free_refresh_verified: bool = False


class ArenaError(RuntimeError):
    def __init__(self, code, detail=''):
        super().__init__(detail or code)
        self.code = code


class ArenaAutopilot:
    def __init__(self, source, desktop, config, memory, output_dir, *, mode='dry',
                 navigate=False, live_armed=False, cycles=1, ui_timeout=10,
                 battle_timeout=180, snapshot_timeout=10, poll=.25,
                 max_recovery=1, max_refreshes=0, clock=time.monotonic, sleep=time.sleep):
        if mode not in ('dry', 'live', 'simulation') or not 1 <= cycles <= 10:
            raise ValueError('Mode/cycle limit invalid')
        if any(not math.isfinite(v) or v <= 0 for v in (ui_timeout, battle_timeout, snapshot_timeout, poll)):
            raise ValueError('Timeouts must be finite and positive')
        if not 0 <= max_recovery <= 2:
            raise ValueError('Recovery limit must be 0..2')
        if type(max_refreshes) is not int or not 0 <= max_refreshes <= 3:
            raise ValueError('Free refresh limit must be 0..3')
        self.source, self.desktop, self.config, self.memory = source, desktop, config, memory
        self.output_dir = Path(output_dir)
        self.mode, self.navigate, self.live_armed = mode, navigate, live_armed
        self.cycles, self.ui_timeout, self.battle_timeout = cycles, ui_timeout, battle_timeout
        self.snapshot_timeout, self.poll, self.max_recovery = snapshot_timeout, poll, max_recovery
        self.clock, self.sleep = clock, sleep
        self.events, self.results, self.excluded = [], [], set()
        self.action = None
        self.last_frame = None
        self.max_refreshes, self.refreshes = max_refreshes, 0

    def refresh_free(self, before):
        from bot_actions import Action
        frame = self.ensure_list()
        if not frame.free_refresh_verified:
            raise ArenaError('REFRESH_COST_UNVERIFIED')
        action = Action('free-refresh', 'ARENA_REFRESH', 'arena', resource_costs={},
                        preconditions={'costs_verified': True}, expected_effects={'type': 'arena_refresh'})
        decision = Safety().evaluate(action, before.state, self.config)
        if not decision.allowed:
            raise ArenaError('SAFETY_BLOCKED', '; '.join(decision.reasons))
        self.event('ACT', command='refresh')
        self.input('refresh', frame)
        self.refreshes += 1
        latest = None
        def refreshed():
            nonlocal latest
            latest = self.source.read()
            return verify(action, before.state, latest.state).verified
        self.wait(refreshed, self.snapshot_timeout, 'REFRESH_NOT_VERIFIED')
        self.wait_screen({'ARENA_LIST'})
        self.event('REPLAN', refreshes=self.refreshes)
        return latest

    def event(self, phase, **detail):
        row = {'phase': phase, 'elapsed_clock': self.clock(), **detail}
        self.events.append(row)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with (self.output_dir/'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')

    def check_stop(self):
        if self.desktop.stopped():
            raise ArenaError('STOP_REQUESTED')

    def capture(self):
        self.check_stop()
        frame = self.desktop.observe()
        if not frame.safe_foreground:
            raise ArenaError('FOREGROUND_LOST')
        if frame.state == 'DIALOG':
            raise ArenaError('UNKNOWN_DIALOG', 'Unknown/premium dialogs are never confirmed')
        self.last_frame = frame
        return frame

    def wait(self, predicate, timeout, code):
        deadline = self.clock() + timeout
        for _ in range(min(2000, math.ceil(timeout/self.poll)+1)):
            self.check_stop()
            result = predicate()
            if result:
                return result
            if self.clock() >= deadline:
                break
            self.sleep(self.poll)
        raise ArenaError(code)

    def wait_screen(self, states, timeout=None):
        return self.wait(lambda: (f if (f := self.capture()).state in states else None),
                         timeout or self.ui_timeout, 'UI_TIMEOUT')

    def input(self, command, frame, target=None):
        self.check_stop()
        if self.mode == 'dry' and not self.navigate:
            raise ArenaError('DRY_RUN_INPUT_BLOCKED')
        if command == 'start_battle' and self.mode == 'dry':
            raise ArenaError('DRY_RUN_BATTLE_BLOCKED')
        self.desktop.perform(command, frame, target)

    def ensure_list(self):
        frame = self.capture()
        for _ in range(3):
            if frame.state == 'ARENA_LIST':
                return frame
            if frame.state == 'HOME':
                self.input('open_battles', frame)
                frame = self.wait_screen({'BATTLE_MENU', 'ARENA_LIST'})
            elif frame.state == 'BATTLE_MENU':
                self.input('open_arena', frame)
                frame = self.wait_screen({'ARENA_LIST'})
            else:
                raise ArenaError('UNEXPECTED_SCREEN', frame.state)
        raise ArenaError('NAVIGATION_LIMIT')

    def current_target(self, snapshot):
        candidates = (section_value(snapshot.state, 'arena') or {}).get('opponents', [])
        return next((o for o in candidates if o['player_id_bytes'] == self.action.target['player_id_bytes']), None)

    def verify_target(self, snapshot):
        target = self.current_target(snapshot)
        if target is None or target['combat_power'] != self.action.target['combat_power'] or target['name'] != self.action.target['name']:
            raise ArenaError('STALE_TARGET', 'Selected identity/power changed; stop and replan from fresh data')
        if target['combat_power'] >= self.config.arena_combat_power:
            raise ArenaError('OPPONENT_NOT_WEAKER')
        return target

    def verify_formation(self, frame):
        from arena_actor import _norm
        if frame.state != 'FORMATION' or _norm(frame.selected_name or '') != _norm(self.action.target['name']):
            raise ArenaError('FORMATION_IDENTITY_MISMATCH')
        if frame.own_power != self.config.arena_combat_power:
            raise ArenaError('OWN_POWER_UNCONFIRMED', 'UI must corroborate, never replace, configured own power')
        if frame.token_cost != 1 or not frame.token_currency_verified:
            raise ArenaError('COST_NOT_VERIFIED', 'Require exactly one recognized Arena token, never premium currency')

    def recover(self):
        self.event('RECOVER')
        # No blind ESC/Alt+Left, dialog confirmation, refresh or battle retry.
        for _ in range(self.max_recovery):
            frame = self.capture()
            if frame.state == 'ARENA_LIST':
                return True
            if frame.state == 'FORMATION' and 'back' in frame.controls:
                self.input('back', frame)
                self.wait_screen({'ARENA_LIST'})
                return True
            break
        return False

    def run(self):
        try:
            self.config.validate()
            if not self.config.modules.arena:
                raise ArenaError('ARENA_DISABLED')
            if self.mode == 'live' and not self.live_armed:
                raise ArenaError('LIVE_DISABLED', 'Explicit activation and a matching navigation preflight are required')
            if self.mode == 'simulation' and not getattr(self.desktop, 'simulated', False):
                raise ArenaError('SIMULATION_BACKEND_REQUIRED')
            if self.mode == 'live' and getattr(self.desktop, 'simulated', False):
                raise ArenaError('SIMULATION_CANNOT_BE_LIVE')
            for cycle in range(self.cycles):
                self.event('OBSERVE', cycle=cycle+1)
                snapshot = self.source.read()
                self.event('PLAN')
                self.action = plan_arena(snapshot, self.config, self.excluded)
                while self.action is None and self.refreshes < self.max_refreshes and self.mode in ('live','simulation'):
                    snapshot = self.refresh_free(snapshot)
                    self.action = plan_arena(snapshot, self.config, self.excluded)
                if self.action is None:
                    raise ArenaError('NO_ELIGIBLE_OPPONENT', 'No automatic paid refresh or premium fallback')
                while self.memory.blocked(self.action):
                    self.excluded.add(self.action.target['player_id_bytes'])
                    self.action = plan_arena(snapshot, self.config, self.excluded)
                    if self.action is None:
                        raise ArenaError('ALL_TARGETS_COOLDOWN')
                from arena_actor import _norm
                records = (section_value(snapshot.state, 'arena') or {}).get('opponents', [])
                if sum(_norm(o['name']) == _norm(self.action.target['name']) for o in records) != 1:
                    raise ArenaError('AMBIGUOUS_IDENTITY')
                if any(type(resource_values(snapshot.state).get(k)) is not int for k in ('Gem', 'Arena_Token')):
                    raise ArenaError('RESOURCES_UNKNOWN')
                self.event('PLAN_SELECTED', target=self.action.target)
                if self.mode == 'dry' and not self.navigate:
                    frame = self.capture()
                    return self.report('DRY_RUN', ui_state=frame.state, target=self.action.target,
                                       preflight_passed=False, note='No inputs; use --navigate for bounded nonspending navigation audit')
                frame = self.ensure_list()
                self.event('ACT', command='locate_selected')
                location = self.desktop.locate(self.action.target, self.capture, self.check_stop)
                if location is None:
                    raise ArenaError('TARGET_NOT_FOUND', 'The selected weakest candidate was not found; do not substitute a visible stronger one')
                frame, point = location
                # The backend must prove a unique name and unique FIGHT button in this row.
                self.verify_target(self.source.read())
                self.input('open_formation', frame, {'opponent': self.action.target, 'point': point})
                formation = self.wait_screen({'FORMATION'})
                self.verify_formation(formation)
                fresh = self.source.read()
                self.verify_target(fresh)
                for currency in ('Gem', 'Arena_Token'):
                    if resource_values(fresh.state).get(currency) != resource_values(snapshot.state).get(currency):
                        raise ArenaError('NAVIGATION_CHANGED_RESOURCES')
                self.action = replace(self.action, preconditions={**self.action.preconditions, 'costs_verified': True})
                decision = Safety().evaluate(self.action, fresh.state, self.config)
                if not decision.allowed:
                    raise ArenaError('SAFETY_BLOCKED', '; '.join(decision.reasons))
                if self.mode == 'dry':
                    return self.report('WOULD_START_BATTLE', target=self.action.target,
                                       preflight_passed=True, cost={'Arena_Token': 1}, own_power=self.config.arena_combat_power)
                self.event('ACT', command='start_battle', target=self.action.target)
                self.input('start_battle', formation, self.action.target)
                battle = self.wait_screen({'BATTLE', 'VICTORY', 'DEFEAT'})
                if battle.state != 'BATTLE' or not battle.auto_off:
                    raise ArenaError('AUTO_NOT_CONFIRMED_OFF')
                def battle_result():
                    frame = self.capture()
                    if frame.state == 'BATTLE' and not frame.auto_off:
                        raise ArenaError('AUTO_NOT_CONFIRMED_OFF')
                    if frame.state not in ('BATTLE', 'VICTORY', 'DEFEAT'):
                        raise ArenaError('UNKNOWN_BATTLE_SCREEN')
                    return frame if frame.state in ('VICTORY', 'DEFEAT') else None
                result_frame = self.wait(battle_result, self.battle_timeout, 'BATTLE_TIMEOUT')
                self.event('VERIFY', ui_result=result_frame.state)
                latest = None
                verification = None
                def structured_result():
                    nonlocal latest, verification
                    latest = self.source.read()  # Always reread field 12 and resources after battle.
                    verification = verify(self.action, fresh.state, latest.state)
                    return verification if verification.verified else None
                try:
                    self.wait(structured_result, self.snapshot_timeout, 'RESULT_NOT_VERIFIED')
                except ArenaError as error:
                    raise ArenaError(error.code, verification.reason if verification else str(error)) from error
                expected = 'success' if result_frame.state == 'VICTORY' else 'defeat'
                if verification.outcome != expected:
                    raise ArenaError('RESULT_MISMATCH')
                if expected == 'success':
                    self.memory.record_success(self.action)
                else:
                    self.memory.record_failure(self.action, 'VERIFIED_DEFEAT')
                self.excluded.add(self.action.target['player_id_bytes'])
                self.input('return_to_arena', result_frame)
                self.wait_screen({'ARENA_LIST'})
                self.source.read()  # No reuse of the pre-fight candidate list.
                self.results.append({'target': self.action.target, 'outcome': verification.outcome,
                                     'evidence': verification.evidence})
                self.event('REPLAN', completed=len(self.results))
            return self.report('COMPLETED')
        except (ArenaError, SnapshotError, ValueError, OSError) as error:
            return self.fail(getattr(error, 'code', 'INVALID_STATE'), str(error))
        except KeyboardInterrupt:
            return self.fail('STOP_REQUESTED', 'Keyboard interrupt')
        except Exception as error:
            # Includes FailSafeException/OCR backend failures; never continue blind.
            return self.fail('STOP_REQUESTED' if type(error).__name__ == 'FailSafeException' else 'UI_BACKEND_ERROR', type(error).__name__ + ': ' + str(error))

    def fail(self, code, detail):
        screenshot = None
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            screenshot = self.desktop.screenshot(self.output_dir/'failure.png')
        except Exception:
            pass
        if self.action is not None and code != 'STOP_REQUESTED':
            try:
                self.memory.record_failure(self.action, code)
            except (OSError, ValueError):
                detail += '; failure-memory persistence also failed'
        recovered = False
        if code not in ('STOP_REQUESTED', 'AUTO_NOT_CONFIRMED_OFF', 'FOREGROUND_LOST', 'UNKNOWN_DIALOG',
                        'LIVE_DISABLED', 'STALE_SNAPSHOT', 'RESULT_NOT_VERIFIED', 'BATTLE_TIMEOUT'):
            try:
                recovered = self.recover()
            except Exception:
                pass
        self.event('SAFE_STOP', code=code, detail=detail, screenshot=str(screenshot) if screenshot else None, recovered=recovered)
        return self.report('SAFE_STOP', code=code, detail=detail, screenshot=str(screenshot) if screenshot else None, recovered=recovered)

    def report(self, status, **extra):
        result = {'status': status, 'mode': self.mode, 'live_tested': False,
                  'completed_cycles': len(self.results), 'results': self.results,
                  'events': self.events, **extra}
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir/'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
