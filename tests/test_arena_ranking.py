from dataclasses import replace
from types import SimpleNamespace
import time
import numpy as np
import pytest
from invokers_bot.arena_ranking import *
from invokers_bot.own_power_probe import numeric_roi,manual_probe_sample
from invokers_bot.account_state import AccountState,Observation
from invokers_bot.arena_opponent import parse_opponent
from test_arena_model import opponent
from pathlib import Path
import json


def setup():
    now=time.monotonic()
    opponents=tuple(parse_opponent(opponent("same",i,p)) for i,p in ((2,6000),(1,6000),(3,4000)))
    arena=SimpleNamespace(version=3,current_opponents=opponents,opponent_set_fingerprint="fp")
    account=AccountState({n:Observation(arena,None,n,now) for n in ("arena","heroes","relics")},frozenset())
    power=OwnPower(8000,PowerSource.STRUCTURED_LAST_META_BATTLE_SETUP,now,"battle",5,1.0,True,True,team_context(account))
    return account,power


def test_exact_rank():
    account,power=setup()
    result=rank(account,power)
    assert [c.player_id for c in result.candidates]==["03"*16,"01"*16,"02"*16]
    assert result.selected.power_ratio==Fraction(1,2)
    assert not result.fight_authorized


@pytest.mark.parametrize("change",[{"value":None},{"source":PowerSource.UNKNOWN},{"exact":False},{"validated":False},{"confidence":.99},{"digest":None},{"version":None},{"observed_at":-1000000000},{"context":()}])
def test_unusable(change):
    account,power=setup()
    result=rank(account,replace(power,**change))
    assert result.selected is None and not result.fight_authorized


def test_policy():
    account,power=setup()
    assert rank(account,power,RankingPolicy(max_power_ratio=.4)).selected is None
    assert rank(account,power,RankingPolicy(minimum_candidates=4)).selected is None
    result=rank(account,power,RankingPolicy(prefer_lower_power=False,points_bound=10))
    assert result.selected.player_id=="01"*16 and result.selected.points_component==1


def test_stale():
    account,power=setup()
    assert rank(account,power,now=power.observed_at+10).reason=="ARENA_STALE"


def test_invalidation():
    account,power=setup()
    facts={"arena_own_power":power}
    update_ranking(facts,account,{})
    old=facts["arena_selected_target"]
    update_ranking(facts,account,{"planner":{"arena_ranking":{"version":"next"}}})
    assert facts["arena_selected_target"].policy.version=="next"
    assert facts["arena_selected_target"]!=old
    facts["arena_own_power"]=replace(power,version=6)
    update_ranking(facts,account,{})
    assert facts["arena_selected_target"].power.version==6
    source=account.sources["arena"]
    new=replace(source,digest="changed",model=SimpleNamespace(version=4,current_opponents=(),opponent_set_fingerprint="new"))
    update_ranking(facts,AccountState({**account.sources,"arena":new},frozenset()),{})
    assert "arena_selected_target" not in facts


def test_roi_only_diagnostic():
    frame=np.zeros((100,200,3),dtype=np.uint8)
    def reader(crop):
        assert crop.shape==(10,40,3)
        return "9368",1.0
    p=numeric_roi(frame,(.1,.1,.3,.2),reader)
    assert p.value==9368 and not p.exact and not p.validated
    assert manual_probe_sample({},frame,"arena_list",{"enabled":True},reader) is None
    with pytest.raises(ValueError):
        numeric_roi(frame,(0,0,1,1),reader)
    assert numeric_roi(frame,(.1,.1,.3,.2),lambda c:("9?68",1)).value is None


def test_start_disabled():
    cfg=json.loads((Path(__file__).resolve().parents[1]/"config"/"arena.json").read_text())
    assert cfg["flows"]["formation"]["actions"][0]["enabled"] is False
    assert not cfg["planner"]["arena"]["allow_test_battle_start"]
