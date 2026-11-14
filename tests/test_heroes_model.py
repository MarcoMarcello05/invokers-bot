from struct import pack
from datetime import datetime, timezone

import pytest

from invokers_bot.heroes_model import parse_hero, parse_heroes_snapshot, read_heroes_snapshot
from invokers_bot.snapshot_envelope import SnapshotFormatError

STAMP = pack("<Q", 621355968000000000 | (1 << 62))


def vi(n):
    return bytes([n]) if n < 128 else b"\x84" + pack("<h", n)


def obj(slots):
    return bytes([len(slots)]) + b"".join(vi(len(s)) for s in slots) + b"".join(slots)


def collection(fmt, entries):
    return pack("<i", len(entries)) + b"".join(pack(fmt, *e) for e in entries)


def hero_slots(key=1):
    s = [b""] * 22
    for i, v in [(0,key),(2,5),(3,24),(4,7),(5,100),(8,999),(16,2),(18,777)]:
        s[i] = pack("<i", v)
    s[1] = pack("<q", 2**40)
    s[6], s[7], s[17] = b"\x01", b"\x00", b"\x01"
    s[9] = bytes(16)
    for i in (11,12,15,21):
        s[i] = bytes(4)
    return s


def root(entries):
    return [pack("<i", 10), pack("<i", len(entries)) +
            b"".join(pack("<i", k)+v for k,v in entries),
            collection("<i", [(1,)]), collection("<q", [(2**40,)]),
            collection("<qi", [(2**40, 3)]), pack("<q", 2**40),
            bytes(4), bytes(4), b"opaque", bytes(4)]


def envelope(payload, tag=2):
    return bytes([tag,3,8,8])+vi(len(payload))+pack("<q", 1)+STAMP+payload


@pytest.mark.parametrize("n", [0,1,3])
def test_roster(n):
    state = parse_heroes_snapshot(envelope(obj(root([(i,obj(hero_slots(i))) for i in range(1,n+1)]))))
    assert len(state.heroes_by_id) == n
    assert state.last_id == 10
    assert state.lobby_hero_ids == (1,)
    assert state.seen_hero_config_ids == (2**40,)
    assert state.starter_hero_id == 2**40
    assert state.received_heroes_count == {2**40:3}
    assert state.opaque_slots[8] == b"opaque"
    with pytest.raises(TypeError):
        state.heroes_by_id[9] = None
    if n:
        h = state.heroes_by_id[1]
        assert (h.inventory_id,h.config_id,h.rank,h.level,h.experience,h.total_experience) == (1,2**40,5,24,7,100)
        assert h.locked and not h.in_storage and h.chroma_enabled
        assert (h.marker,h.awake_level,h.skin) == (999,2,777)
        assert h.recent_battle_time is None
        assert h.relic_id_by_slot == h.accessory_id_by_slot == {}


@pytest.mark.parametrize("n", [6,7])
def test_equipment_skills_and_time(n):
    s = hero_slots()
    s[9] = b"\x01"+bytes(7)+STAMP
    s[11] = collection("<ii", [(i,100+i) for i in range(1,9)])
    s[12] = collection("<ii", [(99,77)])
    s[15] = collection("<i", [(3,),(5,)])
    s[21] = collection("<ii", [(i,2) for i in range(n)])
    h = parse_hero(obj(s))
    assert h.recent_battle_time == datetime(1970,1,1,tzinfo=timezone.utc)
    assert h.recent_battle_ticks == 621355968000000000
    assert h.relic_id_by_slot == {i:100+i for i in range(1,9)}
    assert h.accessory_id_by_slot == {99:77}
    assert h.awake_node_ids == (3,5)
    assert [(x.kind,x.level) for x in h.skill_levels] == [(i,2) for i in range(n)]


@pytest.mark.parametrize("slot", [10,13,14,19,20,22])
def test_opaque(slot):
    s = hero_slots()+[b""]
    s[slot] = b"opaque"
    assert parse_hero(obj(s)).level == 24


@pytest.mark.parametrize("slot", [6,7,17])
def test_bad_bool(slot):
    s = hero_slots()
    s[slot] = b"\x02"
    with pytest.raises(SnapshotFormatError, match="bool"):
        parse_hero(obj(s))


@pytest.mark.parametrize("slot", [0,1,2,3,4,5,8,16,18])
def test_scalar_width(slot):
    s = hero_slots()
    s[slot] = b""
    with pytest.raises(SnapshotFormatError, match="width"):
        parse_hero(obj(s))


@pytest.mark.parametrize("slot,value", [
    (9,b"\x02"+bytes(15)),(9,bytes(8)),(11,pack("<i",2)),
    (12,collection("<ii",[(1,2),(1,3)])),(15,pack("<i",-1)),
    (21,pack("<i",1)+bytes(4)),(21,bytes(5)),
])
def test_invalid_member(slot,value):
    s = hero_slots()
    s[slot] = value
    with pytest.raises(SnapshotFormatError):
        parse_hero(obj(s))


@pytest.mark.parametrize("data", [b"\x15",b"\x16\x84",b"\x16\x01"+bytes(21)])
def test_malformed_hero(data):
    with pytest.raises(SnapshotFormatError):
        parse_hero(data)


@pytest.mark.parametrize("entries", [[(2,obj(hero_slots(1)))],[(1,obj(hero_slots())),(1,obj(hero_slots()))]])
def test_identity(entries):
    with pytest.raises(SnapshotFormatError):
        parse_heroes_snapshot(envelope(obj(root(entries))))


@pytest.mark.parametrize("payload", [b"\x09",b"\x0a\x84",b"\x0a\x01"+bytes(9)])
def test_malformed_root(payload):
    with pytest.raises(SnapshotFormatError):
        parse_heroes_snapshot(envelope(payload))


def test_trailing_and_wrong_tag():
    with pytest.raises(SnapshotFormatError):
        parse_hero(obj(hero_slots())+b"x")
    s = root([])
    s[1] += b"x"
    with pytest.raises(SnapshotFormatError):
        parse_heroes_snapshot(envelope(obj(s)))
    with pytest.raises(SnapshotFormatError):
        parse_heroes_snapshot(envelope(obj(root([])),tag=1))


def test_read_only(tmp_path):
    p = tmp_path/"synthetic.dat"
    blob = envelope(obj(root([])))
    p.write_bytes(blob)
    assert read_heroes_snapshot(p).last_id == 10
    assert p.read_bytes() == blob
