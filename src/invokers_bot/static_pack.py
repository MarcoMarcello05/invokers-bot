"""Read-only HZCP format 4 container index, not a StaticData object decoder.

The profile is supported by ChunkPackHeader/PackChunkKey/PackChunk IL2CPP
declarations and the archived 0.62.1655 artifact. ChunkHashes are preserved
as UInt64 metadata: their hash algorithm has not been established.
"""
from dataclasses import dataclass
from hashlib import sha256
from struct import unpack_from
from types import MappingProxyType
from typing import Mapping
import re

import brotli


class StaticPackError(ValueError):
    """Invalid, incompatible or unsupported pack; never a partial index."""


MAX_HEADER_RAW = 4 * 1024 * 1024
MAX_CHUNK_RAW = 64 * 1024 * 1024
MAX_CHUNKS = 100_000


@dataclass(frozen=True, slots=True, order=True)
class ChunkKey:
    category: int
    id: int


MAIN_KEY = ChunkKey(0, 0)


@dataclass(frozen=True, slots=True)
class PackChunk:
    key: ChunkKey
    offset: int
    size: int
    uncompressed_size: int
    is_compressed: bool
    declared_hash: int


@dataclass(frozen=True, slots=True)
class StaticPackIndex:
    format_version: int
    static_revision: str
    secondary_revision: str
    artifact_size: int
    artifact_sha256: str
    header_size: int
    header_raw_size: int
    data_start: int
    chunks: Mapping[ChunkKey, PackChunk]


def _version_string(blob, offset):
    if offset >= len(blob):
        raise StaticPackError("truncated revision string")
    length = blob[offset]
    offset += 1
    if not 1 <= length <= 80 or offset + length > len(blob):
        raise StaticPackError("invalid revision length")
    data = blob[offset:offset+length]
    if not re.fullmatch(rb"[0-9A-Za-z._-]+", data):
        raise StaticPackError("unsupported revision encoding")
    return data.decode("ascii"), offset + length


def _decompress(data, expected, limit):
    if not 0 <= expected <= limit:
        raise StaticPackError("unsupported uncompressed size")
    decoder = brotli.Decompressor()
    result = bytearray()
    try:
        for offset in range(0, len(data), 4096):
            part = decoder.process(data[offset:offset+4096])
            if len(result) + len(part) > expected:
                raise StaticPackError("decompressed size exceeds declaration")
            result.extend(part)
        if not decoder.is_finished() or len(result) != expected:
            raise StaticPackError("incomplete stream or size mismatch")
    except brotli.error as exc:
        raise StaticPackError("invalid Brotli stream") from exc
    return bytes(result)


def parse_static_pack(blob: bytes, *, expected_revision=None,
                      expected_secondary_revision=None) -> StaticPackIndex:
    """Validate every header vector and chunk extent. No quest table inference."""
    if not isinstance(blob, bytes) or len(blob) < 8 or blob[:4] != b"HZCP":
        raise StaticPackError("not a supported HZCP pack")
    fmt = unpack_from("<I", blob, 4)[0]
    if fmt != 4:
        raise StaticPackError("unsupported HZCP format")
    revision, pos = _version_string(blob, 8)
    secondary, pos = _version_string(blob, pos)
    if expected_revision is not None and revision != expected_revision:
        raise StaticPackError("static revision mismatch")
    if expected_secondary_revision is not None and secondary != expected_secondary_revision:
        raise StaticPackError("secondary revision mismatch")
    if len(blob) - pos < 8:
        raise StaticPackError("truncated header lengths")
    packed_size, raw_size = unpack_from("<II", blob, pos)
    pos += 8
    if not 0 < packed_size <= len(blob) - pos or not 13 <= raw_size <= MAX_HEADER_RAW:
        raise StaticPackError("invalid header lengths")
    header = _decompress(blob[pos:pos+packed_size], raw_size, MAX_HEADER_RAW)
    data_start = pos + packed_size
    if header[0] != 3:
        raise StaticPackError("unsupported ChunkPackHeader member count")
    count = unpack_from("<i", header, 1)[0]
    if not 1 <= count <= MAX_CHUNKS or len(header) != 13 + 40 * count:
        raise StaticPackError("invalid header vector length")
    keys_start = 5
    chunk_count_at = keys_start + 16 * count
    chunks_start = chunk_count_at + 4
    hash_count_at = chunks_start + 16 * count
    hashes_start = hash_count_at + 4
    if (unpack_from("<i",header,chunk_count_at)[0] != count
            or unpack_from("<i",header,hash_count_at)[0] != count):
        raise StaticPackError("header vector counts disagree")
    chunks = {}
    for i in range(count):
        key_id, category = unpack_from("<qB", header, keys_start + 16*i)
        key = ChunkKey(category,key_id)
        offset, size, unpacked, compressed = unpack_from("<iiiB",header,chunks_start+16*i)
        declared_hash = unpack_from("<Q",header,hashes_start+8*i)[0]
        if key in chunks:
            raise StaticPackError("duplicate chunk key")
        if min(offset,size,unpacked)<0 or compressed not in (0,1):
            raise StaticPackError("invalid chunk descriptor")
        if offset+size > len(blob)-data_start:
            raise StaticPackError("chunk extent outside pack")
        if not compressed and size != unpacked:
            raise StaticPackError("uncompressed chunk length mismatch")
        chunks[key] = PackChunk(key,offset,size,unpacked,bool(compressed),declared_hash)
    if MAIN_KEY not in chunks:
        raise StaticPackError("missing Main chunk")
    return StaticPackIndex(fmt,revision,secondary,len(blob),sha256(blob).hexdigest(),
                           packed_size,raw_size,data_start,MappingProxyType(chunks))


def extract_chunk(blob: bytes, index: StaticPackIndex, key: ChunkKey = MAIN_KEY) -> bytes:
    """Return bounded chunk bytes in memory only; verify index/source identity."""
    if (not isinstance(blob,bytes) or len(blob)!=index.artifact_size
            or sha256(blob).hexdigest()!=index.artifact_sha256):
        raise StaticPackError("artifact does not match index")
    item=index.chunks.get(key)
    if item is None:
        raise StaticPackError("unknown chunk key")
    start=index.data_start+item.offset
    end=start+item.size
    if not 0<=start<=end<=len(blob) or not 0<=item.uncompressed_size<=MAX_CHUNK_RAW:
        raise StaticPackError("unsupported chunk extent or decompression size")
    raw=blob[start:end]
    if item.is_compressed:
        return _decompress(raw,item.uncompressed_size,MAX_CHUNK_RAW)
    if len(raw)!=item.uncompressed_size:
        raise StaticPackError("uncompressed chunk length mismatch")
    return raw
