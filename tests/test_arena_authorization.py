from dataclasses import replace,FrozenInstanceError
from types import SimpleNamespace
import pytest
from invokers_bot.arena_authorization import *
from invokers_bot.arena_ranking import OwnPower
from invokers_bot.account_state import AccountState
from test_arena_attempt import account

def setup(tokens=3):
    a=account()
    p=replace(a.sources["player"],model=SimpleNamespace(version=1,resources={21:tokens,22:10}))
    a=AccountState({**a.sources,"player":p,"heroes":a.sources["arena"],"relics":a.sources["arena"]},frozenset())
    ctx=tuple((n,a.sources[n].digest,a.sources[n].model.version) for n in ("arena","heroes","relics"))
    power=OwnPower(10000,PowerSource.STRUCTURED_LAST_META_BATTLE_SETUP,10,"battle",1,1,True,True,ctx)
    rp=RankingPolicy()
    c=rank(a,power,rp,now=10,context=ctx).selected
    return a,c,power,rp

@pytest.mark.parametrize("value,expected",[(10,TokenPressure.AT_CAP),(11,TokenPressure.AT_CAP),(8,TokenPressure.HIGH),(7,TokenPressure.NORMAL),(None,TokenPressure.UNKNOWN),(-1,TokenPressure.UNKNOWN)])
def test_pressure(value,expected):
    assert pressure(value)==expected

@pytest.mark.parametrize("cost,reserve,tokens,reason",[(None,0,10,"BLOCK_TOKEN_COST_UNKNOWN"),(4,0,3,"BLOCK_INSUFFICIENT_TOKENS"),(2,2,3,"BLOCK_RESERVE")])
def test_budget(cost,reserve,tokens,reason):
    a,c,p,r=setup(tokens)
    auth=authorize(a,c,p,ArenaTokenPolicy(expected_battle_cost=cost,reserve=reserve),r,now=10)
    assert not auth.allowed and auth.attempt is None and auth.reason==reason

def test_allow_and_stale():
    a,c,p,r=setup()
    policy=ArenaTokenPolicy(expected_battle_cost=1)
    auth=authorize(a,c,p,policy,r,now=10)
    assert auth.allowed and auth.attempt_id and not auth.fight_authorized
    assert auth.attempt.expected_token_cost==1 and auth.resulting_balance==2
    with pytest.raises(FrozenInstanceError):
        auth.allowed=False
    assert still_valid(auth,a,c,p,policy,r,now=10)
    assert not still_valid(auth,a,c,p,replace(policy,policy_version="next"),r,now=10)
    assert not still_valid(auth,a,c,p,policy,r,now=13)
    assert authorize(a,replace(c,fingerprint="wrong"),p,policy,r,now=10).reason=="BLOCK_TARGET_STALE"
    assert authorize(a,c,replace(p,validated=False),policy,r,now=10).reason=="BLOCK_OWN_POWER_UNKNOWN"

def test_spend():
    a,c,p,r=setup()
    auth=authorize(a,c,p,ArenaTokenPolicy(expected_battle_cost=1),r,now=10)
    assert spend_expectation(auth)["semantic_predicates"][0]["delta"]==-1
    assert verify_spend(auth,a,visual_battle=True,now=10).status=="PENDING"
    assert not verify_spend(auth,a,visual_battle=True,now=10).retry_allowed
    player=replace(a.sources["player"],digest="changed",model=SimpleNamespace(version=2,resources={21:2}))
    b=AccountState({**a.sources,"player":player},frozenset())
    assert verify_spend(auth,b,now=11).status=="PENDING"
    assert verify_spend(auth,b,visual_battle=True,now=11).status=="CONFIRMED"
    assert verify_spend(auth,b,visual_battle=True,now=16).status=="INCONCLUSIVE"
    assert not still_valid(auth,b,c,p,auth.policy,r,now=11)

def test_policy_invalid():
    assert from_config({})==(None,"BLOCK_POLICY")
    with pytest.raises(ValueError):
        ArenaTokenPolicy(expected_battle_cost=0)

def test_stale_token():
    a,c,p,r=setup()
    a=AccountState({**a.sources,"player":replace(a.sources["player"],checked_at=0)},frozenset())
    auth=authorize(a,c,p,ArenaTokenPolicy(expected_battle_cost=1),r,now=10)
    assert auth.reason=="BLOCK_TOKEN_BALANCE_STALE" and auth.pressure==TokenPressure.UNKNOWN
