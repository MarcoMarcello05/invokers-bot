import json
import time
from pathlib import Path

import cv2

from .account_state import AccountObserver
from .action_verification import ActionExpectation, ActionResult, baseline_valid, evaluate
from .world_state import WorldState
from .capture import ScreenCapture
from .input_win import InputController, f12_pressed
from .models import GameState
from .vision import Vision
from .window import GameWindow

class BotEngine:
    def __init__(self, config, live, snapshot_dir=None):
        self.config = config
        self.live = live
        self.window = GameWindow.find(config.window_title_contains)
        capture_fps = int(config.raw.get("runtime", {}).get("capture_fps", 60))
        self.capture = ScreenCapture(target_fps=capture_fps)
        self.vision = Vision(config)
        self.input = InputController()
        self.runtime_dir = Path("runtime")
        self.runtime_dir.mkdir(exist_ok=True)
        self.last_state = GameState.UNKNOWN
        self.stable_count = 0
        self.handled_state = GameState.UNKNOWN
        self.unknown_count = 0
        self.world_state = WorldState()
        self.account_observer = (AccountObserver(snapshot_dir) if snapshot_dir else None)

    def _refresh_account(self, *, force=False, sources=None, poll_now=False):
        if self.account_observer is not None:
            state = self.account_observer.refresh(force=force, sources=sources, poll_now=poll_now)
            self.world_state.facts['account'] = state
            return state
        return None

    def _observe(self):
        if not self.window.is_alive():
            raise RuntimeError("Game window closed")
        rect = self.window.client_rect()
        frame = self.capture.grab(rect)
        match = self.vision.classify(frame)
        state = match.state if match else GameState.UNKNOWN
        self.world_state.screen = state
        self.world_state.confidence = match.score if match else 0.0
        self.world_state.observed_at = time.time()
        self._refresh_account()
        return rect, frame, match, state

    def _stable(self, state):
        if state == self.last_state:
            self.stable_count += 1
        else:
            self.last_state = state
            self.stable_count = 1
            self.handled_state = GameState.UNKNOWN
        return self.stable_count >= self.config.stable_frames

    def _verify_action(self, previous_state, expectation, baseline):
        deadline = time.monotonic() + expectation.timeout
        last = ActionResult(False, "NO_POST_ACTION_OBSERVATION")
        stable_state = GameState.UNKNOWN
        stable_frames = 0
        while time.monotonic() < deadline:
            if f12_pressed():
                return ActionResult(False, "CANCELLED")
            try:
                _, _, _, state = self._observe()
                if state == stable_state:
                    stable_frames += 1
                else:
                    stable_state, stable_frames = state, 1
                visual = state if stable_frames >= self.config.stable_frames else GameState.UNKNOWN
                current = self._refresh_account(force=True, sources=expectation.invalidates_sources) if expectation.invalidates_sources else (
                    self.account_observer.state if self.account_observer else None)
                last = evaluate(expectation, previous_state, visual, baseline, current)
            except (OSError, RuntimeError, ValueError) as exc:
                return ActionResult(False, "OBSERVATION_FAILED:" + type(exc).__name__)
            if f12_pressed():
                return ActionResult(False, "CANCELLED")
            if time.monotonic() >= deadline:
                break
            if last.success:
                if self.account_observer is not None and last.visual_verified and expectation.invalidates_sources:
                    optional = expectation.invalidates_sources - expectation.expects_changed_sources
                    self.world_state.facts['account'] = self.account_observer.release_visual_only(optional, baseline)
                return last
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        return ActionResult(False, "TIMEOUT:" + last.reason,
                            last.visual_verified, last.changed_sources, expectation.legacy)

    def _perform(self, action, rect, frame):
        kind = str(action.get("type", "wait"))

        if action.get("purchase", False) and not self.config.allow_purchase_actions:
            print("[safety] purchase action blocked")
            return False

        if kind == "wait":
            time.sleep(float(action.get("seconds", 0.05)))
            return True

        if kind == "click_template":
            hit = self.vision.find_target(frame, action)
            if not hit:
                print("[action] target not found:", action.get("template"))
                return False
            cx, cy = hit.center
            sx, sy = rect.left + cx, rect.top + cy
            if self.live:
                self.window.activate()
                self.input.click_screen(sx, sy)
            print(f"[{'LIVE' if self.live else 'DRY'}] click {action.get('template')} score={hit.score:.3f} at {sx},{sy}")
            return True

        if kind == "click_norm":
            sx = rect.left + round(rect.width * float(action["x"]))
            sy = rect.top + round(rect.height * float(action["y"]))
            if self.live:
                self.window.activate()
                self.input.click_screen(sx, sy)
            print(f"[{'LIVE' if self.live else 'DRY'}] click_norm -> {sx},{sy}")
            return True

        if kind == "key":
            if self.live:
                self.window.activate()
                self.input.key(str(action["key"]))
            print(f"[{'LIVE' if self.live else 'DRY'}] key {action['key']}")
            return True

        raise ValueError(f"Unknown action: {kind}")

    def _execute_live_action(self, action, state, rect, frame):
        try:
            expectation = ActionExpectation.from_action(action)
        except (TypeError, ValueError) as exc:
            return ActionResult(False, "INVALID_EXPECTATION:" + str(exc))
        baseline = (self._refresh_account(force=True, sources=expectation.invalidates_sources)
                    if expectation.invalidates_sources else self._refresh_account(poll_now=True))
        if not baseline_valid(expectation, baseline):
            return ActionResult(False, "BASELINE_UNAVAILABLE")
        if f12_pressed():
            return ActionResult(False, "CANCELLED")
        try:
            acted = self._perform(action, rect, frame)
        except OSError:
            # SendInput may have partially succeeded. Keep affected facts pending.
            if self.account_observer is not None:
                self.account_observer.invalidate(expectation.invalidates_sources)
                self._refresh_account(force=True, sources=expectation.invalidates_sources)
            return ActionResult(False, "INPUT_FAILED")
        if not acted:
            return ActionResult(False, "INPUT_NOT_SENT")
        if self.account_observer is not None and expectation.invalidates_sources:
            self.account_observer.invalidate(expectation.invalidates_sources)
            self.world_state.facts['account'] = self.account_observer.state
        elif self.account_observer is not None:
            self._refresh_account(poll_now=True)
        return self._verify_action(state, expectation, baseline)

    def _handle(self, state, match, rect, frame):
        actions = list(self.config.flows.get(state.value, {}).get("actions", []))
        if not actions:
            return ActionResult(False, "NO_ACTION")
        print(f"[state] {state.value} score={match.score if match else 0:.3f}")
        for action in actions:
            if f12_pressed():
                result = ActionResult(False, "CANCELLED")
                break
            kind = action.get("type", "wait")
            if self.live and kind != "wait":
                result = self._execute_live_action(action, state, rect, frame)
                # Every real input returns to the observation loop; never chain
                # further actions with stale screen data, even after success.
                break
            if not self._perform(action, rect, frame):
                result = ActionResult(False, "INPUT_NOT_SENT")
                break
            result = ActionResult(False, "WAIT_ONLY" if kind == "wait" else "DRY_RUN")
        self.world_state.facts["last_action_result"] = result
        print(f"[verification] {result.status.value} {result.reason} success={result.success}"
              f" legacy={result.legacy} visual={result.visual_verified}"
              f" changed={sorted(result.changed_sources)}")
        return result

    def run(self):
        print(json.dumps({
            "mode": "LIVE" if self.live else "DRY",
            "window": self.window.title,
            "dpi": self.window.dpi(),
            "capture": self.capture.backend,
            "decision_fps": self.config.fps,
            "f12_abort": True,
        }))

        period = 1 / max(1.0, self.config.fps)
        try:
            while True:
                started = time.perf_counter()
                if f12_pressed():
                    print("[stop] F12")
                    break

                rect, frame, match, state = self._observe()

                if state == GameState.UNKNOWN:
                    self.unknown_count += 1
                    self.stable_count = 0
                    self.last_state = state
                    self.handled_state = state
                    if self.unknown_count == self.config.unknown_dump_after:
                        p = self.runtime_dir / f"unknown-{time.strftime('%Y%m%d-%H%M%S')}.png"
                        cv2.imwrite(str(p), frame)
                        print("[vision] persistent UNKNOWN; screenshot saved; no input sent")
                else:
                    self.unknown_count = 0
                    if self._stable(state) and self.handled_state != state:
                        result = self._handle(state, match, rect, frame)
                        # Suppress blind retries on the same screen even on failure.
                        # handled_state tracks attempts, not verification success.
                        self.handled_state = state

                delay = period - (time.perf_counter() - started)
                if delay > 0:
                    time.sleep(delay)
        finally:
            self.capture.close()
