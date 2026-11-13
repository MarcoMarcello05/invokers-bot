from __future__ import annotations
from pathlib import Path
import json, re, zipfile, sys
from memorypack import DecodeError, field, model

def load_resource_enum(dump_root: Path | None = None):
    if dump_root is None:
        dump_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))/'raw/dumps/InvokersDump(2).zip'
        if not dump_root.is_file():
            dump_root = Path(__file__).resolve().parent/'schemas/ResourceTypeId.cs'
    if dump_root.suffix == '.cs':
        text=dump_root.read_text(encoding='utf-8')
    elif dump_root.is_dir():
        p=next(dump_root.rglob('ResourceTypeId.cs'))
        text=p.read_text(errors='ignore')
    else:
        with zipfile.ZipFile(dump_root) as archive:
            names=[n for n in archive.namelist() if Path(n).name=='ResourceTypeId.cs']
            if len(names)!=1: raise DecodeError('ResourceTypeId schema is ambiguous/missing')
            text=archive.read(names[0]).decode()
    out={}
    for name,val in re.findall(r'^\s*([A-Za-z0-9_]+)\s*=\s*(-?\d+),?\s*$',text,re.M): out[int(val)]=name
    return out

def read_player_resources(path:Path,dump_root:Path | None = None):
    names=load_resource_enum(dump_root)
    fields=model(path.read_bytes(),1)
    result={}
    # Retired members occupy wire slots; do not use backing-field list indices.
    for label,index in [('current',9),('gained',10),('spent',11)]:
        span=field(field(fields,index).object(),0)
        reader=span.reader(); values={}; previous=None
        for _ in range(reader.count(8)):
            key,value=reader.integer(),reader.integer()
            if (previous is not None and key<=previous) or value<0:
                raise DecodeError('Invalid resource dictionary')
            values[names.get(key,str(key))]=value; previous=key
        reader.finish()
        result[label]={'offset':span.offset,'count':len(values),'values':values}
    return result


def read_level_stats(path:Path):
    fields=model(path.read_bytes(),7)
    reader=field(fields,1).reader(); rows=[]; seen=set()
    for _ in range(reader.count(17)):
        offset=reader.offset+reader.pos
        key=tuple(reader.integer() for _ in range(4))
        if key in seen: raise DecodeError('Duplicate level identifier')
        seen.add(key)
        stats=reader.object()
        v,df,bt=(field(stats,i).integer() for i in (1,2,4))
        if min(v,df,bt)<0: raise DecodeError('Negative level statistics')
        a,r,d,n=key
        rows.append({'offset':offset,'area':a,'region':r,'difficulty':d,'number':n,
                     'victories':v,'defeats':df,'best_time_seconds':bt})
    reader.finish()
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
    import argparse
    parser=argparse.ArgumentParser(description='Read structured resources and campaign state')
    parser.add_argument('--snapshots',type=Path,default=Path(__file__).resolve().parents[1]/'tests/fixtures')
    parser.add_argument('--dump',type=Path)
    args=parser.parse_args(); root=args.snapshots; dump=args.dump
    levels=read_level_stats(root/'PlayerBattleModel.dat')
    out={'resources':read_player_resources(root/'PlayerModel.dat',dump),'level_stats':levels,'campaign':campaign_summary(levels)}
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
