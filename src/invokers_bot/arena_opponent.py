"""Verified fields only; historical structured_state.py wire profile."""
from dataclasses import dataclass
from hashlib import sha256
from struct import unpack, pack
from types import MappingProxyType
from typing import Mapping
from .memorypack_slots import read_member_spans
from .snapshot_envelope import SnapshotFormatError

def integer(data):
    if len(data)!=4:
        raise SnapshotFormatError("invalid opponent integer")
    return unpack("<i",data)[0]

def string(data):
    if len(data)<4:
        raise SnapshotFormatError("truncated opponent name")
    n=integer(data[:4])
    try:
        if n>=0 and len(data)==4+2*n:
            return bytes(data[4:]).decode("utf-16-le")
        if n < -1 and len(data)==8+~n:
            value=bytes(data[8:]).decode("utf-8")
            if len(value.encode("utf-16-le"))//2==integer(data[4:8]):
                return value
    except UnicodeError as exc:
        raise SnapshotFormatError("invalid opponent name encoding") from exc
    raise SnapshotFormatError("invalid opponent name length")

@dataclass(frozen=True,slots=True)
class BattlePlayerTeamSetup:
    combat_power: int
    player_id: bytes
    opaque_slots: Mapping[int,bytes]

@dataclass(frozen=True,slots=True)
class ArenaOpponent:
    name: str
    level: int
    arena_points: int
    team_setup: BattlePlayerTeamSetup
    opaque_slots: Mapping[int,bytes]

    @property
    def identity(self):
        return self.team_setup.player_id.hex()

    @property
    def combat_power(self):
        return self.team_setup.combat_power

def parse_team_setup(data):
    s=read_member_spans(data,minimum_count=2)
    power=integer(s[0])
    if power<0 or len(s[1])!=16 or not any(s[1]):
        raise SnapshotFormatError("invalid team power or identity")
    return BattlePlayerTeamSetup(power,bytes(s[1]),MappingProxyType({i:bytes(s[i]) for i in range(2,len(s))}))

def parse_opponent(data):
    s=read_member_spans(data,minimum_count=5)
    return ArenaOpponent(string(s[0]),integer(s[1]),integer(s[3]),parse_team_setup(s[4]),
        MappingProxyType({i:bytes(s[i]) for i in range(len(s)) if i not in (0,1,3,4)}))

def opponent_set_fingerprint(opponents):
    ids=set()
    digest=sha256(b"arena-opponent-set-v1\0")
    for o in sorted(opponents,key=lambda o:o.identity):
        if o.identity in ids:
            raise SnapshotFormatError("duplicate opponent identity")
        ids.add(o.identity)
        name=o.name.encode("utf-8")
        digest.update(o.team_setup.player_id+pack("<iiiI",o.level,o.arena_points,o.combat_power,len(name))+name)
    return digest.hexdigest()
