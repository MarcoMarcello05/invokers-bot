"""Synthetic wire fixtures, no user/account snapshots."""
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from pathlib import Path
from struct import pack
import ast
import time
import pytest
from invokers_bot.quests_model import *
from invokers_bot.quest_domain import quest_view,quest_goal_facts
from invokers_bot.account_state import AccountObserver, AccountState
from test_arena_model import obj,member_length,STAMP

def i(value):
    return pack("<i",value)

def quest(key,tag,state,group,*,extra=False):
    s=[b""]*51
    s[0],s[1],s[2],s[3],s[5],s[50]=i(key),i(700+key),i(state),STAMP,i(2),i(group)
    if extra:
        s[4]=b"reserved"
        s.append(b"future")
    return bytes([tag])+obj(s)

def dictionary(entries):
    return i(len(entries))+b"".join(i(k)+v for k,v in entries)

def root():
    later=pack("<Q",(621355968000000000+864000000000)|(1<<62))
    return [i(20),dictionary([(4,quest(4,3,1,2)),(3,quest(3,2,3,88)),(2,quest(2,1,2,2)),
        (1,quest(1,1,3,1)),(5,quest(5,1,3,99)),(6,quest(6,3,17,2))]),
        i(3)+i(701)+i(702)+i(701),
        dictionary([(2,obj([STAMP,bytes(16)])),(1,obj([STAMP,b"\x01"+bytes(7)+later])),
                    (99,obj([STAMP,bytes(16)]))]),
        dictionary([(88,obj([i(4),i(5)]))]),i(9)]

def envelope(slots,version=3):
    payload=obj(slots)
    return b"\x08\x03\x08\x08"+member_length(len(payload))+pack("<q",version)+STAMP+payload

def test_quest_fields():
    state=parse_quests_snapshot(envelope(root()))
    assert (state.version,state.last_quest_id,state.total_completed_quests)==(3,20,9)
    assert len(state.active_by_id)==6
    assert (state.active_by_id[1].quest_id,state.active_by_id[1].prototype_id,state.active_by_id[1].progress)==(1,701,2)
    assert state.completed_prototype_ids==(701,702,701)
    assert state.active_by_id[6].state_id==17
    assert state.achievement_groups[88]==AchievementProgress(88,4,5)
    assert state.periodic_groups[2].finish_time_utc is None
    assert state.periodic_groups[1].finish_time_utc-state.periodic_groups[1].start_time_utc==timedelta(days=1)
    assert state.periodic_groups[99].group==99
    with pytest.raises(TypeError):
        state.active_by_id[1]=None
    with pytest.raises(FrozenInstanceError):
        state.active_by_id[1].progress=3

@pytest.mark.parametrize("key,kind,group",[(1,QuestKind.PERIODIC,1),(3,QuestKind.ACHIEVEMENT,88),(4,QuestKind.BOOK,2)])
def test_union(key,kind,group):
    q=parse_quests_snapshot(envelope(root())).active_by_id[key]
    assert q.kind==kind and q.source_union_tag==kind.value and q.group_or_page==group

def test_future_slots_skipped():
    s=root()
    s[1]=dictionary([(1,quest(1,1,3,1,extra=True))])
    s.append(b"future root")
    assert parse_quests_snapshot(envelope(s)).active_by_id[1].state_id==3

@pytest.mark.parametrize("slot,raw",[
    (0,b""),(1,dictionary([(2,quest(1,1,3,1))])),
    (1,dictionary([(1,quest(1,4,3,1))])),
    (1,dictionary([(1,b"\x01"+obj([i(1)]))])),
    (1,dictionary([(1,quest(1,1,3,1)),(1,quest(1,1,3,1))])),
    (1,i(-1)),(1,i(1000)),(1,i(0)+b"x"),
    (2,i(2)+i(1)),(2,i(0)+b"x"),
    (3,dictionary([(1,obj([STAMP,b"\x02"+bytes(15)]))])),
    (3,dictionary([(1,obj([STAMP,b"\x00"]))])),
    (3,dictionary([(1,obj([STAMP,bytes(16)])),(1,obj([STAMP,bytes(16)]))])),
    (4,dictionary([(1,obj([i(1),b"x"]))])),
    (5,b"\x01")])
def test_malformed(slot,raw):
    s=root()
    s[slot]=raw
    with pytest.raises(SnapshotFormatError):
        parse_quests_snapshot(envelope(s))

