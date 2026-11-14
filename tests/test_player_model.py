"""Synthetic fixtures only; no account data."""
from datetime import datetime, timezone
from struct import pack

import pytest

from invokers_bot.memorypack_slots import read_member_spans
from invokers_bot.player_model import (
    parse_player_snapshot, parse_resources, read_player_snapshot,
)
from invokers_bot.resource_types import ResourceTypeId, resource_name
from invokers_bot.snapshot_envelope import SnapshotFormatError

TICKS = 621355968000000000
STAMP = pack("<Q", TICKS | (1 << 62))


def varint(n):
    if n <= 127:
        return pack("<b", n)
    if n <= 32767:
        return b"\x84" + pack("<h", n)
    return b"\x82" + pack("<i", n)


def obj(members):
    return bytes([len(members)]) + b"".join(varint(len(m)) for m in members) + b"".join(members)


def dictionary(pairs):
    return obj([pack("<i", len(pairs)) + b"".join(pack("<ii", *p) for p in pairs)])


def slots():
    result = [b""] * 53
    for slot, value in [(4, 17), (5, 234), (6, 3456), (33, 42), (43, 19)]:
        result[slot] = pack("<i", value)
    result[8] = STAMP
    result[34] = pack("<Q", TICKS + 19)
    result[51] = pack("<q", 2**40)
    result[52] = pack("<q", 2**40 - 1)
    result[9] = dictionary([(2, 100), (3, 11), (99999, 4)])
    result[10] = dictionary([(2, 150)])
    result[11] = dictionary([(2, 50)])
    result[19] = b"opaque" * 50
    return result


def envelope(payload, tag=1):
    return bytes([tag, 3, 8, 8]) + varint(len(payload)) + pack("<q", 7) + STAMP + payload


def test_scalars_and_resources():
    state = parse_player_snapshot(envelope(obj(slots())))
    assert (state.level, state.experience, state.total_experience) == (17, 234, 3456)
    assert (state.today_total_played_minutes, state.days_played) == (42, 19)
    assert (state.support_revision, state.support_last_read_revision) == (2**40, 2**40 - 1)
    assert state.energy_sync_time == datetime(1970, 1, 1, tzinfo=timezone.utc)
    assert state.arena_token_sync_time.microsecond == 1
    assert state.arena_token_sync_ticks == TICKS + 19
    assert state.energy_sync_ticks == TICKS
    assert state.version == 7
    assert state.resources == {2: 100, 3: 11, 99999: 4}
    assert state.resources_gained[2] - state.resources_spent[2] == state.resources[2]
    assert state.resources_gained == {2: 150}
    assert state.resources_spent == {2: 50}
    with pytest.raises(TypeError):
        state.resources[2] = 0


@pytest.mark.parametrize("reserved", [7, 12, 13, 14])
def test_reserved_slots(reserved):
    members = slots()
    assert len(read_member_spans(obj(members), minimum_count=53)[reserved]) == 0
    members[reserved] = b"historical opaque bytes"
    assert parse_player_snapshot(envelope(obj(members))).level == 17


def test_empty_resources_and_future_slot():
    members = slots() + [b"future"]
    members[9] = dictionary([])
    assert parse_player_snapshot(envelope(obj(members))).resources == {}


def test_mapping():
    assert len(ResourceTypeId) == 181
    assert resource_name(1) == "Gem"
    assert resource_name(21) == "Arena_Token"
    assert resource_name(1002) == "VIP_30d"
    assert resource_name(99999) is None


@pytest.mark.parametrize("count", [0, 1, 52, 250, 255])
def test_bad_player_count(count):
    with pytest.raises(SnapshotFormatError, match="member count"):
        parse_player_snapshot(envelope(bytes([count])))


@pytest.mark.parametrize("payload,match", [
    (b"\x35\x84", "truncated VarInt"),
    (b"\x35\xff" + bytes(52), "negative member length"),
    (b"\x35\x01" + bytes(52), "out of bounds"),
    (b"\x35" + bytes(53) + b"x", "trailing bytes"),
])
def test_bad_slot_table(payload, match):
    with pytest.raises(SnapshotFormatError, match=match):
        parse_player_snapshot(envelope(payload))


@pytest.mark.parametrize("payload,match", [
    (b"\x02", "member count"),
    (obj([b"\x00"]), "truncated dictionary count"),
    (obj([pack("<i", -1)]), "negative dictionary count"),
    (obj([pack("<i", 2) + pack("<ii", 1, 2)]), "exceeds available"),
    (dictionary([(2, 1), (2, 3)]), "duplicate ResourceTypeId"),
    (obj([pack("<i", 0) + b"x"]), "trailing bytes"),
    (dictionary([]) + b"x", "trailing bytes"),
])
def test_bad_resources(payload, match):
    with pytest.raises(SnapshotFormatError, match=match):
        parse_resources(payload)


@pytest.mark.parametrize("slot", [4, 5, 6, 8, 33, 34, 43, 51, 52])
def test_wrong_scalar_width(slot):
    members = slots()
    members[slot] = b""
    with pytest.raises(SnapshotFormatError, match=f"slot {slot}"):
        parse_player_snapshot(envelope(obj(members)))


@pytest.mark.parametrize("slot", [9, 10, 11])
def test_resource_slot_validation(slot):
    members = slots()
    members[slot] = b"\xff"
    with pytest.raises(SnapshotFormatError, match=f"slot {slot}"):
        parse_player_snapshot(envelope(obj(members)))


def test_large_dictionary():
    pairs = [(i, i * 2) for i in range(100)]
    assert parse_resources(dictionary(pairs)) == dict(pairs)


def test_wrong_union():
    with pytest.raises(SnapshotFormatError, match="expected PlayerModel"):
        parse_player_snapshot(envelope(obj(slots()), tag=2))


def test_file_read_only(tmp_path):
    path = tmp_path / "synthetic.dat"
    blob = envelope(obj(slots()))
    path.write_bytes(blob)
    assert read_player_snapshot(path).level == 17
    assert path.read_bytes() == blob
