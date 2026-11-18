"""Read-only PlayerQuestsModel, build 0.62.1621. No objective inference."""
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from struct import unpack, unpack_from, iter_unpack
from types import MappingProxyType
from typing import Mapping

from .memorypack_slots import read_member_spans, read_member_spans_at
from .snapshot_envelope import AggregateSnapshot, SnapshotFormatError, _datetime_utc, parse_snapshot, read_snapshot


class QuestKind(IntEnum):
    PERIODIC=1
    ACHIEVEMENT=2
    BOOK=3


class QuestStateId(IntEnum):
    UNKNOWN=0
    NEW=1
    IN_PROGRESS=2
    COMPLETED=3


class QuestPeriodicGroup(IntEnum):
    DAILY=1
    WEEKLY=2
    MONTHLY=3
    ADVANCE=4
    CLAN=5


@dataclass(frozen=True, slots=True)
class QuestState:
    quest_id: int
    prototype_id: int
    state_id: int
    time_started_utc: datetime
    time_started_ticks: int
    progress: int
    kind: QuestKind
    group_or_page: int
    source_union_tag: int


@dataclass(frozen=True, slots=True)
class PeriodicWindow:
    group: int
    start_time_utc: datetime
    finish_time_utc: datetime | None
    start_ticks: int
    finish_ticks: int | None


@dataclass(frozen=True, slots=True)
class AchievementProgress:
    group_id: int
    current_level: int
    progress: int


@dataclass(frozen=True, slots=True)
class PlayerQuestsState:
    version: int
    updated_at_utc: datetime
    last_quest_id: int
    active_by_id: Mapping[int, QuestState]
    completed_prototype_ids: tuple[int,...]
    periodic_groups: Mapping[int, PeriodicWindow]
    achievement_groups: Mapping[int, AchievementProgress]
    total_completed_quests: int


def _int(member):
    if len(member)!=4:
        raise SnapshotFormatError("invalid quest Int32 width")
    return unpack("<i",member)[0]


def _time(member):
    if len(member)!=8:
        raise SnapshotFormatError("invalid quest DateTime width")
    return _datetime_utc(unpack("<Q",member)[0])


def _nullable_time(member):
    # Native unmanaged Nullable<DateTime>, bool at 0 and aligned value at 8.
    if len(member)!=16 or member[0] not in (0,1):
        raise SnapshotFormatError("invalid quest nullable time")
    return _time(member[8:]) if member[0] else (None,None)


def _count(member,min_width):
    if len(member)<4:
        raise SnapshotFormatError("truncated quest collection")
    count=unpack_from("<i",member)[0]
    if count<0 or count>(len(member)-4)//min_width:
        raise SnapshotFormatError("invalid quest collection count")
    return count


def _dictionary(member,decode,*,union=False):
    count=_count(member,6 if union else 5)
    offset=4
    result={}
    for _ in range(count):
        if len(member)-offset<4:
            raise SnapshotFormatError("truncated quest key")
        key=unpack_from("<i",member,offset)[0]
        offset+=4
        if key in result:
            raise SnapshotFormatError("duplicate quest dictionary key")
        if union:
            if offset>=len(member):
                raise SnapshotFormatError("missing quest union tag")
            tag=member[offset]
            offset+=1
            if tag not in (1,2,3):
                raise SnapshotFormatError(f"unsupported quest union tag: {tag}")
            fields,offset=read_member_spans_at(member,offset,minimum_count=51)
            result[key]=decode(key,fields,tag)
        else:
            fields,offset=read_member_spans_at(member,offset,minimum_count=2)
            result[key]=decode(key,fields)
    if offset!=len(member):
        raise SnapshotFormatError("trailing quest dictionary bytes")
    return MappingProxyType(result)


def _quest(key,s,tag):
    quest_id=_int(s[0])
    if key!=quest_id or key<=0:
        raise SnapshotFormatError("quest ID disagrees with active dictionary key")
    prototype,progress=_int(s[1]),_int(s[5])
    if prototype<=0 or progress<0:
        raise SnapshotFormatError("invalid quest prototype/progress")
    # Only mapped slots are decoded; reserved and appended slots are skipped.
    started,ticks=_time(s[3])
    return QuestState(quest_id,prototype,_int(s[2]),started,ticks,
                      progress,QuestKind(tag),_int(s[50]),tag)


def _periodic(key,s):
    start,start_ticks=_time(s[0])
    finish,finish_ticks=_nullable_time(s[1])
    return PeriodicWindow(key,start,finish,start_ticks,finish_ticks)


def _achievement(key,s):
    return AchievementProgress(key,_int(s[0]),_int(s[1]))


def parse_quests_model(snapshot: AggregateSnapshot) -> PlayerQuestsState:
    if snapshot.union_tag!=8 or snapshot.model_name!="PlayerQuestsModel":
        raise SnapshotFormatError("expected PlayerQuestsModel aggregate")
    s=read_member_spans(snapshot.data,minimum_count=6)
    count=_count(s[2],4)
    if len(s[2])!=4+count*4:
        raise SnapshotFormatError("trailing completed prototype bytes")
    completed=tuple(v[0] for v in iter_unpack("<i",s[2][4:]))
    return PlayerQuestsState(snapshot.version,snapshot.updated_at_utc,
        _int(s[0]),_dictionary(s[1],_quest,union=True),completed,
        _dictionary(s[3],_periodic),_dictionary(s[4],_achievement),_int(s[5]))


def parse_quests_snapshot(data):
    return parse_quests_model(parse_snapshot(data))


def read_quests_snapshot(path: str | Path):
    return parse_quests_model(read_snapshot(path))
