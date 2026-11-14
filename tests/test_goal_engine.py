from types import SimpleNamespace
from pathlib import Path
import json
import pytest
from invokers_bot import engine
from invokers_bot.models import GameState
from invokers_bot.world_state import WorldState


@pytest.mark.parametrize("screen", ["main","arena_list","formation"])
def test_blocked_goal_never_sends_input(monkeypatch,screen):
    raw=json.loads((Path(__file__).resolve().parents[1]/"config"/"arena.json").read_text())
    bot=engine.BotEngine.__new__(engine.BotEngine)
    bot.config=SimpleNamespace(raw=raw)
    bot.account_observer=None
    bot.world_state=WorldState()
    bot._perform=lambda *args: pytest.fail("blocked action sent input")
    monkeypatch.setattr(engine,"f12_pressed",lambda:False)
    result=bot._execute_live_action(raw["flows"][screen]["actions"][0],GameState(screen),None,None)
    assert not result.success and result.reason=="GOAL_BLOCKED"
    assert bot.world_state.facts["decision_trace"].selected is None
