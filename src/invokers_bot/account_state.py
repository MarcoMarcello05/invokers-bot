"""Read-only observation of independently persisted account aggregates."""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
import time

from .snapshot_envelope import parse_snapshot, SnapshotFormatError
from .player_model import PlayerModelState, parse_player_model
from .heroes_model import PlayerHeroesState, parse_heroes_model
from .relics_model import PlayerRelicsState, parse_relics_model

_SOURCES = {
    "player": ("PlayerModel.dat", parse_player_model),
    "heroes": ("PlayerHeroesModel.dat", parse_heroes_model),
    "relics": ("PlayerRelicsModel.dat", parse_relics_model),
}


@dataclass(frozen=True, slots=True)
class Observation:
    model: PlayerModelState | PlayerHeroesState | PlayerRelicsState | None
    file_stamp: tuple[int, ...] | None
    digest: str | None
    checked_at: float
    error: str | None = None
    awaiting_change: bool = False

    def fresh(self, max_age: float, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        return (self.model is not None and self.error is None
                and not self.awaiting_change and 0 <= now - self.checked_at <= max_age)


@dataclass(frozen=True, slots=True)
class AccountState:
    sources: Mapping[str, Observation]
    changed: frozenset[str]

    def get_fresh(self, source: str, max_age: float = 2.0):
        item = self.sources.get(source)
        return item.model if item and item.fresh(max_age) else None

    @property
    def player(self):
        return self.get_fresh("player")

    @property
    def resources(self):
        player = self.player
        return player.resources if player is not None else None

    @property
    def heroes(self):
        return self.get_fresh("heroes")

    @property
    def relics(self):
        return self.get_fresh("relics")


def _stamp(stat):
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


class AccountObserver:
    """Poll metadata cheaply; reparse changed files, and force reads after inputs.

    Last good data is retained for diagnostics only on failure or invalidation.
    Independent aggregates do not constitute an atomic server-side snapshot.
    """
    def __init__(self, directory: str | Path, interval: float = 0.5):
        if interval <= 0:
            raise ValueError("snapshot interval must be positive")
        self.directory = Path(directory)
        self.interval = interval
        self._last_poll = float("-inf")
        self._items: dict[str, Observation] = {}
        self.state = AccountState(MappingProxyType({}), frozenset())

    def invalidate(self, sources=None):
        names = _SOURCES if sources is None else sources
        for name in names:
            old = self._items.get(name)
            if old:
                self._items[name] = Observation(old.model, old.file_stamp, old.digest,
                                               old.checked_at, old.error, True)
        self._publish(set())

    def _publish(self, changed):
        self.state = AccountState(MappingProxyType(dict(self._items)), frozenset(changed))
        return self.state

    def refresh(self, *, force=False):
        now = time.monotonic()
        if not force and now - self._last_poll < self.interval:
            return self.state
        self._last_poll = now
        changed = set()
        for name, (filename, parser) in _SOURCES.items():
            old = self._items.get(name)
            path = self.directory / filename
            try:
                before = _stamp(path.stat())
                if (not force and old and old.error is None and not old.awaiting_change
                        and before == old.file_stamp):
                    self._items[name] = Observation(old.model, before, old.digest, now)
                    continue
                data = path.read_bytes()
                after = _stamp(path.stat())
                if before != after or len(data) != after[2]:
                    raise OSError("snapshot changed during read")
                digest = sha256(data).hexdigest()
                if old and old.digest == digest and old.model is not None:
                    model = old.model
                    pending = old.awaiting_change
                else:
                    model = parser(parse_snapshot(data))
                    pending = False
                    changed.add(name)
                self._items[name] = Observation(model, after, digest, now,
                                               awaiting_change=pending)
            except (OSError, SnapshotFormatError) as exc:
                self._items[name] = Observation(
                    old.model if old else None, old.file_stamp if old else None,
                    old.digest if old else None, now, type(exc).__name__,
                    old.awaiting_change if old else False)
        return self._publish(changed)
