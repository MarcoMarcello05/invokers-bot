"""Read-only snapshot envelope for Windows build 0.62.1621."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from struct import unpack_from

_NAMES = (
    "PlayerModel", "PlayerHeroesModel", "PlayerAnimasModel",
    "PlayerRelicsModel", "PlayerAccessoriesModel", "PlayerShopModel",
    "PlayerBattleModel", "PlayerQuestsModel", "PlayerArenaModel",
    "PlayerGlobalEventsModel", "PlayerInboxModel", "PlayerClanModel",
)
# MemoryPack signed type markers, not LEB128.
# https://github.com/Cysharp/MemoryPack/blob/main/src/MemoryPack.Core/MemoryPackReaderWriter.VarInt.cs
_CODES = {-121: "B", -122: "b", -123: "H", -124: "h",
          -125: "I", -126: "i", -127: "Q", -128: "q"}
_WIDTHS = {"B": 1, "b": 1, "H": 2, "h": 2, "I": 4, "i": 4, "Q": 8, "q": 8}


class SnapshotFormatError(ValueError):
    """Malformed or unsupported snapshot envelope."""


@dataclass(frozen=True, slots=True)
class AggregateSnapshot:
    union_tag: int
    model_name: str
    version: int
    updated_at_utc: datetime
    data: bytes
    total_size: int
    payload_size: int
    updated_at_ticks: int


def read_varint_int32(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Return a checked MemoryPack Int32 and the next byte offset."""
    if not 0 <= offset < len(data):
        raise SnapshotFormatError("truncated VarInt marker")
    marker = unpack_from("<b", data, offset)[0]
    offset += 1
    code = _CODES.get(marker)
    if code is None:
        return marker, offset
    width = _WIDTHS[code]
    if len(data) - offset < width:
        raise SnapshotFormatError("truncated VarInt value")
    value = unpack_from("<" + code, data, offset)[0]
    if not -(1 << 31) <= value < (1 << 31):
        raise SnapshotFormatError("VarInt exceeds Int32 range")
    return value, offset + width


def _datetime_utc(raw: int) -> tuple[datetime, int]:
    # Native .NET DateTime: lower 62 bits are ticks, upper two are kind.
    # Unspecified is permitted by the UTC field contract; local is ambiguous.
    kind = raw >> 62
    ticks = raw & ((1 << 62) - 1)
    if kind not in (0, 1):
        raise SnapshotFormatError("UpdatedAtUtc has local DateTime kind")
    if ticks > 3155378975999999999:
        raise SnapshotFormatError("UpdatedAtUtc ticks out of range")
    # Python datetime has microsecond precision; preserve exact ticks separately.
    return datetime(1, 1, 1, tzinfo=timezone.utc) + timedelta(
        microseconds=ticks // 10
    ), ticks


def parse_snapshot(data: bytes) -> AggregateSnapshot:
    """Decode only the verified envelope; payload remains opaque and immutable."""
    data = bytes(data)
    if not data:
        raise SnapshotFormatError("missing union tag")
    tag = data[0]
    if not 1 <= tag <= len(_NAMES):
        raise SnapshotFormatError(f"unsupported union tag: {tag}")
    if len(data) < 2:
        raise SnapshotFormatError("missing object header")
    if data[1] != 3:
        raise SnapshotFormatError(f"expected 3 members, got {data[1]}")
    offset = 2
    lengths = []
    for _ in range(3):
        value, offset = read_varint_int32(data, offset)
        if value < 0:
            raise SnapshotFormatError("negative member length")
        lengths.append(value)
    if lengths[:2] != [8, 8]:
        raise SnapshotFormatError("Version and UpdatedAtUtc must each be 8 bytes")
    if len(data) - offset < 8:
        raise SnapshotFormatError("truncated Version")
    version = unpack_from("<q", data, offset)[0]
    offset += 8
    if len(data) - offset < 8:
        raise SnapshotFormatError("truncated UpdatedAtUtc")
    timestamp, ticks = _datetime_utc(unpack_from("<Q", data, offset)[0])
    offset += 8
    remaining = len(data) - offset
    if lengths[2] > remaining:
        raise SnapshotFormatError("truncated Data payload")
    if lengths[2] < remaining:
        raise SnapshotFormatError("unexpected trailing bytes")
    return AggregateSnapshot(tag, _NAMES[tag - 1], version, timestamp,
                             data[offset:], len(data), remaining, ticks)


def read_snapshot(path: str | Path) -> AggregateSnapshot:
    """Open a snapshot in binary read mode only."""
    return parse_snapshot(Path(path).read_bytes())
