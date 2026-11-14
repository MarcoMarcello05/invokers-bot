"""Read-only observation of independently persisted account aggregates."""
from dataclasses import dataclass, replace
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
from .arena_model import ArenaState, parse_arena_model

_SOURCES = {
    "player": ("PlayerModel.dat", parse_player_model),
    "heroes": ("PlayerHeroesModel.dat", parse_heroes_model),
    "relics": ("PlayerRelicsModel.dat", parse_relics_model),
    "arena": ("PlayerArenaModel.dat", parse_arena_model),
}


@dataclass(frozen=True, slots=True)
class Observation:
    model: PlayerModelState | PlayerHeroesState | PlayerRelicsState | ArenaState | None
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


    @property
    def arena(self):
        return self.get_fresh("arena")


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

    @staticmethod
    def source_names():
        return frozenset(_SOURCES)

    def _names(self, sources):
        names = self.source_names() if sources is None else frozenset(sources)
        if not names <= self.source_names():
            raise ValueError("unknown snapshot source")
        return names

    def invalidate(self, sources=None):
        names = self._names(sources)
        for name in names:
            old = self._items.get(name)
            if old:
                self._items[name] = Observation(old.model, old.file_stamp, old.digest,
                                               old.checked_at, old.error, True)
        self._publish(set())

    def release_visual_only(self, sources, baseline):
        """Release only this action\'s optional invalidations after visual success.

        A pre-existing invalidation or read error is never cleared by navigation.
        """
        for name in self._names(sources):
            old = self._items.get(name)
            pre = baseline.sources.get(name) if baseline else None
            if (old and pre and not pre.awaiting_change and old.error is None
                    and old.model is not None and old.checked_at >= pre.checked_at):
                self._items[name] = replace(old, awaiting_change=False)
        return self._publish(set())

    def _publish(self, changed):
        self.state = AccountState(MappingProxyType(dict(self._items)), frozenset(changed))
        return self.state

    def envelope_metadata(self, filename, expected_tag):
        """Diagnostics only: do not publish a Battle model or raw data."""
        try:
            path = self.directory / filename
            before = _stamp(path.stat())
            data = path.read_bytes()
            if before != _stamp(path.stat()) or len(data) != before[2]:
                raise OSError("snapshot changed during read")
            envelope = parse_snapshot(data)
            if envelope.union_tag != expected_tag:
                raise SnapshotFormatError("wrong diagnostic model")
            return {"version": envelope.version, "digest": sha256(data).hexdigest()}
        except (OSError, SnapshotFormatError) as exc:
            return {"error": type(exc).__name__}

    def refresh(self, *, force=False, sources=None, poll_now=False):
        names = self._names(sources)
        now = time.monotonic()
        if sources is not None and not force:
            raise ValueError("scoped refresh requires force=True")
        if sources is None:
            if not force and not poll_now and now - self._last_poll < self.interval:
                return self.state
            self._last_poll = now
        changed = set()
        for name, (filename, parser) in _SOURCES.items():
            if name not in names:
                continue
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
