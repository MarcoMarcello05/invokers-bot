"""Bounded read-only MemoryPack VersionTolerant member spans."""
from .snapshot_envelope import SnapshotFormatError, read_varint_int32


def read_member_spans(data: bytes, *, minimum_count: int,
                      exact_count: int | None = None) -> tuple[memoryview, ...]:
    """Read all lengths before slicing any members; reject trailing data."""
    members, end = read_member_spans_at(bytes(data), 0, minimum_count=minimum_count,
                                        exact_count=exact_count)
    if end != len(data):
        raise SnapshotFormatError("unexpected trailing bytes in object")
    return members


def read_member_spans_at(data: bytes | memoryview, offset: int, *, minimum_count: int,
                         exact_count: int | None = None) -> tuple[tuple[memoryview, ...], int]:
    """Read one bounded object in a collection and return its next offset."""
    data = memoryview(data).toreadonly()
    if not 0 <= offset < len(data):
        raise SnapshotFormatError("missing object member count")
    count = data[offset]
    # MemoryPack object headers reserve 250..255.
    if count >= 250 or count < minimum_count or (
        exact_count is not None and count != exact_count
    ):
        raise SnapshotFormatError(f"invalid object member count: {count}")
    offset += 1
    lengths = []
    for _ in range(count):
        length, offset = read_varint_int32(data, offset)
        if length < 0:
            raise SnapshotFormatError("negative member length")
        lengths.append(length)
    view = memoryview(data)
    members = []
    for slot, length in enumerate(lengths):
        end = offset + length
        if end > len(data):
            raise SnapshotFormatError(f"slot {slot} out of bounds")
        members.append(view[offset:end])
        offset = end
    return tuple(members), offset
