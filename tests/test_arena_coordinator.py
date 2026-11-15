"""Shadow-only tests, no real game input. Loss fixture is not live validated."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from invokers_bot.arena_coordinator import ArenaRunCoordinator,Phase
from invokers_bot.arena_authorization import ArenaTokenPolicy
from invokers_bot.arena_ranking import OwnPower,PowerSource,RankingPolicy
from invokers_bot.arena_attempt import AttemptObservation
from invokers_bot.arena_outcome import capture,Outcome
from invokers_bot.arena_traversal import Inventory
from invokers_bot.account_state import AccountState
from test_live_victory_fixture import fixture


def inputs():
    pre,post=fixture()
    a=pre.sources["arena"]
    pre=AccountState({**pre.sources,"heroes":a,"relics":a},frozenset())
    ctx=tuple((n,pre.sources[n].digest,pre.sources[n].model.version) for n in ("arena","heroes","relics"))
    power=OwnPower(9368,PowerSource.PREBATTLE_NUMERIC_ROI,10,"synthetic",None,1,True,True,ctx)
    inv=Inventory("synthetic",a.digest,a.model.version,2,(),(),2,0,"COUNT_REACHED")
    return pre,post,inv,power,ArenaTokenPolicy(),RankingPolicy()


def prepared():
    pre,post,inv,power,p,r=inputs()
    c=ArenaRunCoordinator()
    assert c.prepare(pre,inv,power,p,r,now=10)==Phase.PREPARED
    return c,pre,post,power,p,r


def window():
    c,pre,post,power,p,r=prepared()
    i=c.begin_observation_window(pre,c.auth.candidate,power,p,r,now=10)
    assert i.resource_delta==-1 and not i.retry_allowed
    return c,pre,post,i


@pytest.mark.parametrize("win",[True,False])
def test_end_to_end(win):
    c,pre,post,i=window()
    assert c.observe_start(i.attempt_id,pre,visual_battle=True,now=11)==Phase.BATTLE_RUNNING
    assert not c.spend_confirmed
    assert c.tick(now=16)==Phase.BATTLE_RUNNING
    sample=capture(post,now=11)
    if not win:
        sample=replace(sample,stats=replace(sample.stats,total_offense_wins=13,attack_wins_this_week=13),
                       points=534,coins=100)
    record=c.observe_result(AttemptObservation(i.attempt_id,replace(sample,observed_at=20),"victory" if win else "defeat"))
    assert record.outcome==(Outcome.WIN_CONFIRMED if win else Outcome.LOSS_CONFIRMED)
    assert record.opponent_id==i.opponent_id and c.phase==Phase.TERMINAL
    assert c.observe_result(AttemptObservation(i.attempt_id,replace(sample,observed_at=21))) is record
    assert not c.retry_allowed and not record.result.replay_allowed


def test_stale_arena():
    pre,post,inv,power,p,r=inputs()
    assert ArenaRunCoordinator().prepare(pre,inv,power,p,r,now=13)==Phase.BLOCKED


@pytest.mark.parametrize("kind",["fingerprint","power","token","policy","candidate"])
def test_invalidation(kind):
    c,pre,post,power,p,r=prepared()
    target=c.auth.candidate
    if kind=="fingerprint":
        a=pre.sources["arena"]
        pre=AccountState({**pre.sources,"arena":replace(a,model=replace(a.model,opponent_set_fingerprint="new"))},frozenset())
    elif kind=="power":
        power=replace(power,validated=False)
    elif kind=="token":
        pre=AccountState({**pre.sources,"player":post.sources["player"]},frozenset())
    elif kind=="policy":
        p=replace(p,policy_version="changed")
    else:
        target=replace(target,fingerprint="wrong")
    assert c.begin_observation_window(pre,target,power,p,r,now=10) is None
    assert c.phase==Phase.BLOCKED and c.intent is None


def test_visual_only_then_spend():
    c,pre,post,i=window()
    assert c.observe_start(i.attempt_id,pre,visual_battle=True,now=10.5)==Phase.BATTLE_RUNNING
    assert c.observe_start(i.attempt_id,post,now=11)==Phase.BATTLE_RUNNING


def test_spend_only_then_visual():
    c,pre,post,i=window()
    assert c.observe_start(i.attempt_id,post,now=11)==Phase.START_OBSERVED
    assert c.observe_start(i.attempt_id,post,visual_battle=True,now=11.5)==Phase.BATTLE_RUNNING


def test_wrong_delta():
    c,pre,post,i=window()
    item=post.sources["player"]
    bad=AccountState({**post.sources,"player":replace(item,model=SimpleNamespace(version=2,resources={21:10}))},frozenset())
    assert c.observe_start(i.attempt_id,bad,visual_battle=True,now=11)==Phase.TERMINAL
    assert c.record.outcome==Outcome.CONFLICTED


def test_deadline():
    c,pre,post,i=window()
    assert c.tick(now=15)==Phase.START_UNRESOLVED and not c.retry_allowed
    assert c.record is None
    with pytest.raises(ValueError):
        c.prepare(pre,None,None,now=15)
    assert c.observe_start(i.attempt_id,pre,visual_battle=True,now=16)==Phase.BATTLE_RUNNING


@pytest.mark.parametrize("started",[False,True])
def test_cancel(started):
    if started:
        c,pre,post,i=window()
        c.observe_start(i.attempt_id,post,visual_battle=True,now=11)
    else:
        c,pre,post,power,p,r=prepared()
    assert c.cancel(now=12)==Phase.CANCELLED
    with pytest.raises(ValueError):
        c.prepare(pre,None,None,now=12)
    assert not c.retry_allowed


def test_wrong_id_and_single_attempt():
    c,pre,post,i=window()
    assert c.observe_start("bad",post,now=11)=="WRONG_ATTEMPT"
    with pytest.raises(ValueError):
        c.prepare(pre,None,None,now=11)


def test_result_timeout():
    c,pre,post,i=window()
    c.observe_start(i.attempt_id,post,visual_battle=True,now=11)
    assert c.tick(now=75)==Phase.TERMINAL and c.record.outcome==Outcome.INCONCLUSIVE


def test_refresh_after_start():
    c,pre,post,i=window()
    c.observe_start(i.attempt_id,post,visual_battle=True,now=11)
    sample=replace(capture(post,now=11),observed_at=12,arena_digest="refreshed")
    record=c.observe_result(AttemptObservation(i.attempt_id,sample,"victory"))
    assert record.opponent_id==i.opponent_id and record.attempt_id==i.attempt_id


@pytest.mark.parametrize("wallet,spent,expected",[(12,1,Outcome.WIN_CONFIRMED),(11,2,Outcome.CONFLICTED),(10,1,Outcome.CONFLICTED)])
def test_counter_preferred(wallet,spent,expected):
    c,pre,post,i=window()
    c.observe_start(i.attempt_id,pre,visual_battle=True,now=11)
    c.tick(now=16)
    sample=replace(capture(post,now=11),observed_at=20,tokens=wallet,tokens_spent=spent)
    record=c.observe_result(AttemptObservation(i.attempt_id,sample,"victory"))
    assert record.outcome==expected
    if expected==Outcome.WIN_CONFIRMED:
        assert record.result.evidence.spend_source=="RESOURCES_SPENT"


def test_visual_result_without_spend_pending():
    c,pre,post,i=window()
    c.observe_start(i.attempt_id,pre,visual_battle=True,now=11)
    sample=replace(capture(post,now=11),observed_at=20,tokens=12,tokens_spent=0)
    result=c.observe_result(AttemptObservation(i.attempt_id,sample,"victory"))
    assert result.pending and c.phase==Phase.RESULT_PENDING
    assert c.tick(now=75)==Phase.TERMINAL
    assert c.record.outcome==Outcome.INCONCLUSIVE and not c.record.result.replay_allowed


def test_no_start_evidence_final_timeout():
    c,pre,post,i=window()
    assert c.tick(now=15)==Phase.START_UNRESOLVED
    assert c.tick(now=75)==Phase.TERMINAL
    assert c.record.attempt_id==i.attempt_id and c.record.opponent_id==i.opponent_id
    assert c.record.outcome==Outcome.INCONCLUSIVE


def test_late_wrong_stale():
    c,pre,post,i=window()
    c.observe_start(i.attempt_id,pre,visual_battle=True,now=11)
    sample=capture(post,now=11)
    assert c.observe_result(AttemptObservation("other",sample,"victory"))=="WRONG_ATTEMPT"
    assert c.observe_result(AttemptObservation(i.attempt_id,replace(sample,observed_at=9),"victory"))=="IGNORED_STALE"
    assert c.phase==Phase.BATTLE_RUNNING


@pytest.mark.parametrize("kind,reason",[(None,"TRAVERSAL_MISSING"),("digest","TRAVERSAL_DIGEST_MISMATCH"),("version","TRAVERSAL_VERSION_MISMATCH"),("reason","TRAVERSAL_INCOMPLETE"),("unique_count","TRAVERSAL_COUNT_MISMATCH")])
def test_traversal_diagnostics(kind,reason):
    pre,post,inv,power,p,r=inputs()
    if kind is None:
        inv=None
    else:
        inv=replace(inv,**{kind:{"digest":"wrong","version":99,"reason":"TIMEOUT","unique_count":1}[kind]})
    c=ArenaRunCoordinator()
    assert c.prepare(pre,inv,power,p,r,now=10)==Phase.NEED_TRAVERSAL
    assert c.reason==reason


# Liveness hardening: continuously observed state, not predicted duration.
@pytest.mark.parametrize("duration",[61,95,240])
def test_long_battle_liveness(duration):
    c,pre,post,i=window()
    for now in range(11,10+duration+1,15):
        assert c.observe_start(i.attempt_id,pre,visual_battle=True,now=now)==Phase.BATTLE_RUNNING
        assert c.last_progress_at==now
    assert c.tick(now=10+duration)==Phase.BATTLE_RUNNING
    assert c.record is None and not c.retry_allowed
    assert c.hard_deadline==310
    with pytest.raises(ValueError):
        c.prepare(pre,None,None,now=10+duration)

@pytest.mark.parametrize("win",[True,False])
def test_late_result_before_hard_cap(win):
    c,pre,post,i=window()
    for now in range(11,290,20):
        assert c.observe_start(i.attempt_id,pre,visual_battle=True,now=now)==Phase.BATTLE_RUNNING
    sample=replace(capture(post,now=11),observed_at=309)
    if not win:
        sample=replace(sample,stats=replace(sample.stats,total_offense_wins=13,attack_wins_this_week=13))
    record=c.observe_result(AttemptObservation(i.attempt_id,sample,"victory" if win else "defeat"))
    assert record.outcome==(Outcome.WIN_CONFIRMED if win else Outcome.LOSS_CONFIRMED)

def test_hard_cap_cannot_be_extended():
    c,pre,post,i=window()
    for now in range(11,310,20):
        c.observe_start(i.attempt_id,pre,visual_battle=True,now=now)
    assert c.observe_start(i.attempt_id,pre,visual_battle=True,now=310)==Phase.TERMINAL
    assert c.record.outcome==Outcome.INCONCLUSIVE and c.record.recovery_required
    assert c.record.result.reason=="RECOVERY_REQUIRED_HARD_TIMEOUT"
    assert not c.record.retry_allowed and c.recovery_required
    with pytest.raises(ValueError):
        c.prepare(pre,None,None,now=311)

def test_no_progress_and_stale_events():
    c,pre,post,i=window()
    c.observe_start(i.attempt_id,pre,visual_battle=True,now=11)
    assert c.tick(now=50)==Phase.BATTLE_RUNNING
    assert c.observe_start("other",pre,visual_battle=True,now=60)=="WRONG_ATTEMPT"
    assert c.observe_start(i.attempt_id,pre,visual_battle=True,now=49)=="IGNORED_STALE"
    assert c.observe_start(i.attempt_id,pre,now=65)==Phase.BATTLE_RUNNING
    assert c.last_progress_at==11
    assert c.tick(now=71)==Phase.TERMINAL
    assert c.record.result.reason=="RECOVERY_REQUIRED_NO_PROGRESS"
    assert c.record.recovery_required and not c.record.retry_allowed

def test_semantic_progress_is_not_repeated():
    c,pre,post,i=window()
    c.observe_start(i.attempt_id,pre,visual_battle=True,now=11)
    # Fresh real semantic spend evidence, without a battle visual.
    player=replace(post.sources["player"],checked_at=50)
    changed=AccountState({**pre.sources,"player":player},frozenset())
    c.observe_start(i.attempt_id,changed,now=50)
    assert c.last_progress_at==50
    changed=AccountState({**pre.sources,"player":replace(player,checked_at=90)},frozenset())
    c.observe_start(i.attempt_id,changed,now=90)
    assert c.last_progress_at==50
    assert c.tick(now=110)==Phase.TERMINAL

def test_result_visual_progress_once():
    c,pre,post,i=window()
    c.observe_start(i.attempt_id,pre,visual_battle=True,now=11)
    sample=replace(capture(post,now=11),observed_at=55,tokens=12,tokens_spent=0)
    assert c.observe_result(AttemptObservation(i.attempt_id,sample,"victory")).pending
    assert c.last_progress_at==55
    assert c.observe_result(AttemptObservation(i.attempt_id,replace(sample,observed_at=90),"victory")).pending
    assert c.last_progress_at==55
    assert c.tick(now=115)==Phase.TERMINAL

def test_custom_liveness_bounds():
    c=ArenaRunCoordinator(start_timeout=3,stagnation_timeout=90,hard_timeout=400)
    assert c.stagnation_timeout==90 and c.hard_timeout==400
    with pytest.raises(ValueError):
        ArenaRunCoordinator(stagnation_timeout=90,hard_timeout=80)
