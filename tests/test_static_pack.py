"""Synthetic HZCP format 4 fixtures; no real game/static payloads."""
from dataclasses import replace
from struct import pack
from hashlib import sha256
import brotli
import pytest

from invokers_bot.static_pack import (
    parse_static_pack,extract_chunk,StaticPackError,ChunkKey,MAIN_KEY,
)


def fixture(*,keys=((0,0),(1,7)),fmt=4,member_count=3,
            key_count=None,chunk_count=None,hash_count=None,
            extent=None,compression_flag=1,raw_size=None,tail=b""):
    raw=b"synthetic Main object"
    stored=brotli.compress(raw)
    other=b"abc"
    header=bytes([member_count])+pack("<i",len(keys) if key_count is None else key_count)
    header+=b"".join(pack("<qB7x",ident,category) for category,ident in keys)
    header+=pack("<i",2 if chunk_count is None else chunk_count)
    header+=pack("<iiiB3x",0,len(stored) if extent is None else extent,
                 len(raw) if raw_size is None else raw_size,compression_flag)
    header+=pack("<iiiB3x",len(stored),len(other),len(other),0)
    header+=pack("<iQQ",2 if hash_count is None else hash_count,17,23)+tail
    compressed=brotli.compress(header)
    pre=b"HZCP"+pack("<I",fmt)+b"\x05test1\x05test2"
    return pre+pack("<II",len(compressed),len(header))+compressed+stored+other,raw,other


def test_index_and_extract():
    blob,raw,other=fixture()
    index=parse_static_pack(blob,expected_revision="test1",expected_secondary_revision="test2")
    assert index.format_version==4 and index.artifact_sha256==sha256(blob).hexdigest()
    assert (index.static_revision,index.secondary_revision)==("test1","test2")
    assert len(index.chunks)==2 and index.chunks[MAIN_KEY].declared_hash==17
    assert extract_chunk(blob,index)==raw
    assert extract_chunk(blob,index,ChunkKey(1,7))==other
    with pytest.raises(TypeError):
        index.chunks[MAIN_KEY]=None


@pytest.mark.parametrize("kwargs",[
    {"fmt":5},{"member_count":2},{"key_count":3},{"chunk_count":1},{"hash_count":1},
    {"tail":b"x"},{"keys":((0,0),(0,0))},{"keys":((1,1),(1,2))},
    {"extent":999999},{"extent":-1},{"compression_flag":2},
])
def test_reject_malformed_header(kwargs):
    with pytest.raises(StaticPackError):
        parse_static_pack(fixture(**kwargs)[0])


@pytest.mark.parametrize("kwargs",[{"expected_revision":"test9"},{"expected_secondary_revision":"other"}])
def test_revision_mismatch(kwargs):
    with pytest.raises(StaticPackError,match="revision mismatch"):
        parse_static_pack(fixture()[0],**kwargs)


def test_truncations():
    blob,_,_=fixture()
    for n in (0,4,8,10,20,len(blob)-1):
        with pytest.raises(StaticPackError):
            parse_static_pack(blob[:n])


def test_bad_brotli_and_lengths():
    blob,_,_=fixture()
    # Synthetic prefix: magic/format 8 + two length-prefixed strings 12.
    corrupted=blob[:28]+bytes(10)+blob[38:]
    with pytest.raises(StaticPackError):
        parse_static_pack(corrupted)
    for kwargs in ({"raw_size":1},{"raw_size":100},{"raw_size":100*1024*1024}):
        blob,_,_=fixture(**kwargs)
        with pytest.raises(StaticPackError):
            extract_chunk(blob,parse_static_pack(blob))


def test_source_identity_and_missing_chunk():
    blob,_,_=fixture()
    index=parse_static_pack(blob)
    with pytest.raises(StaticPackError,match="artifact does not match"):
        extract_chunk(blob[:-1]+b"z",index)
    with pytest.raises(StaticPackError,match="unknown chunk"):
        extract_chunk(blob,index,ChunkKey(4,0))
