"""Read-only metadata discovery. No raw archive output or catalog guesses."""
import argparse
import hashlib
import io
import re
import struct
import subprocess
import zipfile

ARCHIVE="d363ef72e3cde80e05cc3829ac09f0137acedc5f"
PREFIX="InvokersBot_CODEX_HANDOFF/raw/"
TYPE=re.compile(r"(?:Quest(?:Prototype|Condition|Action|Reward|Definition|Config|Requirement|Task|State|Periodic|Achievement|Book)|StaticQuestData|StaticData|ChunkPackHeader|PackChunk|ChunkKey|ChunkCategory|RewardPrototype|IReward|BattleArea|PackChunkKey|QuestAchievementKey|QuestAchievementGroupSettings|QuestPeriodicGroupShard|QuestBookPageShard|QuestAchievementGroupShard|Reward\.cs|AreaId\.cs|RegionId\.cs|Difficulty\.cs|StaticDataProvider|QuestNavigation)")

def read_git(path):
    return subprocess.check_output(["git","show",f"{ARCHIVE}:{PREFIX}{path}"])

def describe_zip(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        files=[n for n in z.namelist() if n.lower().endswith(".cs") and TYPE.search(n.rsplit("/",1)[-1])]
        print("Named C# candidates:",len(files))
        for name in sorted(files):
            if not re.search(r"(?:Formatter|DisplayClass|Iterator|MemoryPackFormatter|<>|__)",name.rsplit("/",1)[-1]):
                print("TYPE FILE",name)
        # Individual DiffableCs declarations, not source bodies or bulk dumps.
        wanted=re.compile(r"^(?:IQuestPrototype|QuestPrototype\w*|IQuestCondition|QuestCondition\w*|QuestAction|StaticQuestData|StaticData|StaticDataContainer|ChunkPackHeader|PackChunk|ChunkKey|ChunkCategory|QuestReward\w*|QuestStateBase|QuestPeriodicGroup|QuestAchievementGroupSettings|QuestAchievementKey|QuestPeriodicGroupShard|QuestBookPageShard|QuestAchievementGroupShard|PackChunkKey|Reward|AreaId|RegionId|Difficulty|BattleArea\w*)\.cs$")
        for name in sorted(files):
            if not wanted.fullmatch(name.rsplit("/",1)[-1]):
                continue
            data=z.read(name).decode("utf-8",errors="replace")
            print("SCHEMA",name)
            for line in data.splitlines():
                line=line.split("//",1)[0].strip()
                if re.match(r"^(?:namespace\s|\[.*(?:MemoryPack|GenerateType|SerializeLayout)|(?:public|internal|private|protected)\s.*(?:\bclass\b|\bstruct\b|\binterface\b|\benum\b|k__BackingField;))",line) or re.match(r"^(?:public|private|internal|protected)\s+(?:readonly\s+|const\s+|static\s+)*[\w.<>,?\[\]` ]+\s+\w+\s*(?:;|=\s*-?\d+;)$",line):
                    if len(line)<500:
                        print(line)
                elif re.match(r"^\w+\s*=\s*-?\d+\s*,?$",line):
                    print(line)
                elif re.match(r"^(?:public|internal|private|protected)\s+[^{};]*(?:PrototypeById|GetPrototype|GetQuestPrototype|QuestData|Keys|Chunks|Hashes|Deserialize|Serialize)\s*\([^{};]*\)\s*;?$",line):
                    print(line)
            # No method bodies, values from static pack, or account material.

def describe_pack(blob):
    import brotli
    print("STATIC size",len(blob),"sha256",hashlib.sha256(blob).hexdigest())
    if blob[:4]!=b"HZCP":
        print("UNSUPPORTED_MAGIC");return
    print("magic HZCP; format word",struct.unpack_from("<I",blob,4)[0],"; header probe using archived hypothesis")
    pos=8
    for _ in range(2):
        if pos>=len(blob): raise ValueError("truncated pack string")
        n=blob[pos];pos+=1
        if pos+n>len(blob): raise ValueError("truncated pack string")
        # strings may be revision/build; print only safe short version strings
        value=blob[pos:pos+n]
        print("header string",value.decode("ascii") if re.fullmatch(rb"[0-9A-Za-z._-]{1,80}",value) else "opaque", "length",n)
        pos+=n
    packed,raw=struct.unpack_from("<II",blob,pos);pos+=8
    if not 0<packed<=len(blob)-pos or not 0<raw<=64*1024*1024:
        raise ValueError("invalid pack header lengths")
    header=brotli.decompress(blob[pos:pos+packed])
    if len(header)!=raw: raise ValueError("header raw size mismatch")
    count=struct.unpack_from("<i",header,1)[0]
    if not 1<=count<=100000: raise ValueError("invalid key count")
    start=5+16*count
    if start+4>len(header): raise ValueError("key table truncated")
    chunk_count=struct.unpack_from("<i",header,start)[0]
    chunk_end=start+4+16*count
    if count!=chunk_count or chunk_end>len(header):
        print("HEADER_LAYOUT_UNVERIFIED",len(header),count,chunk_count);return
    print("header object member-count byte",header[0])
    print("header packed/raw",packed,raw,"key/chunk count",count,"remainder after key/chunk entries",len(header)-chunk_end)
    if len(header)-chunk_end>=4:
        tail_count=struct.unpack_from("<i",header,chunk_end)[0]
        print("trailing vector candidate count",tail_count,"width8 exact",len(header)-chunk_end==4+8*tail_count)
    # The third vector must be checked against its actual C# declaration.
    # Extract the Main candidate only if all key/chunk extents validate.
    main=[]
    for i in range(count):
        key_id,cat=struct.unpack_from("<qB",header,5+16*i)
        off,size,usize,comp=struct.unpack_from("<iiiB",header,start+4+16*i)
        if min(off,size,usize)<0 or comp not in (0,1) or pos+packed+off+size>len(blob):
            raise ValueError("chunk extent invalid")
        if key_id==0 and cat==0: main.append((off,size,usize,comp))
    print("unique Main key",len(main)==1)
    if len(main)==1:
        off,size,usize,comp=main[0]
        data=blob[pos+packed+off:pos+packed+off+size]
        result=brotli.decompress(data) if comp else data
        print("Main stored/uncompressed",size,len(result),"declared size matches",len(result)==usize)
        print("Main SHA256",hashlib.sha256(result).hexdigest())
        print("Main root member-count byte",result[0] if result else None)
        print("No quest table boundaries asserted")
        if len(result)==usize:
            compare_historical_candidates(result)

def compare_historical_candidates(main):
    """Count-only comparison with old prefix scan; never return definitions."""
    from invokers_bot.quests_model import parse_quests_snapshot
    try:
        raw=subprocess.check_output(["git","show",f"{ARCHIVE}:InvokersBot_CODEX_HANDOFF/tests/fixtures/PlayerQuestsModel.dat"])
        state=parse_quests_snapshot(raw)
    except (ValueError,subprocess.CalledProcessError) as exc:
        print("Archived quest comparison unavailable",type(exc).__name__)
        return
    wanted={q.prototype_id for q in state.active_by_id.values()}
    matches={}
    # This is the archived prefix hypothesis, not a reliable object boundary.
    pattern=b"\x01\x0a"
    pos=main.find(pattern)
    while pos!=-1:
        if pos+14<=len(main):
            pid,action,amount=struct.unpack_from("<iii",main,pos+2)
            if pid in wanted and 0<=action<=10000 and 0<=amount<=100000000:
                matches[pid]=matches.get(pid,0)+1
        pos=main.find(pattern,pos+1)
    print("HEURISTIC ONLY: archived active distinct IDs",len(wanted),
          "matched periodic signature",len(matches),"ambiguous",sum(n>1 for n in matches.values()))
    print("Prototype values/objectives withheld; no verified table join")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",action="store_true",required=True)
    parser.parse_args()
    describe_pack(read_git("static/static-data.0.62.1655(1).dat"))
    describe_zip(read_git("dumps/InvokersDump(2).zip"))
    describe_zip(read_git("dumps/InvokersIL(1).zip"))

if __name__=="__main__":
    main()
