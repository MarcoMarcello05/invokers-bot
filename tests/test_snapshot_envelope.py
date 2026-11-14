from datetime import datetime, timezone
from struct import pack

import pytest

from invokers_bot.snapshot_envelope import (
    SnapshotFormatError, parse_snapshot, read_snapshot, read_varint_int32,
)

TICKS = 621355968000000000 + 1234567
STAMP = pack("<Q", TICKS | (1 << 62))
HEADER = b"\x01\x03\x08\x08"
FIXED = pack("<q", 3600) + STAMP


def packet(tag=1, payload=b"abc"):
    n = len(payload)
    length = bytes([n]) if n <= 127 else (
        b"\x84" + pack("<h", n) if n <= 32767 else b"\x82" + pack("<i", n)
    )
    return bytes([tag, 3, 8, 8]) + length + FIXED + payload


@pytest.mark.parametrize("tag,name", enumerate((
    "PlayerModel", "PlayerHeroesModel", "PlayerAnimasModel",
    "PlayerRelicsModel", "PlayerAccessoriesModel", "PlayerShopModel",
    "PlayerBattleModel", "PlayerQuestsModel", "PlayerArenaModel",
    "PlayerGlobalEventsModel", "PlayerInboxModel", "PlayerClanModel",
), 1))
def test_tags(tag, name):
    blob = packet(tag)
    result = parse_snapshot(blob)
    assert (result.union_tag, result.model_name, result.version) == (tag, name, 3600)
    assert result.data == b"abc"
    assert result.total_size == len(blob)
    assert result.payload_size == 3
    assert result.updated_at_utc == datetime(1970, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)
    assert result.updated_at_ticks == TICKS


@pytest.mark.parametrize("size", [0, 1, 127, 128, 738, 32767, 32768, 204292])
def test_lengths(size):
    payload = b"x" * size
    assert parse_snapshot(packet(payload=payload)).data == payload


@pytest.mark.parametrize("blob,message", [
    (b"", "union tag"),
    (b"\x0d", "unsupported union"),
    (b"\xff", "unsupported union"),
    (b"\x01", "object header"),
    (b"\x01\x02", "3 members"),
    (b"\x01\x03\x07\x08\x00" + FIXED, "8 bytes"),
    (HEADER + b"\xff" + FIXED, "negative"),
    (HEADER + b"\x84", "truncated VarInt"),
    (HEADER + b"\x03" + FIXED[:7], "truncated Version"),
    (HEADER + b"\x03" + FIXED[:15], "truncated UpdatedAtUtc"),
    (packet()[:-1], "truncated Data"),
    (packet() + b"x", "trailing bytes"),
    (HEADER + b"\x00" + pack("<qQ", 1, 1 << 63), "local DateTime"),
    (HEADER + b"\x00" + pack("<qQ", 1, 3155378976000000000), "ticks out of range"),
])
def test_invalid(blob, message):
    with pytest.raises(SnapshotFormatError, match=message):
        parse_snapshot(blob)


@pytest.mark.parametrize("encoded,value", [
    (b"\x7f", 127), (b"\x88", -120),
    (b"\x87\xff", 255), (b"\x86\x80", -128),
    (b"\x85" + pack("<H", 65535), 65535),
    (b"\x84" + pack("<h", -32768), -32768),
    (b"\x83" + pack("<I", 2147483647), 2147483647),
    (b"\x82" + pack("<i", -2147483648), -2147483648),
    (b"\x81" + pack("<Q", 12345), 12345),
    (b"\x80" + pack("<q", -12345), -12345),
])
def test_varint(encoded, value):
    assert read_varint_int32(b"x" + encoded, 1) == (value, len(encoded) + 1)
    if len(encoded) > 1:
        with pytest.raises(SnapshotFormatError):
            read_varint_int32(encoded[:-1])


def test_varint_overflow():
    with pytest.raises(SnapshotFormatError, match="Int32"):
        read_varint_int32(b"\x81" + pack("<Q", 1 << 31))


def test_read_only(tmp_path):
    path = tmp_path / "synthetic.dat"
    blob = packet()
    path.write_bytes(blob)
    assert read_snapshot(path).data == b"abc"
    assert path.read_bytes() == blob


def test_unspecified_datetime():
    blob = HEADER + b"\x00" + pack("<qQ", -1, 0)
    result = parse_snapshot(blob)
    assert result.version == -1
    assert result.updated_at_utc == datetime(1, 1, 1, tzinfo=timezone.utc)
