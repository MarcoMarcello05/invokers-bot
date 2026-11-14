from dataclasses import replace
from types import SimpleNamespace
import time
import pytest
from invokers_bot.arena_opponent import parse_opponent, opponent_set_fingerprint
from invokers_bot.arena_refresh import update_arena,CACHE_KEYS
from invokers_bot.account_state import Observation,AccountState
from invokers_bot.transition_probe import observe_transition
from invokers_bot.snapshot_envelope import SnapshotFormatError
from test_arena_model import opponent,root,obj,envelope
from invokers_bot.arena_model import parse_arena_snapshot

def test_verified_fields():
    o=parse_opponent(opponent("same",1))
    assert (o.name,o.level,o.arena_points,o.combat_power)==("same",7,534,6151)
    assert o.identity=="01"*16
    assert o.opaque_slots[2]==b"opaque"
    assert o.team_setup.opaque_slots[2]==b"team-opaque"

@pytest.mark.parametrize("data",[b"",b"\xff",opponent("same",1)[:-1],opponent("same",0),opponent("same",1,-1)])
def test_invalid(data):
    with pytest.raises(SnapshotFormatError):
        parse_opponent(data)

def test_identity_and_fingerprint():
    a,b=[parse_opponent(opponent("same",i)) for i in (1,2)]
    assert a.identity!=b.identity
    assert opponent_set_fingerprint([a,b])==opponent_set_fingerprint([b,a])
    assert opponent_set_fingerprint([a,b])!=opponent_set_fingerprint([a])
    assert opponent_set_fingerprint([a,b])!=opponent_set_fingerprint([a,parse_opponent(opponent("same",2,6152))])
    with pytest.raises(SnapshotFormatError):
        opponent_set_fingerprint([a,a])

def account(model,digest):
    return AccountState({"arena":Observation(model,None,digest,time.monotonic())},frozenset())

def test_refresh():
    model=parse_arena_snapshot(envelope(obj(root())))
    facts={}
    assert not update_arena(facts,account(model,"a"))
    facts.update({k:object() for k in CACHE_KEYS})
    assert update_arena(facts,account(model,"b"))
    assert not facts["arena_refresh_event"]["semantic_refresh"]
    facts.update({k:object() for k in CACHE_KEYS})
    changed=replace(model,opponent_set_fingerprint="different",last_opponents_refresh_ticks=model.last_opponents_refresh_ticks+1)
    assert update_arena(facts,account(changed,"c"))
    assert facts["arena_refresh_event"]["semantic_refresh"]
    assert facts["arena_refresh_event"]["refresh_time_changed"]
    assert not any(k in facts for k in CACHE_KEYS)

def test_probe():
    facts={}
    probes=[{"id":"own","from":"arena_list","to":"formation","sources":[["arena","a",9],["battle","b",7]]}]
    for i,screen in enumerate(("arena_list","formation","formation","arena_list")):
        events=list(observe_transition(facts,screen,probes,lambda name,tag:{"version":i,"digest":str(tag)},now=i))
    event=events[0]
    assert (event["A"]["battle"]["version"],event["B"]["battle"]["version"],event["C"]["battle"]["version"])==(0,1,3)
    assert event["B_latest"]["arena"]["version"]==2
