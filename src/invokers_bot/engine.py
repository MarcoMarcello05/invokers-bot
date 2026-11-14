import json
import time
from pathlib import Path

import cv2

from .capture import ScreenCapture
from .input_win import InputController, f12_pressed
from .models import GameState
from .vision import Vision
from .window import GameWindow

class BotEngine:
    def __init__(self, config, live):
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

    def _observe(self):
        if not self.window.is_alive():
            raise RuntimeError("Game window closed")
        rect = self.window.client_rect()
        frame = self.capture.grab(rect)
        match = self.vision.classify(frame)
        return rect, frame, match, match.state if match else GameState.UNKNOWN

    def _stable(self, state):
        if state == self.last_state:
            self.stable_count += 1
        else:
            self.last_state = state
            self.stable_count = 1
            self.handled_state = GameState.UNKNOWN
        return self.stable_count >= self.config.stable_frames

    def _wait_for_transition(self, previous_state, action):
        timeout = float(action.get("transition_timeout", 1.5))
        expected = {GameState(x) for x in action.get("expect", [])}
        deadline = time.perf_counter() + timeout
        latest = None

        while time.perf_counter() < deadline:
            if f12_pressed():
                return latest
            rect, frame, match, state = self._observe()
            latest = (rect, frame, match, state)
            if state == GameState.UNKNOWN:
                continue
            if expected:
                if state in expected:
                    return latest
            elif state != previous_state:
                return latest
        return latest

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

    def _handle(self, state, match, rect, frame):
        actions = list(self.config.flows.get(state.value, {}).get("actions", []))
        if not actions:
            return

        print(f"[state] {state.value} score={match.score if match else 0:.3f}")
        for action in actions:
            acted = self._perform(action, rect, frame)
            if not acted:
                continue

            if action.get("wait_for_transition", action.get("recapture", True)):
                result = self._wait_for_transition(state, action)
                if result is not None:
                    rect, frame, _match, _state = result

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
                        self._handle(state, match, rect, frame)
                        self.handled_state = state

                delay = period - (time.perf_counter() - started)
                if delay > 0:
                    time.sleep(delay)
        finally:
            self.capture.close()
