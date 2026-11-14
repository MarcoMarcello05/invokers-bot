"""Action-scoped evidence, including the actual observer on synthetic files."""
from types import SimpleNamespace

import pytest

import invokers_bot.account_state as module
from invokers_bot.action_verification import ActionExpectation, evaluate, baseline_valid
from invokers_bot.models import GameState

MAIN, ARENA, UNKNOWN = GameState.MAIN, GameState.ARENA_LIST, GameState.UNKNOWN


@pytest.fixture
def observer(tmp_path, monkeypatch):
    def parse(data):
        if data == b"bad":
            raise module.SnapshotFormatError("invalid")
        return SimpleNamespace(version=int(data), resources={2:int(data)})
    monkeypatch.setattr(module, "parse_snapshot", parse)
    monkeypatch.setattr(module, "_SOURCES", {
        name:(file,lambda value:value) for name,(file,_) in module._SOURCES.items()
    })
    for filename,_ in module._SOURCES.values():
        (tmp_path/filename).write_bytes(b"1")
    return module.AccountObserver(tmp_path), tmp_path


def contract(sources=(), mode="VISUAL_ONLY", changed=()):
    return ActionExpectation.from_action({
        "invalidates_sources": list(sources), "expects_source_change": list(changed),
        "success_mode": mode, "expects_visual_transition": mode != "STRUCTURED_ONLY",
        "expected_visual_states": [] if mode == "STRUCTURED_ONLY" else ["arena_list"],
    })


def update(root, name, value):
    (root/module._SOURCES[name][0]).write_bytes(value)


def test_navigation_no_invalidation(observer):
    obs, root = observer
    exp = contract()
    before = obs.refresh(force=True)
    obs.invalidate(exp.invalidates_sources)
    after = obs.refresh(force=True, sources=exp.invalidates_sources)
    assert evaluate(exp, MAIN, ARENA, before, after).success
    assert all(after.get_fresh(name) is not None for name in module._SOURCES)
    assert all(p.read_bytes() == b"1" for p in root.iterdir())


@pytest.mark.parametrize("sources", [("player",), ("heroes","relics")])
def test_scoped_invalidation(observer, sources):
    obs, root = observer
    obs.refresh(force=True)
    exp = contract(sources, "STRUCTURED_ONLY", sources)
    before = obs.refresh(force=True, sources=exp.invalidates_sources)
    obs.invalidate(exp.invalidates_sources)
    after = obs.refresh(force=True, sources=exp.invalidates_sources)
    for name in module._SOURCES:
        assert (after.get_fresh(name) is None) == (name in sources)
    for name in sources:
        update(root,name,b"2")
    current = obs.refresh(force=True, sources=exp.invalidates_sources)
    assert evaluate(exp, MAIN, UNKNOWN, before, current).success


@pytest.mark.parametrize("mode,visual,changed,success", [
    ("VISUAL_ONLY",True,False,True),
    ("VISUAL_ONLY",False,False,False),
    ("STRUCTURED_ONLY",False,True,True),
    ("STRUCTURED_ONLY",True,False,False),
    ("VISUAL_AND_STRUCTURED",True,True,True),
    ("VISUAL_AND_STRUCTURED",True,False,False),
    ("VISUAL_AND_STRUCTURED",False,True,False),
    ("VISUAL_OR_STRUCTURED",True,False,True),
    ("VISUAL_OR_STRUCTURED",False,True,True),
    ("VISUAL_OR_STRUCTURED",False,False,False),
])
def test_modes(observer, mode, visual, changed, success):
    obs, root = observer
    names = [] if mode == "VISUAL_ONLY" else ["player"]
    exp = contract(names, mode, names)
    before = obs.refresh(force=True)
    obs.invalidate(exp.invalidates_sources)
    if changed:
        update(root,"player",b"2")
    current = obs.refresh(force=True, sources=exp.invalidates_sources)
    assert evaluate(exp, MAIN, ARENA if visual else MAIN, before, current).success is success


def test_all_expected_sources_required(observer):
    obs, root = observer
    exp = contract(["heroes","relics"], "STRUCTURED_ONLY", ["heroes","relics"])
    before = obs.refresh(force=True)
    obs.invalidate(exp.invalidates_sources)
    update(root,"heroes",b"2")
    result = evaluate(exp, MAIN, UNKNOWN, before, obs.refresh(force=True))
    assert not result.success and result.changed_sources == {"heroes"}


@pytest.mark.parametrize("mode", ["STRUCTURED_ONLY","VISUAL_AND_STRUCTURED","VISUAL_OR_STRUCTURED"])
def test_corrupt_source_cannot_verify(observer, mode):
    obs, root = observer
    exp = contract(["player"], mode, ["player"])
    before = obs.refresh(force=True)
    obs.invalidate(exp.invalidates_sources)
    update(root,"player",b"bad")
    result = evaluate(exp, MAIN, ARENA, before, obs.refresh(force=True))
    assert not result.success and result.reason == "SOURCE_UNAVAILABLE:player"


def test_visual_release_only_optional_and_not_preexisting(observer):
    obs, _ = observer
    obs.refresh(force=True)
    obs.invalidate({"heroes"})
    exp = contract(["heroes","player"])
    before = obs.refresh(force=True, sources=exp.invalidates_sources)
    obs.invalidate(exp.invalidates_sources)
    current = obs.refresh(force=True, sources=exp.invalidates_sources)
    assert evaluate(exp, MAIN, ARENA, before, current).success
    after = obs.release_visual_only(exp.invalidates_sources, before)
    assert after.player is not None and after.heroes is None and after.relics is not None


def test_timestamp_only_not_proof(observer):
    obs, root = observer
    exp = contract(["player"], "STRUCTURED_ONLY", ["player"])
    before = obs.refresh(force=True)
    obs.invalidate(exp.invalidates_sources)
    update(root,"player",b"1")
    assert not evaluate(exp, MAIN, UNKNOWN, before, obs.refresh(force=True)).success


def test_legacy_visual_only():
    exp = ActionExpectation.from_action({"type":"key","key":"esc","wait_for_transition":False})
    assert exp.legacy and not exp.invalidates_sources
    assert not evaluate(exp, MAIN, MAIN, None, None).success
    assert not evaluate(exp, MAIN, UNKNOWN, None, None).success
    assert evaluate(exp, MAIN, ARENA, None, None).success


def test_visual_only_no_observer():
    exp = contract()
    assert evaluate(exp, MAIN, ARENA, None, None).success


@pytest.mark.parametrize("bad", [
    {"invalidates_sources":["not_a_source"]},
    {"expects_source_change":["player"]},
    {"success_mode":"STRUCTURED_ONLY"},
    {"verification_timeout":0},
    {"verification_timeout":float("nan")},
    {"expected_visual_states":["unknown"]},
    {"invalidates_sources":"player"},
    {"expects_visual_transition":False},
])
def test_invalid_contract(bad):
    with pytest.raises(ValueError):
        ActionExpectation.from_action(bad)


def test_no_baseline_blocks_structured(observer):
    obs, _ = observer
    exp = contract(["player"], "STRUCTURED_ONLY", ["player"])
    assert not baseline_valid(exp, None)
    assert not baseline_valid(exp, obs.state)
    assert baseline_valid(exp, obs.refresh(force=True))
    obs.invalidate({"player"})
    assert not baseline_valid(exp, obs.state)
