from types import SimpleNamespace
import pytest

import invokers_bot.account_state as module


@pytest.fixture
def observer(tmp_path, monkeypatch):
    def parse(data):
        if data == b"broken":
            raise module.SnapshotFormatError("invalid")
        return SimpleNamespace(version=int(data), resources={2:int(data)})
    monkeypatch.setattr(module, "parse_snapshot", parse)
    monkeypatch.setattr(module, "_SOURCES", {
        name:(file,lambda value:value) for name,(file,_) in module._SOURCES.items()
    })
    for filename,_ in module._SOURCES.values():
        (tmp_path/filename).write_bytes(b"1")
    return module.AccountObserver(tmp_path), tmp_path


def test_initial_and_change(observer):
    obs, root = observer
    initial = obs.refresh(force=True)
    assert initial.changed == {"player","heroes","relics","arena"}
    assert initial.resources == {2:1}
    assert initial.heroes.version == initial.relics.version == 1
    (root/"PlayerModel.dat").write_bytes(b"2")
    updated = obs.refresh(force=True)
    assert updated.changed == {"player"}
    assert updated.resources == {2:2}
    assert initial.resources == {2:1}


def test_invalidate_requires_new_content(observer):
    obs, root = observer
    obs.refresh(force=True)
    obs.invalidate()
    assert obs.refresh(force=True).resources is None
    (root/"PlayerModel.dat").write_bytes(b"2")
    state = obs.refresh(force=True)
    assert state.resources == {2:2}
    assert state.heroes is None


def test_bad_file_and_recovery(observer):
    obs, root = observer
    obs.refresh(force=True)
    path = root/"PlayerHeroesModel.dat"
    path.write_bytes(b"broken")
    state = obs.refresh(force=True)
    assert state.heroes is None
    assert state.sources["heroes"].model.version == 1
    assert state.sources["heroes"].error
    path.unlink()
    assert obs.refresh(force=True).heroes is None
    path.write_bytes(b"2")
    assert obs.refresh(force=True).heroes.version == 2


def test_throttle_and_read_only(observer):
    obs, root = observer
    first = obs.refresh()
    assert obs.refresh() is first
    assert all(p.read_bytes() == b"1" for p in root.iterdir())
    with pytest.raises(TypeError):
        first.sources["player"] = None


def test_freshness(observer):
    obs, _ = observer
    item = obs.refresh(force=True).sources["player"]
    assert item.fresh(1, item.checked_at)
    assert not item.fresh(1, item.checked_at+2)
