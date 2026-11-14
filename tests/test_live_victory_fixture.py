"""Sanitized synthetic regression based on observed deltas, not raw snapshots."""
from dataclasses import replace
from types import SimpleNamespace
from struct import pack
from invokers_bot.arena_model import parse_arena_snapshot
from invokers_bot.account_state import AccountState,Observation
from invokers_bot.arena_attempt import create_attempt,AttemptReconciliation,AttemptObservation
from invokers_bot.arena_outcome import capture,Outcome,finished_opponent_added
from test_arena_model import root,obj,envelope,opponent
from test_arena_outcome import raw_stats

def fixture():
    s=root()
    s[0]=pack("<i",534)
    s[10]=obj(raw_stats())
    history=b"".join(opponent("synthetic",i) for i in range(3,26))
    s[15]=pack("<i",23)+history
    before=parse_arena_snapshot(envelope(obj(s)))
    s[0]=pack("<i",543)
    stats=raw_stats()
    for i in (8,9,14,15):
        stats[i]=pack("<i",14)
    stats[13]=pack("<iiiii",2,11,22,12,2)
    s[10]=obj(stats)
    s[15]=pack("<i",24)+history+opponent("same",1)
    after=replace(parse_arena_snapshot(envelope(obj(s))),version=4)
    def state(a,post):
        p=SimpleNamespace(version=2 if post else 1,resources={21:11 if post else 12,22:150 if post else 100,23:1 if post else 0},resources_spent={21:1 if post else 0})
        t=11 if post else 10
        return AccountState({"arena":Observation(a,None,"post-a" if post else "pre-a",t),
                             "player":Observation(p,None,"post-p" if post else "pre-p",t)},frozenset())
    return state(before,False),state(after,True)

def test_live_victory():
    pre,post=fixture()
    c=create_attempt(pre,"01"*16,expected_token_cost=1,now=10)
    r=AttemptReconciliation(c);r.mark_started(pre,now=10)
    sample=capture(post,now=11)
    result=r.observe(AttemptObservation(c.attempt_id,sample,"victory"))
    assert result.outcome==Outcome.WIN_CONFIRMED
    e=result.result.evidence
    assert (e.token_delta,e.coin_delta,e.points_delta,e.offense_battles_delta,e.offense_wins_delta)==(-1,50,9,1,1)
    assert e.exact_token_spend and e.finished_added and not result.result.replay_allowed
    assert sample.stats.attack_battles_this_week==sample.stats.attack_wins_this_week==14
    assert post.sources["player"].model.resources[23]-pre.sources["player"].model.resources[23]==1
    assert post.sources["player"].model.resources_spent[21]-pre.sources["player"].model.resources_spent[21]==1
    assert not finished_opponent_added(c.baseline,sample,"02"*16)
    assert r.observe(AttemptObservation(c.attempt_id,replace(sample,observed_at=12))) is result
