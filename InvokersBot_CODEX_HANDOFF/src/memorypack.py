"""Bounded readers for the captured little-endian MemoryPack profile.

VersionTolerant objects have a byte member count, signed VarInt field lengths,
then concatenated payloads. Zero lengths are reserved/omitted fields, not nulls.
This is deliberately not a general-purpose MemoryPack implementation.
"""
from dataclasses import dataclass
import struct


class DecodeError(ValueError):
    pass


@dataclass(frozen=True)
class Span:
    data: bytes
    offset: int = 0

    def reader(self):
        return Reader(self.data, self.offset)

    def integer(self, fmt='i'):
        if len(self.data) != struct.calcsize('<' + fmt):
            raise DecodeError(f'Invalid {fmt} width at {self.offset}: {len(self.data)}')
        return struct.unpack('<' + fmt, self.data)[0]

    def boolean(self):
        if self.data not in (b'\x00', b'\x01'):
            raise DecodeError(f'Invalid bool at {self.offset}')
        return bool(self.data[0])

    def nullable(self, fmt='i'):
        # MemoryPack writes unmanaged Nullable<T> including CLR alignment/padding.
        size = struct.calcsize('<' + fmt)
        alignment = size
        if len(self.data) != alignment + size or self.data[0] not in (0, 1):
            raise DecodeError(f'Invalid nullable {fmt} at {self.offset}')
        return struct.unpack_from('<' + fmt, self.data, alignment)[0] if self.data[0] else None

    def object(self):
        reader = self.reader()
        fields = reader.object()
        reader.finish()
        return fields

    def string(self):
        reader = self.reader()
        length = reader.integer()
        if length == -1:
            reader.finish()
            return None
        if length >= 0:
            value = reader.take(length * 2).data.decode('utf-16-le')
        else:
            chars = reader.integer()
            if chars < 0:
                raise DecodeError('Invalid UTF-8 character count')
            value = reader.take(~length).data.decode('utf-8')
            if len(value.encode('utf-16-le')) // 2 != chars:
                raise DecodeError('UTF-8 character count mismatch')
        reader.finish()
        return value


class Reader:
    VARINT = {128: 'q', 129: 'Q', 130: 'i', 131: 'I',
              132: 'h', 133: 'H', 134: 'b', 135: 'B'}

    def __init__(self, data, offset=0):
        self.data, self.offset, self.pos = data, offset, 0

    def take(self, size):
        if size < 0 or size > len(self.data) - self.pos:
            raise DecodeError(f'Truncated payload at {self.offset + self.pos}: need {size}')
        span = Span(self.data[self.pos:self.pos + size], self.offset + self.pos)
        self.pos += size
        return span

    def integer(self, fmt='i'):
        return self.take(struct.calcsize('<' + fmt)).integer(fmt)

    def count(self, minimum_item_size=1):
        count = self.integer()
        if count < 0 or count > (len(self.data) - self.pos) // minimum_item_size:
            raise DecodeError(f'Invalid collection count {count} at {self.offset + self.pos - 4}')
        return count

    def object(self):
        count = self.integer('B')
        if count == 255:
            return None
        if count >= 250:
            raise DecodeError('Unsupported object header')
        lengths = []
        for _ in range(count):
            code = self.integer('B')
            size = self.integer(self.VARINT[code]) if code in self.VARINT else (code if code < 128 else code - 256)
            if size < 0:
                raise DecodeError('Negative field length')
            lengths.append(size)
        return [self.take(size) for size in lengths]

    def finish(self):
        if self.pos != len(self.data):
            raise DecodeError(f'Unconsumed bytes at {self.offset + self.pos}')


def field(fields, index):
    if fields is None or index >= len(fields) or not fields[index].data:
        raise DecodeError(f'Missing required field {index}')
    return fields[index]


def model(data, tag):
    reader = Reader(data)
    if reader.integer('B') != tag:
        raise DecodeError('Unexpected snapshot union tag')
    wrapper = reader.object()
    reader.finish()
    if wrapper is None or len(wrapper) != 3:
        raise DecodeError('Unsupported snapshot envelope')
    field(wrapper, 0).integer('q')
    field(wrapper, 1).integer('q')
    return field(wrapper, 2).object()


def int_list(span):
    reader = span.reader()
    count = reader.count(4)
    values = [reader.integer() for _ in range(count)]
    reader.finish()
    if len(set(values)) != len(values):
        raise DecodeError('Duplicate set member')
    return values
