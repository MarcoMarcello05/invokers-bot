from dataclasses import replace
from struct import pack
import pytest
from invokers_bot.arena_stats import parse_arena_stats
from invokers_bot.arena_outcome import Sample,Reconciliation,Outcome,arena_token_spent_exactly,capture
from invokers_bot.snapshot_envelope import SnapshotFormatError
from test_arena_model import obj,root,envelope
from invokers_bot.arena_model import parse_arena_snapshot

def raw_stats():
    # Captured historical Windows profile, reconstructed without account bytes.
    return [b""]*4+[pack("<i",n) for n in (10,0,0,0,13,13,10,0,12)]+[
        pack("<iiiii",2,11,22,12,1)]+[pack("<i",n) for n in (13,13,0,0)]

def test_stats_profile():
    s=raw_stats()+[b"future"]
    stats=parse_arena_stats(obj(s))
    assert (stats.total_offense_battles,stats.total_offense_wins,stats.total_defense_battles)==(13,13,10)
    assert stats.league_accounting_matches and stats.opaque_slots[18]==b"future"
    r=root();r[10]=obj(s)
    assert parse_arena_snapshot(envelope(obj(r))).stats==stats

@pytest.mark.parametrize("index,value",[(8,b""),(9,pack("<i",14)),(10,pack("<i",-1)),(13,pack("<i",1)),(13,pack("<iiiii",2,11,1,11,2))])
def test_bad_stats(index,value):
    s=raw_stats();s[index]=value
    with pytest.raises(SnapshotFormatError):
        parse_arena_stats(obj(s))

def baseline():
    return Sample(10,"a",1,"p",1,parse_arena_stats(obj(raw_stats())),100,534,3,20,(),None)

def post(b,**kwargs):
    return replace(b,observed_at=11,arena_digest="b",arena_version=2,player_digest="q",player_version=2,**kwargs)

@pytest.mark.parametrize("win,visual,expected",[(1,"victory",Outcome.WIN_CONFIRMED),(0,"defeat",Outcome.LOSS_CONFIRMED),(0,"victory",Outcome.CONFLICTED)])
def test_counter_visual(win,visual,expected):
    b=baseline()
    s=replace(b.stats,total_offense_battles=14,total_offense_wins=13+win,attack_battles_this_week=14,attack_wins_this_week=13+win)
    result=Reconciliation(b,cost=1).observe(post(b,stats=s,tokens=2),visual=visual)
    assert result.outcome==expected and not result.replay_allowed

@pytest.mark.parametrize("changes,expected",[({"points":600},Outcome.INCONCLUSIVE),({"coins":50},Outcome.INCONCLUSIVE),({"tokens":2},Outcome.BATTLE_START_ONLY)])
def test_single_channel(changes,expected):
    b=baseline()
    assert Reconciliation(b,cost=1).observe(post(b,**changes)).outcome==expected

def test_pending_and_timeout():
    b=baseline();r=Reconciliation(b,timeout=5)
    a=r.observe(post(b),visual="victory")
    assert a.pending and a.outcome==Outcome.INCONCLUSIVE
    final=r.observe(replace(b,observed_at=16))
    assert not final.pending and final.outcome==Outcome.INCONCLUSIVE and not final.replay_allowed
    assert r.observe(post(b))==final

def test_defense_only():
    b=baseline()
    s=replace(b.stats,total_defense_battles=11,defense_battles_this_week=11)
    assert Reconciliation(b).observe(post(b,stats=s)).outcome==Outcome.INCONCLUSIVE

def test_week_reset():
    b=baseline()
    s=replace(b.stats,attack_battles_this_week=0,attack_wins_this_week=0)
    assert Reconciliation(b).observe(post(b,stats=s),visual="victory").outcome==Outcome.CONFLICTED

def test_exact_token():
    b=baseline();a=post(b,tokens=1)
    assert arena_token_spent_exactly(b,a,2)
    assert not arena_token_spent_exactly(b,a,1)
    assert not arena_token_spent_exactly(b,a,None)

def test_unknown_result():
    b=baseline()
    s=replace(b.stats,total_offense_battles=14)
    result=Reconciliation(b).observe(post(b,stats=s))
    assert result.outcome==Outcome.BATTLE_COMPLETED_RESULT_UNKNOWN and result.pending

def test_finished_and_spend_support():
    b=baseline();s=replace(b.stats,total_offense_battles=14,total_offense_wins=14)
    result=Reconciliation(b,identity="01"*16,cost=1).observe(post(b,stats=s,tokens=2,finished_ids=("01"*16,)))
    assert result.outcome==Outcome.WIN_CONFIRMED

def test_missing_sources():
    assert capture(None,now=10)==Sample(10)
