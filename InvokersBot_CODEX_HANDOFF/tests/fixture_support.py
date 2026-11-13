"""Optional private captures stay outside Git; ordinary tests generate a public profile.

Set INVOKERS_PRIVATE_COMPARE locally to run the same assertions on a private ZIP.
No private archive, account manifest or filesystem path is embedded in the repo.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def pack(fields):
    return bytes([len(fields)])+b''.join(bytes([len(x)]) if len(x)<=127 else b'\x82'+struct.pack('<i',len(x)) for x in fields)+b''.join(fields)


def clan_sample():
    integer=lambda x:struct.pack('<i',x)
    text=b'TEST'
    membership=pack([b'\x12'*16,integer(20),b'\0'*8,b'\0'*16,struct.pack('<ii',~len(text),len(text))+text])
    boss=pack([b'\0'*8,integer(0),integer(0),integer(0),integer(0)])
    fields=[b'']*19
    fields[0]=membership
    for index in (6,7,8,9):fields[index]=b'\xff'
    fields[18]=boss
    return b'\x0c'+pack([b'\0'*8,b'\0'*8,pack(fields)])


@contextmanager
def comparison_fixture():
    private=os.environ.get('INVOKERS_PRIVATE_COMPARE')
    if private:
        path=Path(private)
        if not path.is_file():raise FileNotFoundError('Configured private comparison archive does not exist')
        yield path,True
        return
    with TemporaryDirectory(prefix='invokers-public-compare-') as directory:
        path=Path(directory)/'comparison.zip'
        data={p.name:p.read_bytes() for p in (ROOT/'tests/fixtures').glob('Player*.dat')}
        data.update({'PlayerClanModel.dat':clan_sample(),'PlayerShopModel.dat':b'synthetic-unused-shop',
                     'PlayerInboxModel.dat':b'synthetic-unused-inbox'})
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for group in ('A_BEFORE_ARENA','B_FORMATION','C_AFTER_BACK'):
                manifest=[]
                for name,payload in data.items():
                    archive.writestr(group+'\\'+name,payload)
                    manifest.append({'Name':name,'Size':len(payload),'SHA256':hashlib.sha256(payload).hexdigest(),
                                     'LastWriteTimeUtc':'2020-01-01T00:00:00Z'})
                archive.writestr(group+'\\manifest.json',json.dumps(manifest))
                archive.writestr(group+'\\capture_info.json',json.dumps({'file_count':len(data),'note':'Generated test profile; not a live capture'}))
        yield path,False


def arena_source_samples():
    """Invented minimal wire samples for packaged Arena tests, no player captures."""
    i=lambda value:struct.pack('<i',value)
    string=lambda value:struct.pack('<ii',~len(value.encode()),len(value))+value.encode()
    envelope=lambda tag,fields:bytes([tag])+pack([b'\0'*8,b'\0'*8,pack(fields)])
    team=pack([i(2000),b'\x34'*16])
    opponent=pack([string('UnitTarget'),i(1),b'',i(100),team])
    stats=[b'']*4+[i(0)]*9+[i(0)]+[i(0)]*4
    arena=[b'']*18
    arena[5]=b'\0'*8;arena[7]=b'\0'*8
    arena[10]=pack(stats);arena[12]=i(1)+opponent;arena[15]=i(0)
    account=[b'']*12
    resources=pack([i(2)+i(1)+i(10)+i(21)+i(5)])
    account[9]=resources;account[10]=resources;account[11]=pack([i(0)])
    return {'PlayerArenaModel.dat':envelope(9,arena),'PlayerModel.dat':envelope(1,account)}
