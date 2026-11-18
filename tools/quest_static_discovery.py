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
    from invokers_bot.static_pack import parse_static_pack, extract_chunk, MAIN_KEY
    pack=parse_static_pack(blob,expected_revision="0.62.1655",
                           expected_secondary_revision="0.62.700")
    if pack.artifact_sha256!="85c4b47a4b07e73454e6f923416a9f5da516599d455dc721c172b9ebf7805e4c":
        raise ValueError("unexpected archived artifact fingerprint")
    print("STRICT HZCP index validated",pack.format_version,pack.static_revision,pack.secondary_revision)
    print("STATIC size",pack.artifact_size,"sha256",pack.artifact_sha256)
    print("header packed/raw",pack.header_size,pack.header_raw_size,"key/chunk/hash count",len(pack.chunks))
    main=extract_chunk(blob,pack)
    digest=hashlib.sha256(main).hexdigest()
    if digest!="be4fd758a5a107b8f39ee9001e3f472e5c5175aaa2821fcecd3ce197eeff482f":
        raise ValueError("unexpected archived Main fingerprint")
    print("Main stored/uncompressed",pack.chunks[MAIN_KEY].size,len(main))
    print("Main SHA256",digest,"root member-count byte",main[0] if main else None)
    print("ChunkHashes preserved, algorithm not verified; no quest table boundaries asserted")
    compare_historical_candidates(main)

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
