"""Selected read-only PlayerModel fields, build 0.62.1621-0cc5."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from struct import iter_unpack, unpack
from types import MappingProxyType
from typing import Mapping

from .memorypack_slots import read_member_spans
from .snapshot_envelope import (
    AggregateSnapshot, SnapshotFormatError, _datetime_utc, parse_snapshot,
    read_snapshot,
)


@dataclass(frozen=True, slots=True)
class PlayerModelState:
    version: int
    updated_at_utc: datetime
    level: int
    experience: int
    total_experience: int
    energy_sync_time: datetime
    resources: Mapping[int, int]
    resources_gained: Mapping[int, int]
    resources_spent: Mapping[int, int]
    today_total_played_minutes: int
    arena_token_sync_time: datetime
    days_played: int
    support_revision: int
    support_last_read_revision: int
    energy_sync_ticks: int
    arena_token_sync_ticks: int


def parse_resources(data: bytes) -> Mapping[int, int]:
    """Decode one Resources.RawValues dictionary, with numeric keys."""
    (member,) = read_member_spans(data, minimum_count=1, exact_count=1)
    if len(member) < 4:
        raise SnapshotFormatError("truncated dictionary count")
    count = unpack("<i", member[:4])[0]
    if count < 0:
        raise SnapshotFormatError("negative dictionary count")
    expected = 4 + count * 8
    if expected > len(member):
        raise SnapshotFormatError("dictionary count exceeds available pairs")
    if expected < len(member):
        raise SnapshotFormatError("unexpected trailing bytes in dictionary")
    values: dict[int, int] = {}
    for key, value in iter_unpack("<ii", member[4:]):
        if key in values:
            raise SnapshotFormatError(f"duplicate ResourceTypeId: {key}")
        values[key] = value
    return MappingProxyType(values)


def parse_player_model(snapshot: AggregateSnapshot) -> PlayerModelState:
    """Consume an already validated Phase-1 snapshot, never interpret other models."""
    if snapshot.union_tag != 1 or snapshot.model_name != "PlayerModel":
        raise SnapshotFormatError("expected PlayerModel aggregate")
    slots = read_member_spans(snapshot.data, minimum_count=53)

    def scalar(slot: int, fmt: str, width: int) -> int:
        if len(slots[slot]) != width:
            raise SnapshotFormatError(f"invalid scalar width at slot {slot}")
        return unpack(fmt, slots[slot])[0]

    def timestamp(slot: int) -> tuple[datetime, int]:
        try:
            return _datetime_utc(scalar(slot, "<Q", 8))
        except SnapshotFormatError as exc:
            raise SnapshotFormatError(f"invalid DateTime at slot {slot}: {exc}") from exc

    def resources(slot: int) -> Mapping[int, int]:
        try:
            return parse_resources(slots[slot])
        except SnapshotFormatError as exc:
            raise SnapshotFormatError(f"invalid Resources at slot {slot}: {exc}") from exc

    # Reserved slots 7, 12, 13, 14 and all unselected slots stay opaque.
    energy, energy_ticks = timestamp(8)
    arena, arena_ticks = timestamp(34)
    return PlayerModelState(
        version=snapshot.version,
        updated_at_utc=snapshot.updated_at_utc,
        level=scalar(4, "<i", 4),
        experience=scalar(5, "<i", 4),
        total_experience=scalar(6, "<i", 4),
        energy_sync_time=energy,
        resources=resources(9),
        resources_gained=resources(10),
        resources_spent=resources(11),
        today_total_played_minutes=scalar(33, "<i", 4),
        arena_token_sync_time=arena,
        days_played=scalar(43, "<i", 4),
        support_revision=scalar(51, "<q", 8),
        support_last_read_revision=scalar(52, "<q", 8),
        energy_sync_ticks=energy_ticks,
        arena_token_sync_ticks=arena_ticks,
    )


def parse_player_snapshot(data: bytes) -> PlayerModelState:
    return parse_player_model(parse_snapshot(data))


def read_player_snapshot(path: str | Path) -> PlayerModelState:
    return parse_player_model(read_snapshot(path))
