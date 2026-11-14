"""Captured ArenaBattleStats wire profile, build 0.62.1621.

Evidence: archive research/ADDITIONAL_STRUCTURED_STATE.md and
src/additional_readers.py, correlated schema, league sums and offense quest.
Actual offensive transition still requires live validation.
"""
from dataclasses import dataclass
from struct import unpack, iter_unpack
from types import MappingProxyType
from typing import Mapping
from .memorypack_slots import read_member_spans
from .snapshot_envelope import SnapshotFormatError


@dataclass(frozen=True, slots=True)
class ArenaBattleStats:
    defense_battles_this_week: int
    defense_wins_this_week: int
    defense_battles_last_week: int
    defense_wins_last_week: int
    total_offense_battles: int
    total_offense_wins: int
    total_defense_battles: int
    total_defense_wins: int
    max_league_reached: int
    total_battles_by_league: Mapping[int,int]
    attack_battles_this_week: int
    attack_wins_this_week: int
    attack_battles_last_week: int
    attack_wins_last_week: int
    opaque_slots: Mapping[int,bytes]

    @property
    def league_accounting_matches(self):
        return sum(self.total_battles_by_league.values()) == self.total_offense_battles+self.total_defense_battles


def parse_arena_stats(data):
    slots=read_member_spans(data,minimum_count=18)
    def counter(i):
        if len(slots[i])!=4:
            raise SnapshotFormatError("invalid ArenaStats counter width")
        val=unpack("<i",slots[i])[0]
        if val<0:
            raise SnapshotFormatError("negative ArenaStats counter")
        return val
    values={i:counter(i) for i in (*range(4,13),*range(14,18))}
    for i in (4,6,8,10,14,16):
        if values[i+1]>values[i]:
            raise SnapshotFormatError("ArenaStats wins exceed battles")
    raw=slots[13]
    if len(raw)<4:
        raise SnapshotFormatError("truncated ArenaStats league dictionary")
    count=unpack("<i",raw[:4])[0]
    if count<0 or len(raw)!=4+8*count:
        raise SnapshotFormatError("invalid ArenaStats league dictionary size")
    leagues={}
    previous=None
    for key,value in iter_unpack("<ii",raw[4:]):
        if value<0 or (previous is not None and key<=previous):
            raise SnapshotFormatError("invalid ArenaStats league entry")
        leagues[key]=value
        previous=key
    return ArenaBattleStats(*(values[i] for i in range(4,13)),MappingProxyType(leagues),
        *(values[i] for i in range(14,18)),
        MappingProxyType({i:bytes(slots[i]) for i in (*range(4),*range(18,len(slots)))}))