def test_truncated_root():
    with pytest.raises(SnapshotFormatError):
        parse_quests_snapshot(envelope(root()[:-1]))

def test_wrong_aggregate():
    with pytest.raises(SnapshotFormatError):
        parse_quests_snapshot(b"\x09"+envelope(root())[1:])

def test_observer_and_domain(tmp_path):
    path=tmp_path/"PlayerQuestsModel.dat"
    blob=envelope(root());path.write_bytes(blob)
    obs=AccountObserver(tmp_path)
    state=obs.refresh(force=True,sources={"quests"})
    item=state.sources["quests"]
    assert state.changed=={"quests"} and state.quests is item.model
    assert path.read_bytes()==blob
    view=quest_view(state,now=item.checked_at)
    assert [q.quest_id for q in view.all_completed_candidates()]==[1,3,5]
    assert [q.quest_id for q in view.periodic_candidates(1)]==[1]
    assert [w.group for w in view.active_periodic_windows()]==[1,2,99]
    a,b,c=view.all_completed_candidates()
    assert a.periodic_finish_time_utc is not None and b.periodic_finish_time_utc is None and c.periodic_finish_time_utc is None
    summary=view.summary()
    assert (summary.total_active,summary.total_completed_state_active,summary.periodic_count,
            summary.achievement_count,summary.book_count,summary.completed_prototype_count)==(6,3,3,1,2,3)
    assert summary.total_completed_quests==9
    facts=quest_goal_facts(state,now=item.checked_at)
    assert facts.source_fresh and facts.has_completed_candidates and facts.completed_candidate_count==3
    assert facts.groups_with_completed_candidates==(1,99)
    assert facts.nearest_known_periodic_finish_time==a.periodic_finish_time_utc
    assert facts.provenance.digest==item.digest and facts.provenance.version==3
    assert quest_goal_facts(state,now=item.checked_at+3).has_completed_candidates is None
    unchanged=obs.refresh(force=True,sources={"quests"})
    assert not unchanged.changed and unchanged.quests is item.model and unchanged.sources["quests"].digest==item.digest
    path.write_bytes(envelope(root(),version=4))
    updated=obs.refresh(force=True,sources={"quests"})
    assert updated.changed=={"quests"} and updated.quests.version==4
    path.write_bytes(b"bad")
    broken=obs.refresh(force=True,sources={"quests"})
    assert broken.quests is None and broken.sources["quests"].model is updated.quests
    assert quest_view(broken,now=broken.sources["quests"].checked_at) is None

def test_source_scoped_invalidation(tmp_path):
    from test_arena_model import root as arena_root,envelope as arena_envelope
    (tmp_path/"PlayerQuestsModel.dat").write_bytes(envelope(root()))
    (tmp_path/"PlayerArenaModel.dat").write_bytes(arena_envelope(obj(arena_root())))
    obs=AccountObserver(tmp_path)
    state=obs.refresh(force=True,sources={"arena","quests"})
    obs.invalidate({"quests"})
    assert obs.state.arena is state.arena and obs.state.quests is None
    same=obs.refresh(force=True,sources={"quests"})
    assert same.quests is None and same.sources["quests"].awaiting_change
    (tmp_path/"PlayerQuestsModel.dat").write_bytes(envelope(root(),version=4))
    new=obs.refresh(force=True,sources={"quests"})
    assert new.changed=={"quests"} and new.quests.version==4 and new.arena is state.arena

def test_no_input_dependency():
    base=Path(__file__).resolve().parents[1]/"src"/"invokers_bot"
    for name in ("quests_model.py","quest_domain.py"):
        tree=ast.parse((base/name).read_text())
        imports=[n.module or "" for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        imports += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
        assert not any(any(word in module for word in ("input","engine","vision","ocr","action","cv2","pyautogui")) for module in imports)

def test_facts_empty_is_not_unknown(tmp_path):
    s=root();s[1]=i(0)
    (tmp_path/"PlayerQuestsModel.dat").write_bytes(envelope(s))
    state=AccountObserver(tmp_path).refresh(force=True,sources={"quests"})
    facts=quest_goal_facts(state,now=state.sources["quests"].checked_at)
    assert facts.has_completed_candidates is False and facts.completed_candidate_count==0
    assert facts.groups_with_completed_candidates==()
    assert quest_goal_facts(None,now=0).has_completed_candidates is None
