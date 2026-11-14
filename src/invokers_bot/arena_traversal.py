"""Diagnostic traversal only. No opponent identity, ranking, click or spending."""
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
import time
from uuid import uuid4

from .models import GameState
from .wheel import validate_wheel


@dataclass(frozen=True, slots=True)
class Row:
    fingerprint: str
    region: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class View:
    state: GameState
    digest: str | None
    version: int | None
    count: int | None
    fingerprint: str
    rows: tuple[Row, ...]


@dataclass(frozen=True, slots=True)
class Inventory:
    traversal_id: str
    digest: str | None
    version: int | None
    structured_count: int | None
    pages: tuple[tuple[Row, ...], ...]
    viewport_hashes: tuple[str, ...]
    unique_count: int
    scrolls: int
    reason: str

    def matches(self, observation):
        return bool(observation and observation.fresh(2.0)
                    and observation.digest == self.digest
                    and observation.model.version == self.version
                    and self.reason in ("END_UNCHANGED", "NO_NEW_ROWS", "COUNT_REACHED"))


@dataclass(frozen=True, slots=True)
class Bounds:
    delta: int = -120
    max_scrolls: int = 30
    max_seconds: float = 25.0
    settle_seconds: float = 1.5
    unchanged_frames: int = 3
    no_new_limit: int = 3
    interval: float = 0.1

    def __post_init__(self):
        validate_wheel(self.delta, (0,0,1,1))
        if self.delta >= 0 or not (1 <= self.max_scrolls <= 100 and 2 <= self.unchanged_frames <= 20
                                  and 1 <= self.no_new_limit <= 10):
            raise ValueError("invalid traversal bounds")
        if not all(isfinite(x) and x > 0 for x in (self.max_seconds,self.settle_seconds,self.interval)) or self.max_seconds > 120:
            raise ValueError("invalid traversal timing")


def traverse(observe, scroll, cancelled, bounds=Bounds(), *, clock=time.monotonic, sleep=time.sleep):
    """observe() must return a fresh screen and arena source identity each time.

    Starts at caller's viewport. Seeking top is a caller/calibration prerequisite
    for complete coverage; count match is diagnostic, never semantic identity.
    """
    deadline = clock() + bounds.max_seconds
    pages, hashes, seen = [], [], set()
    scrolls = 0
    baseline = None
    traversal_id = uuid4().hex

    def finish(reason):
        return Inventory(traversal_id, baseline.digest if baseline else None,
            baseline.version if baseline else None, baseline.count if baseline else None,
            tuple(pages), tuple(hashes), len(seen), scrolls, reason)

    def read():
        if cancelled():
            return None, "CANCELLED"
        if clock() >= deadline:
            return None, "TIMEOUT"
        view = observe()
        if cancelled():
            return None, "CANCELLED"
        if clock() >= deadline:
            return None, "TIMEOUT"
        if view.state == GameState.UNKNOWN:
            return None, "UNKNOWN"
        if view.state != GameState.ARENA_LIST:
            return None, "UNEXPECTED_SCREEN"
        if view.digest is None or view.version is None:
            return None, "SOURCE_UNAVAILABLE"
        if baseline and (view.digest,view.version) != (baseline.digest,baseline.version):
            return None, "STALE"
        return view, None

    def capture(view):
        pages.append(view.rows)
        hashes.append(view.fingerprint)
        old = len(seen)
        seen.update(row.fingerprint for row in view.rows)
        return len(seen) - old

    try:
        baseline, reason = read()
        if reason:
            return finish(reason)
        capture(baseline)
        previous = baseline
        no_new = 0
        if baseline.count == 0 or (baseline.count is not None and len(seen) == baseline.count):
            return finish("COUNT_REACHED")
        while scrolls < bounds.max_scrolls:
            current, reason = read()
            if reason:
                return finish(reason)
            if cancelled():
                return finish("CANCELLED")
            if clock() >= deadline:
                return finish("TIMEOUT")
            if not scroll(bounds.delta):
                return finish("INPUT_FAILED")
            scrolls += 1
            settle = min(deadline, clock()+bounds.settle_seconds)
            stable, last = 0, None
            while clock() < settle:
                current, reason = read()
                if reason:
                    return finish(reason)
                stable = stable+1 if current.fingerprint == last else 1
                last = current.fingerprint
                if stable >= bounds.unchanged_frames and last != previous.fingerprint:
                    break
                sleep(min(bounds.interval,max(0,settle-clock())))
            else:
                # Wait the entire settling window before classifying unchanged.
                if clock() >= deadline:
                    return finish("TIMEOUT")
                if stable < bounds.unchanged_frames or last != previous.fingerprint:
                    return finish("UNSTABLE_ROI")
                return finish("END_UNCHANGED")
            no_new = 0 if capture(current) else no_new+1
            previous = current
            if baseline.count is not None and len(seen) == baseline.count:
                return finish("COUNT_REACHED")
            if no_new >= bounds.no_new_limit:
                return finish("NO_NEW_ROWS")
        return finish("MAX_SCROLLS")
    except (OSError, RuntimeError, ValueError):
        return finish("OBSERVATION_FAILED")
