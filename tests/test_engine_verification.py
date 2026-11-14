"""Runtime verification tests, no live window or input."""
from types import SimpleNamespace
import pytest

from invokers_bot import engine
from invokers_bot.action_verification import ActionExpectation
from invokers_bot.models import GameState
from invokers_bot.world_state import WorldState


@pytest.fixture
def bot(monkeypatch):
    instance = engine.BotEngine.__new__(engine.BotEngine)
    instance.account_observer = None
    instance.world_state = WorldState()
    instance.config = SimpleNamespace(stable_frames=2, flows={})
    instance.live = True
    monkeypatch.setattr(engine, "f12_pressed", lambda: False)
    return instance


def test_timeout(bot, monkeypatch):
    bot._observe = lambda: (None,None,None,GameState.MAIN)
    exp = ActionExpectation.from_action({"verification_timeout":0.1})
    ticks = iter([0.,0.,0.2])
    monkeypatch.setattr(engine.time, "monotonic", lambda: next(ticks))
    result = bot._verify_action(GameState.MAIN, exp, None)
    assert not result.success and result.reason.startswith("TIMEOUT:")


def test_stable_visual_success(bot):
    calls = []
    bot._observe = lambda: (calls.append(1),None,None,GameState.ARENA_LIST)
    exp = ActionExpectation.from_action({"expect":["arena_list"],"verification_timeout":1})
    result = bot._verify_action(GameState.MAIN, exp, None)
    assert result.success and result.visual_verified and len(calls) == 2


def test_missing_baseline_blocks_before_input(bot):
    bot._perform = lambda *args: pytest.fail("input must not run")
    result = bot._execute_live_action({
        "invalidates_sources":["player"],"expects_source_change":["player"],
        "success_mode":"STRUCTURED_ONLY",
    }, GameState.MAIN, None, None)
    assert not result.success and result.reason == "BASELINE_UNAVAILABLE"


def test_input_not_sent(bot):
    bot._perform = lambda *args: False
    bot._verify_action = lambda *args: pytest.fail("verification must not run")
    result = bot._execute_live_action({"type":"key"}, GameState.MAIN, None, None)
    assert not result.success and result.reason == "INPUT_NOT_SENT"


def test_failure_stops_action_chain(bot):
    bot.config.flows={"main":{"actions":[{"type":"key"},{"type":"key"}]}}
    calls=[]
    bot._perform=lambda *args: calls.append(1) or False
    result=bot._handle(GameState.MAIN,None,None,None)
    assert not result.success and calls == [1]
    assert bot.world_state.facts["last_action_result"] == result


def test_cancel_during_verification(bot, monkeypatch):
    monkeypatch.setattr(engine,"f12_pressed",lambda: True)
    bot._observe=lambda: pytest.fail("no observation after cancel")
    result=bot._verify_action(GameState.MAIN,ActionExpectation.from_action({}),None)
    assert not result.success and result.reason == "CANCELLED"
