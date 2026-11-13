from __future__ import annotations
from pathlib import Path
import struct, json, re

RESOURCE_NAMES={}

def _i32(b,o): return struct.unpack_from('<i',b,o)[0]

def load_resource_enum(dump_root: Path):
    p=next(dump_root.rglob('ResourceTypeId.cs'))
    text=p.read_text(errors='ignore')
    out={}
    for name,val in re.findall(r'^\s*([A-Za-z0-9_]+)\s*=\s*(-?\d+),?\s*$',text,re.M): out[int(val)]=name
    return out

def find_resource_maps(path:Path, known_ids:set[int]):
    b=path.read_bytes(); candidates=[]
    for off in range(0,len(b)-4):
        n=_i32(b,off)
        if not 5<=n<=256 or off+4+n*8>len(b): continue
        pairs=[struct.unpack_from('<ii',b,off+4+i*8) for i in range(n)]
        keys=[k for k,v in pairs]
        if keys!=sorted(keys) or len(set(keys))!=n: continue
        if not all(k in known_ids and v>=0 for k,v in pairs): continue
        # Player resource maps always have core currency; current/gained include Gems, spent may not.
        if not {2,3}.issubset(keys): continue
        candidates.append((off,dict(pairs)))
    # remove overlapping/subset false positives by keeping maps with maximal useful cardinality per region
    clean=[]
    for off,m in candidates:
        if any(abs(off-o)<32 and len(m)<len(mm) for o,mm in candidates): continue
        clean.append((off,m))
    return clean

def read_player_resources(path:Path,dump_root:Path):
    names=load_resource_enum(dump_root); maps=find_resource_maps(path,set(names))
    # top-level order in PlayerModel: Resources, ResourcesGained, ResourcesSpent
    maps=sorted(maps,key=lambda x:x[0])[:3]
    labels=['current','gained','spent']
    result={}
    for label,(off,m) in zip(labels,maps):
        result[label]={'offset':off,'count':len(m),'values':{names.get(k,str(k)):v for k,v in m.items()}}
    return result


def read_level_stats(path:Path):
    b=path.read_bytes(); rows=[]; seen=set()
    valid_areas={1,2,3,4,5,6,7,8}; valid_diffs={1,2,3,9}
    for o in range(0,len(b)-64):
        a,r,d,n=struct.unpack_from('<iiii',b,o)
        if a not in valid_areas or not (-1<=r<=501) or d not in valid_diffs or not (1<=n<=100): continue
        if b[o+16:o+22] != b'\x08\x00\x04\x04\x08\x04': continue
        h=b[o+16:o+32]; parsed=None
        for rel in range(6,16):
            if h[rel] != 4: continue
            start=o+16+rel+1
            victories,defeats=struct.unpack_from('<ii',b,start)
            best=struct.unpack_from('<i',b,start+16)[0]
            if 0<=victories<=1000 and 0<=defeats<=1000 and 0<=best<=100000:
                parsed=(victories,defeats,best); break
        if not parsed: continue
        key=(a,r,d,n)
        if key in seen: continue
        seen.add(key)
        v,df,bt=parsed
        rows.append({'offset':o,'area':a,'region':r,'difficulty':d,'number':n,'victories':v,'defeats':df,'best_time_seconds':bt})
    return rows

def campaign_summary(rows):
    c=[x for x in rows if x['area']==1 and x['difficulty'] in (1,2,3)]
    out={}
    for diff,name in [(1,'Normal'),(2,'Hard'),(3,'Brutal')]:
        rr=sorted([x for x in c if x['difficulty']==diff],key=lambda x:(x['region'],x['number']))
        if not rr: continue
        won=[x for x in rr if x['victories']>0]
        failed=[x for x in rr if x['victories']==0 and x['defeats']>0]
        out[name]={'entries':len(rr),'highest_won': ({k:won[-1][k] for k in ('region','number','victories','defeats')} if won else None),
                   'first_failed': ({k:failed[0][k] for k in ('region','number','victories','defeats')} if failed else None)}
    return out

def main():
    root=Path('/mnt/data/workdeep/live/Invokers_LiveData'); dump=Path('/mnt/data/workdeep/dump')
    levels=read_level_stats(root/'PlayerBattleModel.dat')
    out={'resources':read_player_resources(root/'PlayerModel.dat',dump),'level_stats':levels,'campaign':campaign_summary(levels)}
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
