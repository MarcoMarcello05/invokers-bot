"""Build 0.62.1621 Arena root; no semantic opponent decoding."""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from struct import unpack
from types import MappingProxyType
from typing import Mapping

from .memorypack_slots import read_member_spans, read_member_spans_at
from .snapshot_envelope import AggregateSnapshot, SnapshotFormatError, _datetime_utc, parse_snapshot, read_snapshot


@dataclass(frozen=True, slots=True)
class OpaqueCollection:
    count: int
    raw: bytes
    entries: tuple[bytes, ...] = ()

    @property
    def entry_hashes(self):
        return tuple(sha256(entry).hexdigest() for entry in self.entries)

    @property
    def fingerprint(self):
        return sha256(b"".join(bytes.fromhex(h) for h in sorted(self.entry_hashes))).hexdigest()


@dataclass(frozen=True, slots=True)
class ArenaState:
    version: int
    updated_at_utc: datetime
    points: int
    defense_raw: bytes
    last_week_process_time: datetime
    last_week_process_ticks: int
    last_opponents_refresh_time: datetime
    last_opponents_refresh_ticks: int
    last_weekly_points: int
    hall_bonuses: OpaqueCollection
    stats_raw: bytes
    opponents: OpaqueCollection
    current_battle_opponent_raw: bytes | None
    finished_opponents: OpaqueCollection
    shop_state_by_period: OpaqueCollection
    last_weekly_reward_raw: bytes | None
    opaque_slots: Mapping[int, bytes]


def _scalar(data, fmt, width):
    if len(data) != width:
        raise SnapshotFormatError("invalid Arena scalar width")
    return unpack(fmt, data)[0]


def _collection(data, *, objects=False):
    if len(data) < 4:
        raise SnapshotFormatError("truncated Arena collection count")
    count = unpack("<i", data[:4])[0]
    if count < 0 or count > len(data)-4 or (count == 0 and len(data) != 4):
        raise SnapshotFormatError("invalid Arena collection count")
    entries = []
    if objects:
        offset = 4
        for _ in range(count):
            start = offset
            _, offset = read_member_spans_at(data, offset, minimum_count=1)
            entries.append(bytes(data[start:offset]))
        if offset != len(data):
            raise SnapshotFormatError("trailing Arena collection bytes")
    return OpaqueCollection(count, bytes(data), tuple(entries))


def _nullable_object(data):
    if bytes(data) == b"\xff":
        return None
    if not data or data[0] == 255:
        raise SnapshotFormatError("invalid nullable Arena object")
    # Internal formatter is not verified for every optional object.
    return bytes(data)


def parse_arena_model(snapshot: AggregateSnapshot) -> ArenaState:
    if snapshot.union_tag != 9 or snapshot.model_name != "PlayerArenaModel":
        raise SnapshotFormatError("expected PlayerArenaModel")
    s = read_member_spans(snapshot.data, minimum_count=18)
    week, week_ticks = _datetime_utc(_scalar(s[5], "<Q", 8))
    refresh, refresh_ticks = _datetime_utc(_scalar(s[7], "<Q", 8))
    read_member_spans(s[10], minimum_count=18)
    return ArenaState(snapshot.version, snapshot.updated_at_utc,
        _scalar(s[0], "<i", 4), bytes(s[1]), week, week_ticks, refresh, refresh_ticks,
        _scalar(s[8], "<i", 4), _collection(s[9]), bytes(s[10]),
        _collection(s[12], objects=True), _nullable_object(s[14]),
        _collection(s[15], objects=True), _collection(s[16]), _nullable_object(s[17]),
        MappingProxyType({i: bytes(s[i]) for i in (2,3,4,6,11,13,*range(18,len(s)))}))


def parse_arena_snapshot(data):
    return parse_arena_model(parse_snapshot(data))


def read_arena_snapshot(path: str | Path):
    return parse_arena_model(read_snapshot(path))
