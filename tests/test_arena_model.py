from struct import pack
import pytest
from invokers_bot.arena_model import parse_arena_snapshot
from invokers_bot.account_state import AccountObserver
from invokers_bot.snapshot_envelope import SnapshotFormatError

STAMP=pack("<Q",621355968000000000 | (1<<62))

def obj(slots):
    return bytes([len(slots)])+bytes(map(len,slots))+b"".join(slots)

def root():
    s=[b""]*18
    s[0]=pack("<i",42)
    s[5]=s[7]=STAMP
    s[8]=pack("<i",12)
    s[9]=s[16]=bytes(4)
    s[10]=obj([b""]*18)
    s[12]=pack("<i",2)+obj([b"abc"])+obj([b"def"])
    s[14]=s[17]=b"\xff"
    s[15]=pack("<i",1)+obj([b"finished"])
    return s

def envelope(payload):
    size=len(payload)
    vi=bytes([size]) if size<128 else b"\x84"+pack("<h",size)
    return b"\x09\x03\x08\x08"+vi+pack("<q",3)+STAMP+payload

def test_arena():
    s=root()
    state=parse_arena_snapshot(envelope(obj(s)))
    assert (state.points,state.last_weekly_points,state.version)==(42,12,3)
    assert state.opponents.count==2 and state.opponents.entries==(obj([b"abc"]),obj([b"def"]))
    assert state.finished_opponents.count==1 and state.current_battle_opponent_raw is None
    assert state.hall_bonuses.count==state.shop_state_by_period.count==0
    s[12]=pack("<i",2)+obj([b"def"])+obj([b"abc"])
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
