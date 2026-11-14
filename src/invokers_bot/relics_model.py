"""Read-only relic inventory for build 0.62.1621-0cc5.

Bonus internals and Randoms are intentionally opaque.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from struct import unpack, unpack_from
from types import MappingProxyType
from typing import Mapping

from .memorypack_slots import read_member_spans, read_member_spans_at
from .snapshot_envelope import (
    AggregateSnapshot, SnapshotFormatError, parse_snapshot, read_snapshot,
)


@dataclass(frozen=True, slots=True)
class RelicState:
    inventory_id: int
    slot: int
    rank: int
    rarity: int
    set: int
    equipped_hero_id: int | None
    level: int
    is_seen: bool
    bonuses_raw: bytes


@dataclass(frozen=True, slots=True)
class PlayerRelicsState:
    version: int
    updated_at_utc: datetime
    last_id: int
    relics_by_id: Mapping[int, RelicState]
    randoms_raw: bytes


def _int32(member: memoryview, field: str) -> int:
    if len(member) != 4:
        raise SnapshotFormatError(f"invalid scalar width: {field}")
    return unpack("<i", member)[0]


def _nullable_int32(member: memoryview) -> int | None:
    # Unmanaged Nullable<int>: HasValue at byte 0, value at byte 4.
    # Native padding and the value of a null instance are not semantic data.
    if len(member) != 8 or member[0] not in (0, 1):
        raise SnapshotFormatError("invalid nullable EquippedHeroId")
    return unpack_from("<i", member, 4)[0] if member[0] else None


def _relic(slots: tuple[memoryview, ...]) -> RelicState:
    flag = slots[7]
    if len(flag) != 1 or flag[0] not in (0, 1):
        raise SnapshotFormatError("invalid IsSeen bool")
    return RelicState(
        inventory_id=_int32(slots[0], "InventoryId"),
        slot=_int32(slots[1], "Slot"),
        rank=_int32(slots[2], "Rank"),
        rarity=_int32(slots[3], "Rarity"),
        set=_int32(slots[4], "Set"),
        equipped_hero_id=_nullable_int32(slots[5]),
        level=_int32(slots[6], "Level"),
        is_seen=bool(flag[0]),
        bonuses_raw=bytes(slots[8]),
    )


def parse_relic(data: bytes) -> RelicState:
    """Decode confirmed fields; additive slots are skipped by length."""
    return _relic(read_member_spans(data, minimum_count=9))


def parse_relics_model(snapshot: AggregateSnapshot) -> PlayerRelicsState:
    if snapshot.union_tag != 4 or snapshot.model_name != "PlayerRelicsModel":
        raise SnapshotFormatError("expected PlayerRelicsModel aggregate")
    slots = read_member_spans(snapshot.data, minimum_count=3)
    member = slots[1]
    if len(member) < 4:
        raise SnapshotFormatError("truncated relic dictionary count")
    count = unpack_from("<i", member)[0]
    # At least an Int32 key, object header and nine delta bytes per entry.
    if count < 0 or count > (len(member) - 4) // 14:
        raise SnapshotFormatError("invalid relic dictionary count")
    offset = 4
    relics: dict[int, RelicState] = {}
    for _ in range(count):
        if len(member) - offset < 4:
            raise SnapshotFormatError("truncated relic dictionary key")
        key = unpack_from("<i", member, offset)[0]
        offset += 4
        if key in relics:
            raise SnapshotFormatError("duplicate relic dictionary key")
        fields, offset = read_member_spans_at(member, offset, minimum_count=9)
        relic = _relic(fields)
        if relic.inventory_id != key:
            raise SnapshotFormatError("relic inventory ID disagrees with dictionary key")
        relics[key] = relic
    if offset != len(member):
        raise SnapshotFormatError("trailing bytes in relic dictionary")
    return PlayerRelicsState(
        version=snapshot.version, updated_at_utc=snapshot.updated_at_utc,
        last_id=_int32(slots[0], "LastId"),
        relics_by_id=MappingProxyType(relics), randoms_raw=bytes(slots[2]),
    )


def parse_relics_snapshot(data: bytes) -> PlayerRelicsState:
    return parse_relics_model(parse_snapshot(data))


def read_relics_snapshot(path: str | Path) -> PlayerRelicsState:
    return parse_relics_model(read_snapshot(path))
