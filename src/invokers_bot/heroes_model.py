"""Read-only Hero roster parsing for build 0.62.1621."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from struct import calcsize, iter_unpack, unpack, unpack_from
from types import MappingProxyType
from typing import Mapping

from .memorypack_slots import read_member_spans, read_member_spans_at
from .snapshot_envelope import (
    AggregateSnapshot, SnapshotFormatError, _datetime_utc, parse_snapshot, read_snapshot,
)


@dataclass(frozen=True, slots=True)
class UpgradeableSkill:
    kind: int
    level: int


@dataclass(frozen=True, slots=True)
class HeroState:
    inventory_id: int
    config_id: int
    rank: int
    level: int
    experience: int
    total_experience: int
    locked: bool
    in_storage: bool
    marker: int
    recent_battle_time: datetime | None
    recent_battle_ticks: int | None
    relic_id_by_slot: Mapping[int, int]
    accessory_id_by_slot: Mapping[int, int]
    awake_node_ids: tuple[int, ...]
    awake_level: int
    chroma_enabled: bool
    skin: int
    skill_levels: tuple[UpgradeableSkill, ...]


@dataclass(frozen=True, slots=True)
class PlayerHeroesState:
    version: int
    updated_at_utc: datetime
    last_id: int
    heroes_by_id: Mapping[int, HeroState]
    lobby_hero_ids: tuple[int, ...]
    seen_hero_config_ids: tuple[int, ...]
    starter_hero_id: int
    received_heroes_count: Mapping[int, int]
    # Not decoded until the current nested schema is confirmed.
    opaque_slots: Mapping[int, bytes]


def _scalar(member, fmt):
    if len(member) != calcsize(fmt):
        raise SnapshotFormatError("invalid scalar width")
    return unpack(fmt, member)[0]


def _bool(member):
    value = _scalar(member, "<B")
    if value not in (0, 1):
        raise SnapshotFormatError("invalid bool")
    return bool(value)


def _count(member, minimum_width):
    if len(member) < 4:
        raise SnapshotFormatError("truncated collection count")
    count = unpack_from("<i", member)[0]
    if count < 0 or count > (len(member) - 4) // minimum_width:
        raise SnapshotFormatError("invalid collection count")
    return count


def _pairs(member, fmt):
    count = _count(member, calcsize(fmt))
    if len(member) != 4 + count * calcsize(fmt):
        raise SnapshotFormatError("trailing bytes in collection")
    return tuple(iter_unpack(fmt, member[4:]))


def _map(member, fmt="<ii"):
    result = {}
    for key, value in _pairs(member, fmt):
        if key in result:
            raise SnapshotFormatError("duplicate dictionary key")
        result[key] = value
    return MappingProxyType(result)


def _list(member, fmt="<i"):
    return tuple(v[0] for v in _pairs(member, fmt))


def _time(member):
    # Native Nullable<DateTime>: HasValue at 0, aligned DateTime at 8.
    # Padding is not semantic data.
    if len(member) != 16 or member[0] not in (0, 1):
        raise SnapshotFormatError("invalid nullable DateTime")
    if not member[0]:
        return None, None
    return _datetime_utc(unpack_from("<Q", member, 8)[0])


def _hero(slots):
    time, ticks = _time(slots[9])
    return HeroState(
        inventory_id=_scalar(slots[0], "<i"),
        config_id=_scalar(slots[1], "<q"),
        rank=_scalar(slots[2], "<i"),
        level=_scalar(slots[3], "<i"),
        experience=_scalar(slots[4], "<i"),
        total_experience=_scalar(slots[5], "<i"),
        locked=_bool(slots[6]), in_storage=_bool(slots[7]),
        marker=_scalar(slots[8], "<i"),
        recent_battle_time=time, recent_battle_ticks=ticks,
        relic_id_by_slot=_map(slots[11]), accessory_id_by_slot=_map(slots[12]),
        awake_node_ids=_list(slots[15]), awake_level=_scalar(slots[16], "<i"),
        chroma_enabled=_bool(slots[17]), skin=_scalar(slots[18], "<i"),
        skill_levels=tuple(UpgradeableSkill(*p) for p in _pairs(slots[21], "<ii")),
    )


def parse_hero(data: bytes) -> HeroState:
    return _hero(read_member_spans(data, minimum_count=22))


def parse_heroes_model(snapshot: AggregateSnapshot) -> PlayerHeroesState:
    if snapshot.union_tag != 2 or snapshot.model_name != "PlayerHeroesModel":
        raise SnapshotFormatError("expected PlayerHeroesModel aggregate")
    slots = read_member_spans(snapshot.data, minimum_count=10)
    member = slots[1]
    count = _count(member, 5)
    offset = 4
    heroes = {}
    for _ in range(count):
        if len(member) - offset < 4:
            raise SnapshotFormatError("truncated hero dictionary key")
        key = unpack_from("<i", member, offset)[0]
        offset += 4
        if key in heroes:
            raise SnapshotFormatError("duplicate hero dictionary key")
        fields, offset = read_member_spans_at(member, offset, minimum_count=22)
        hero = _hero(fields)
        if hero.inventory_id != key:
            raise SnapshotFormatError("hero inventory ID disagrees with dictionary key")
        heroes[key] = hero
    if offset != len(member):
        raise SnapshotFormatError("trailing bytes in hero dictionary")
    return PlayerHeroesState(
        version=snapshot.version, updated_at_utc=snapshot.updated_at_utc,
        last_id=_scalar(slots[0], "<i"), heroes_by_id=MappingProxyType(heroes),
        lobby_hero_ids=_list(slots[2]), seen_hero_config_ids=_list(slots[3], "<q"),
        starter_hero_id=_scalar(slots[5], "<q"),
        received_heroes_count=_map(slots[4], "<qi"),
        opaque_slots=MappingProxyType({i: bytes(slots[i]) for i in range(6, len(slots))}),
    )


def parse_heroes_snapshot(data: bytes) -> PlayerHeroesState:
    return parse_heroes_model(parse_snapshot(data))


def read_heroes_snapshot(path: str | Path) -> PlayerHeroesState:
    return parse_heroes_model(read_snapshot(path))
