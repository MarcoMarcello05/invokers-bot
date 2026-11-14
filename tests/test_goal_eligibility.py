import json
from types import SimpleNamespace
from dataclasses import replace
from pathlib import Path
import time

import pytest

from invokers_bot.account_state import AccountState, Observation
from invokers_bot.goal_eligibility import decide, authorize_action, ARENA, REFRESH
from invokers_bot.action_verification import ActionExpectation, evaluate, baseline_valid
from invokers_bot.models import GameState

CFG = json.loads((Path(__file__).resolve().parents[1]/"config"/"arena.json").read_text())


def account(tokens=9, *, age=0, error=None, pending=False, version=1, digest="a"):
    model = SimpleNamespace(version=version, resources={} if tokens is None else {21:tokens})
    return AccountState({"player":Observation(model,None,digest,time.monotonic()-age,error,pending)},frozenset())


@pytest.mark.parametrize("tokens,age,error,pending,reason", [
    (9,0,None,False,None),
    (10,0,None,False,None),
    (0,0,None,False,"BELOW_THRESHOLD"),
    (None,0,None,False,"ARENA_TOKEN_MISSING_OR_INVALID"),
    (9,10,None,False,"PLAYER_STALE_OR_INVALID"),
    (9,0,"bad",False,"PLAYER_STALE_OR_INVALID"),
    (9,0,None,True,"PLAYER_STALE_OR_INVALID"),
])
def test_eligibility(tokens,age,error,pending,reason):
    trace = decide(account(tokens,age=age,error=error,pending=pending),CFG,observer_available=True)
    evaluation = trace.evaluations[1]
    assert evaluation.eligible == (reason is None)
    if reason:
        assert reason in evaluation.blocked_reasons and trace.selected != ARENA
    else:
        assert trace.selected == ARENA


def test_missing_and_no_source():
    trace = decide(None,CFG,observer_available=True)
    assert trace.selected == REFRESH and "PLAYER_MISSING" in trace.evaluations[1].blocked_reasons
    assert decide(None,CFG,observer_available=False).selected is None


def test_trace_determinism():
    state=account()
    now=time.monotonic()
    a=decide(state,CFG,observer_available=True,now=now,timestamp=1)
    b=decide(state,CFG,observer_available=True,now=now,timestamp=1)
    assert a==b
    trace=json.dumps(a.to_dict())
    assert "source_digest" in trace and "token_balance" in trace and "raw" not in trace


def test_reserve_and_cap_policy():
    config=json.loads(json.dumps(CFG))
    config["planner"]["arena"].update(threshold=1,reserve=9,cap=10,cost=1)
    assert "RESOURCE_RESERVE" in decide(account(9),config,observer_available=True).evaluations[1].blocked_reasons


def test_missing_navigation():
    config=json.loads(json.dumps(CFG))
    config["flows"].pop("formation")
    assert "ARENA_NAVIGATION_UNAVAILABLE" in decide(account(),config,observer_available=True).evaluations[1].blocked_reasons


@pytest.mark.parametrize("kind,tokens,error,success", [
    ("resource_delta",8,None,True),
    ("resource_delta",7,None,False),
    ("resource_delta",9,None,False),
    ("resource_delta",10,None,False),
    ("resource_delta",None,None,False),
    ("resource_delta",8,"bad",False),
    ("resource_decreased",7,None,True),
    ("resource_decreased",9,None,False),
    ("resource_decreased",10,None,False),
])
def test_semantic(kind,tokens,error,success):
    spec={"kind":kind,"resource_id":21}
    if kind=="resource_delta":
        spec["delta"]=-1
    exp=ActionExpectation.from_action({
        "invalidates_sources":["player"],"expects_source_change":["player"],
        "success_mode":"VISUAL_AND_STRUCTURED","semantic_predicates":[spec],
    })
    before=account()
    after=account(tokens,error=error,version=2,digest="b")
    result=evaluate(exp,GameState.FORMATION,GameState.BATTLE,before,after)
    assert result.success is success
    assert not baseline_valid(exp,account(None))


def test_configured_predicate():
    exp=ActionExpectation.from_action(CFG["flows"]["formation"]["actions"][0])
    assert len(exp.semantic_predicates)==1
    predicate=exp.semantic_predicates[0]
    assert (predicate.kind,predicate.resource_id,predicate.delta)==("resource_delta",21,-1)
    assert predicate.source=="player"
    assert exp.timeout==5


def test_invalid_predicate():
    with pytest.raises(ValueError):
        ActionExpectation.from_action({"semantic_predicates":[{"kind":"unknown"}]})



def test_regeneration_ceiling_does_not_clamp_wallet_or_enable_spend():
    trace=decide(account(12),CFG,observer_available=True)
    assert trace.selected == ARENA and trace.evaluations[1].eligible
    assert trace.evaluations[1].cap == 10
    assert trace.evaluations[1].token_balance == 12
    assert CFG["planner"]["arena"]["allow_test_battle_start"] is False
    assert CFG["flows"]["formation"]["actions"][0]["enabled"] is False
    assert authorize_action(CFG["flows"]["formation"]["actions"][0],trace,CFG) == "GOAL_BLOCKED:TEST_FLOW_NOT_ENABLED"


def test_explicit_cost_required_and_predicate_matches():
    config=json.loads(json.dumps(CFG))
    policy=config["planner"]["arena"]
    policy["allow_test_battle_start"]=True
    action=config["flows"]["formation"]["actions"][0]
    assert policy["cost"]==1
    trace=decide(account(3),config,observer_available=True)
    assert authorize_action(action,trace,config) is None
    policy["cost"]=None  # Synthetic unknown-cost scenario only.
    trace=decide(account(3),config,observer_available=True)
    assert authorize_action(action,trace,config)=="GOAL_BLOCKED:DENY_UNKNOWN_COST"
    policy["cost"]=1
    trace=decide(account(3),config,observer_available=True)
    for predicate in ({"kind":"resource_decreased","resource_id":21},
                      {"kind":"resource_delta","resource_id":21,"delta":-2},
                      {"kind":"resource_delta","resource_id":22,"delta":-1},
                      {"kind":"resource_delta","source":"arena","resource_id":21,"delta":-1}):
        action["semantic_predicates"]=[predicate]
        assert authorize_action(action,trace,config)=="GOAL_BLOCKED:COST_PREDICATE_MISMATCH"
    action["semantic_predicates"]=[{"kind":"resource_delta","source":"player","resource_id":21,"delta":-1}]
    assert authorize_action(action,trace,config) is None
    assert action["enabled"] is False
    assert CFG["planner"]["arena"]["allow_test_battle_start"] is False
