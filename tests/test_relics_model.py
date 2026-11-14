"""Synthetic relic fixtures, with no game/account data."""
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from struct import pack

import pytest

from invokers_bot.relics_model import parse_relic, parse_relics_snapshot, read_relics_snapshot
from invokers_bot.snapshot_envelope import SnapshotFormatError

STAMP = pack("<Q", 621355968000000000 | (1 << 62))


def vi(n):
    if n < 128:
        return bytes([n])
    if n <= 32767:
        return b"\x84" + pack("<h", n)
    return b"\x82" + pack("<i", n)


def obj(slots):
    return bytes([len(slots)]) + b"".join(vi(len(s)) for s in slots) + b"".join(slots)


def relic_slots(key=1, equipped=None, seen=False, bonuses=bytes(4)):
    nullable = bytes(8) if equipped is None else b"\x01" + bytes(3) + pack("<i", equipped)
    return [pack("<i", v) for v in (key, 99, 5, 88, 77)] + [
        nullable, pack("<i", 20), bytes([seen]), bonuses,
    ]


def root(entries):
    return [pack("<i", 200), pack("<i", len(entries)) +
            b"".join(pack("<i", k) + v for k, v in entries), b"randoms-opaque"]


def envelope(payload, tag=4):
    return bytes([tag, 3, 8, 8]) + vi(len(payload)) + pack("<q", 7) + STAMP + payload


@pytest.mark.parametrize("n", [0, 1, 4, 180])
def test_inventory(n):
    data = envelope(obj(root([(i, obj(relic_slots(i))) for i in range(1, n + 1)])))
    state = parse_relics_snapshot(data)
    assert len(state.relics_by_id) == n
    assert state.last_id == 200
    assert state.version == 7
    assert state.updated_at_utc == datetime(1970, 1, 1, tzinfo=timezone.utc)
    assert state.randoms_raw == b"randoms-opaque"
    with pytest.raises(TypeError):
        state.relics_by_id[0] = None
    if n:
        relic = state.relics_by_id[n]
        assert (relic.inventory_id, relic.slot, relic.rank, relic.rarity, relic.set, relic.level) == (n, 99, 5, 88, 77, 20)
        assert relic.equipped_hero_id is None
        assert relic.is_seen is False
        assert relic.bonuses_raw == bytes(4)
        with pytest.raises(FrozenInstanceError):
            relic.level = 1


@pytest.mark.parametrize("equipped", [None, 1234])
@pytest.mark.parametrize("seen", [False, True])
def test_nullable_and_seen(equipped, seen):
    state = parse_relic(obj(relic_slots(equipped=equipped, seen=seen)))
    assert state.equipped_hero_id == equipped
    assert state.is_seen is seen


@pytest.mark.parametrize("bonuses", [bytes(4), b"\x02\x00\x00\x00\xff\x81\x00" * 100, b""])
def test_opaque_bonuses(bonuses):
    assert parse_relic(obj(relic_slots(bonuses=bonuses))).bonuses_raw == bonuses


def test_nullable_padding_ignored():
    slots = relic_slots()
    slots[5] = b"\x00\xff\xff\xff" + pack("<i", 99)
    assert parse_relic(obj(slots)).equipped_hero_id is None
    slots[5] = b"\x01\xff\xff\xff" + pack("<i", 99)
    assert parse_relic(obj(slots)).equipped_hero_id == 99


@pytest.mark.parametrize("value", [b"", b"\x02", b"\x01\x00"])
def test_invalid_bool(value):
    slots = relic_slots()
    slots[7] = value
    with pytest.raises(SnapshotFormatError, match="bool"):
        parse_relic(obj(slots))


@pytest.mark.parametrize("value", [b"", bytes(4), bytes(9), b"\x02" + bytes(7)])
def test_invalid_nullable(value):
    slots = relic_slots()
    slots[5] = value
    with pytest.raises(SnapshotFormatError, match="nullable"):
        parse_relic(obj(slots))


@pytest.mark.parametrize("slot", [0, 1, 2, 3, 4, 6])
def test_scalar_width(slot):
    slots = relic_slots()
    slots[slot] = bytes(3)
    with pytest.raises(SnapshotFormatError, match="scalar width"):
        parse_relic(obj(slots))


@pytest.mark.parametrize("entries,match", [
    ([(2,obj(relic_slots(1)))], "disagrees"),
    ([(1,obj(relic_slots())),(1,obj(relic_slots()))], "duplicate"),
])
def test_identity(entries, match):
    with pytest.raises(SnapshotFormatError, match=match):
        parse_relics_snapshot(envelope(obj(root(entries))))


@pytest.mark.parametrize("payload", [b"\x02", b"\x03\x84", b"\x03\xff"+bytes(2), b"\x03\x01"+bytes(2)])
def test_bad_root(payload):
    with pytest.raises(SnapshotFormatError):
        parse_relics_snapshot(envelope(payload))


@pytest.mark.parametrize("payload", [b"\x08", b"\x09\x84", b"\x09\xff"+bytes(8), b"\x09\x01"+bytes(8)])
def test_bad_relic(payload):
    with pytest.raises(SnapshotFormatError):
        parse_relic(payload)


@pytest.mark.parametrize("member", [b"", pack("<i",-1), pack("<i",100), pack("<i",0)+b"x",
                                   pack("<i",1)+pack("<i",1)+b"\x09"+bytes(9)])
def test_malformed_dictionary(member):
    slots = root([])
    slots[1] = member
    with pytest.raises(SnapshotFormatError):
        parse_relics_snapshot(envelope(obj(slots)))


def test_trailing():
    with pytest.raises(SnapshotFormatError, match="trailing"):
        parse_relic(obj(relic_slots())+b"x")
    with pytest.raises(SnapshotFormatError, match="trailing"):
        parse_relics_snapshot(envelope(obj(root([]))+b"x"))


def test_additive_slots():
    state = parse_relics_snapshot(envelope(obj(root([(1,obj(relic_slots()+[b"future relic"]))])+[b"future root"])))
    assert state.relics_by_id[1].level == 20


def test_wrong_tag():
    with pytest.raises(SnapshotFormatError, match="expected PlayerRelicsModel"):
        parse_relics_snapshot(envelope(obj(root([])), tag=2))


def test_read_only(tmp_path):
    path = tmp_path / "synthetic.dat"
    blob = envelope(obj(root([(1,obj(relic_slots()))])))
    path.write_bytes(blob)
    assert read_relics_snapshot(path).relics_by_id[1].level == 20
    assert path.read_bytes() == blob


def test_hero_reference_join():
    # Cross-model join uses inventory IDs, not parser coupling.
    state = parse_relics_snapshot(envelope(obj(root([(42,obj(relic_slots(42,equipped=9)))]))))
    hero_relic_id_by_slot = {99: 42}
    relic = state.relics_by_id[hero_relic_id_by_slot[99]]
    assert relic.slot == 99 and relic.equipped_hero_id == 9
