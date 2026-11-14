from struct import pack
import pytest
from invokers_bot.arena_model import parse_arena_snapshot
from invokers_bot.account_state import AccountObserver
from invokers_bot.snapshot_envelope import SnapshotFormatError

STAMP=pack("<Q",621355968000000000 | (1<<62))

def member_length(size):
    """MemoryPack WriteVarInt(int): signed marker, little-endian payload."""
    if not 0 <= size <= 2147483647:
        raise ValueError("member length outside Int32 range")
    if size <= 127:
        return bytes([size])
    if size <= 32767:
        return b"\x84"+pack("<h",size)
    return b"\x82"+pack("<i",size)

def obj(slots):
    return bytes([len(slots)])+b"".join(member_length(len(s)) for s in slots)+b"".join(slots)

def opponent(name, identity, power=6151):
    return obj([pack("<i",len(name))+name.encode("utf-16-le"),pack("<i",7),b"opaque",pack("<i",534),obj([pack("<i",power),bytes([identity])*16,b"team-opaque"])])

def root():
    s=[b""]*18
    s[0]=pack("<i",42)
    s[5]=s[7]=STAMP
    s[8]=pack("<i",12)
    s[9]=s[16]=bytes(4)
    s[10]=obj([b""]*4+[bytes(4)]*14)
    s[12]=pack("<i",2)+opponent("same",1)+opponent("same",2)
    s[14]=s[17]=b"\xff"
    s[15]=pack("<i",1)+obj([b"finished"])
    return s

def envelope(payload):
    size=len(payload)
    vi=member_length(size)
    return b"\x09\x03\x08\x08"+vi+pack("<q",3)+STAMP+payload

def test_arena():
    s=root()
    state=parse_arena_snapshot(envelope(obj(s)))
    assert (state.points,state.last_weekly_points,state.version)==(42,12,3)
    assert state.opponents.count==2 and state.opponents.entries==(opponent("same",1),opponent("same",2))
    assert state.finished_opponents.count==1 and state.current_battle_opponent_raw is None
    assert state.hall_bonuses.count==state.shop_state_by_period.count==0
    s[12]=pack("<i",2)+opponent("same",2)+opponent("same",1)
    assert parse_arena_snapshot(envelope(obj(s))).opponents.fingerprint==state.opponents.fingerprint

@pytest.mark.parametrize("slot,value",[(0,b""),(5,b""),(12,pack("<i",3)+obj([b"a"])),(12,pack("<i",-1)),(15,bytes(4)+b"x"),(10,b""),(14,b"\xffx")])
def test_bad(slot,value):
    s=root();s[slot]=value
    with pytest.raises(SnapshotFormatError):
        parse_arena_snapshot(envelope(obj(s)))

def test_truncated():
    with pytest.raises(SnapshotFormatError):
        parse_arena_snapshot(envelope(obj(root())[:-1]))

def test_observer(tmp_path):
    path=tmp_path/"PlayerArenaModel.dat"
    blob=envelope(obj(root()));path.write_bytes(blob)
    observer=AccountObserver(tmp_path)
    assert observer.refresh(force=True,sources={"arena"}).arena.points==42
    assert path.read_bytes()==blob
    path.write_bytes(b"bad")
    assert observer.refresh(force=True,sources={"arena"}).arena is None


@pytest.mark.parametrize("size,expected",[(127,"7f"),(128,"848000"),(255,"84ff00"),(256,"840001"),(32767,"84ff7f"),(32768,"8200800000")])
def test_length_wire_boundaries(size,expected):
    from invokers_bot.memorypack_slots import read_member_spans
    # Literal upstream WriteVarInt(int) vectors independent of fixture encoder.
    prefix=bytes.fromhex(expected)
    assert member_length(size)==prefix
    payload=b"x"*size
    assert bytes(read_member_spans(b"\x01"+prefix+payload,minimum_count=1)[0])==payload


def test_original_invalid_fixture_rejected():
    s=root()
    assert len(s[12])==138
    old=bytes([len(s)])+bytes(map(len,s))+b"".join(s)
    with pytest.raises(SnapshotFormatError,match="negative member length"):
        parse_arena_snapshot(envelope(old))


@pytest.mark.parametrize("size",[128,256,32768])
def test_large_nested_opponent(size):
    from invokers_bot.arena_opponent import parse_opponent
    opaque=b"z"*size
    # Explicit nested wire vector using known semantic slots and independent literal scalars.
    team=obj([bytes.fromhex("07180000"),bytes(range(1,17)),opaque])
    entry=obj([bytes.fromhex("010000004100"),bytes.fromhex("07000000"),b"",bytes.fromhex("16020000"),team])
    decoded=parse_opponent(entry)
    assert (decoded.name,decoded.level,decoded.arena_points,decoded.combat_power)==("A",7,534,6151)
    assert decoded.team_setup.player_id==bytes(range(1,17))
    assert decoded.team_setup.opaque_slots[2]==opaque
    s=root();s[12]=pack("<i",1)+entry
    parsed=parse_arena_snapshot(envelope(obj(s)))
    assert parsed.current_opponents==(decoded,)


def test_literal_opponent_wire():
    from invokers_bot.arena_opponent import parse_opponent
    # Hand-authored object header: five member lengths 6,4,0,4,23.
    # Team header: two members, lengths 4 and 16.
    raw=bytes.fromhex("050604000417 010000004100 07000000 16020000 020410 07180000 0102030405060708090a0b0c0d0e0f10")
    o=parse_opponent(raw)
    assert (o.name,o.level,o.arena_points,o.combat_power)==("A",7,534,6151)
    assert o.identity=="0102030405060708090a0b0c0d0e0f10"
