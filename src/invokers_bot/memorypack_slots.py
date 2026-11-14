"""Bounded read-only MemoryPack VersionTolerant member spans."""
from .snapshot_envelope import SnapshotFormatError, read_varint_int32


def read_member_spans(data: bytes, *, minimum_count: int,
                      exact_count: int | None = None) -> tuple[memoryview, ...]:
    """Read all lengths before slicing any members; reject trailing data."""
    data = bytes(data)
    if not data:
        raise SnapshotFormatError("missing object member count")
    count = data[0]
    # MemoryPack object headers reserve 250..255.
    if count >= 250 or count < minimum_count or (
        exact_count is not None and count != exact_count
    ):
        raise SnapshotFormatError(f"invalid object member count: {count}")
    offset = 1
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
    if offset != len(data):
        raise SnapshotFormatError("unexpected trailing bytes in object")
    return tuple(members)
