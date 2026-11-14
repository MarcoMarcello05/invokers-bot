from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace
from collections.abc import Mapping
import pytest
from invokers_bot.arena_finished import parse_finished_opponent
from invokers_bot.arena_attempt import create_attempt,AttemptReconciliation,AttemptObservation,TerminalRecord
from invokers_bot.arena_outcome import Outcome,capture,finished_opponent_added
from invokers_bot.account_state import AccountState,Observation
from invokers_bot.snapshot_envelope import SnapshotFormatError
from test_arena_model import root,obj,envelope,opponent
from invokers_bot.arena_model import parse_arena_snapshot
from struct import pack

def account():
    s=root()
    s[15]=pack("<i",0)
    arena=parse_arena_snapshot(envelope(obj(s)))
    player=SimpleNamespace(version=1,resources={21:3,22:10})
    return AccountState({"arena":Observation(arena,None,"a",10),
                         "player":Observation(player,None,"p",10)},frozenset())

def test_finished_profile():
    entry=parse_finished_opponent(opponent("same",1))
    assert entry.identity=="01"*16
    assert entry.opponent.opaque_slots[2]==b"opaque"
    assert entry.opponent.combat_power==6151
    with pytest.raises(SnapshotFormatError):
        parse_finished_opponent(opponent("same",1)[:-1])

def test_identity():
    a=account();b=capture(a,now=10)
    assert not finished_opponent_added(b,replace(b,finished_ids=("02"*16,)),"01"*16)
    assert not finished_opponent_added(b,replace(b,finished_ids=("01"*16,)*2),"01"*16)
    assert finished_opponent_added(b,replace(b,finished_ids=("01"*16,)),"01"*16)

def test_immutable_and_stale():
    a=account();c=create_attempt(a,"01"*16,now=10)
    with pytest.raises(FrozenInstanceError):
        c.opponent_id="02"*16
    source=a.sources["arena"]
    changed=replace(source,model=replace(source.model,opponent_set_fingerprint="new"))
    with pytest.raises(ValueError,match="stale"):
        AttemptReconciliation(c).mark_started(AccountState({**a.sources,"arena":changed},frozenset()),now=10)

def test_attempt_terminal():
    a=account();c=create_attempt(a,"01"*16,expected_token_cost=1,now=10)
    r=AttemptReconciliation(c);r.mark_started(a,now=10)
    b=c.baseline
    stats=replace(b.stats,total_offense_battles=1,total_offense_wins=1)
    post=replace(b,observed_at=11,arena_digest="new-list",arena_version=4,
                 player_digest="new-player",player_version=2,stats=stats,tokens=2,finished_ids=("01"*16,))
    with pytest.raises(ValueError,match="wrong attempt"):
        r.observe(AttemptObservation("other",post,"victory"))
    assert r.observe(AttemptObservation(c.attempt_id,b,"victory")) is None
    record=r.observe(AttemptObservation(c.attempt_id,post,"victory"))
    assert isinstance(record,TerminalRecord) and record.outcome==Outcome.WIN_CONFIRMED
    assert record.opponent_id==c.opponent_id and not record.result.replay_allowed
    assert r.observe(AttemptObservation(c.attempt_id,post,"defeat")) is record

def test_ambiguous_pending():
    a=account();c=create_attempt(a,"01"*16,expected_token_cost=1,now=10)
    r=AttemptReconciliation(c);r.mark_started(a,now=10)
    b=c.baseline
    post=replace(b,observed_at=11,arena_digest="b",arena_version=4,player_digest="q",
         player_version=2,tokens=2,stats=replace(b.stats,total_offense_battles=1),
         finished_ids=("01"*16,)*2)
    result=r.observe(AttemptObservation(c.attempt_id,post))
    assert result.pending and result.outcome==Outcome.BATTLE_COMPLETED_RESULT_UNKNOWN

def test_no_raw_baseline():
    a=account();c=create_attempt(a,"01"*16,now=10)
    assert not c.baseline.stats.opaque_slots
    assert c.expected_token_cost is None
