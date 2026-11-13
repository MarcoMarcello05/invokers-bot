from __future__ import annotations
import os, struct, time
from pathlib import Path

DEFAULT = Path(os.environ.get('LOCALAPPDATA','')) / 'Low' / 'Hit_Zone' / 'Invokers' / 'aggregate_snapshots' / 'PlayerArenaModel.dat'
# LOCALAPPDATA points AppData/Local; Unity LocalLow is its sibling.
def arena_path():
    p = DEFAULT
    if p.exists(): return p
    la = Path(os.environ.get('LOCALAPPDATA',''))
    p = la.parent / 'LocalLow' / 'Hit_Zone' / 'Invokers' / 'aggregate_snapshots' / 'PlayerArenaModel.dat'
    return p

def _i32(b,o): return struct.unpack_from('<i',b,o)[0]

def read_opponents(path:Path|None=None):
    path = path or arena_path(); b=path.read_bytes(); out=[]; seen=set()
    # MemoryPack UTF-8 string observed in ArenaOpponent: marker=-(byte_len+1), byte_len, bytes.
    for pos in range(8, len(b)-40):
        try:
            marker=_i32(b,pos-8); ln=_i32(b,pos-4)
            if not (2 <= ln <= 32 and marker == -(ln+1)): continue
            raw=b[pos:pos+ln]
            if any(c<32 or c>126 for c in raw): continue
            name=raw.decode('utf-8')
            end=pos+ln
            level=_i32(b,end); points=_i32(b,end+4); power=_i32(b,end+23)
            if not (1<=level<=100 and 0<=points<=100000 and 100<=power<=1000000): continue
            # ArenaOpponent layout fingerprint around TeamSetup. Reject unrelated MemoryPack strings.
            if b[end+8:end+13] not in (b'\x0c\x04\x10\x04\x84', b'\x0f\x04\x10\x04\x84', b'\x10\x04\x10\x04\x84'):
                # version-tolerant field headers can vary; require repeated 04/84 structure instead
                chunk=b[end+8:end+23]
                if chunk.count(4)<3 or 0x84 not in chunk: continue
            key=(name,level,points,power)
            if key in seen: continue
            seen.add(key); out.append({'name':name,'level':level,'arena_points':points,'combat_power':power,'offset':pos})
        except Exception: pass
    return out

def signature(items): return tuple(sorted((x['name'],x['level'],x['arena_points'],x['combat_power']) for x in items))

def wait_for_change(old_sig, timeout=8.0, poll=.25, path=None):
    end=time.time()+timeout
    while time.time()<end:
        try:
            items=read_opponents(path); sig=signature(items)
            if items and sig != old_sig: return items
        except Exception: pass
        time.sleep(poll)
    return None
