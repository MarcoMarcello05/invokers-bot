from __future__ import annotations
import os, time
from pathlib import Path

DEFAULT = Path(os.environ.get('LOCALAPPDATA','')) / 'Low' / 'Hit_Zone' / 'Invokers' / 'aggregate_snapshots' / 'PlayerArenaModel.dat'
# LOCALAPPDATA points AppData/Local; Unity LocalLow is its sibling.
def arena_path():
    p = DEFAULT
    if p.exists(): return p
    la = Path(os.environ.get('LOCALAPPDATA',''))
    p = la.parent / 'LocalLow' / 'Hit_Zone' / 'Invokers' / 'aggregate_snapshots' / 'PlayerArenaModel.dat'
    return p

def read_opponents(path:Path|None=None):
    """Read current opponents only, using the UI-correlated captured wire profile.

    Field 12 was matched to _SILVA00 / 6151 in the Windows comparison.
    The other stored collection must never enter actor candidate ranking.
    """
    from structured_state import read_arena_collections
    collections = read_arena_collections(path or arena_path())
    return next(c['records'] for c in collections if c['role'] == 'current')


def signature(items): return tuple(sorted((x['name'],x['level'],x['arena_points'],x['combat_power']) for x in items))

def wait_for_change(old_sig, timeout=8.0, poll=.25, path=None):
    end=time.time()+timeout
    while time.time()<end:
        try:
            items=read_opponents(path); sig=signature(items)
            if items and sig != old_sig: return items
        except Exception: pass
        time.sleep(poll)
    return None


class SnapshotError(ValueError):
    def __init__(self, code, detail=''):
        super().__init__(detail or code)
        self.code = code


class ArenaObservation:
    def __init__(self, state, observed_at, fingerprint=''):
        self.state, self.observed_at, self.fingerprint = state, observed_at, fingerprint


class ArenaSnapshotSource:
    """Small coherent arena/resources view; no full-account scan on each UI poll."""
    def __init__(self, config, max_age=300, wall_clock=time.time):
        if not 1 <= max_age <= 3600:
            raise ValueError('Snapshot maximum age must be 1..3600 seconds')
        self.config, self.max_age, self.wall_clock = config, max_age, wall_clock

    def read(self):
        import hashlib
        from tempfile import TemporaryDirectory
        from additional_readers import read_arena_stats
        from state_reader import read_player_resources
        root = Path(self.config.game_root)
        folder = root/'aggregate_snapshots' if (root/'aggregate_snapshots').is_dir() else root
        names = ('PlayerArenaModel.dat', 'PlayerModel.dat')
        try:
            originals = {}
            now = self.wall_clock()
            with TemporaryDirectory(prefix='invokers-arena-') as directory:
                local = Path(directory)
                for name in names:
                    path = folder/name
                    stamp = path.stat().st_mtime
                    if stamp > now + 5 or now - stamp > self.max_age:
                        raise SnapshotError('STALE_SNAPSHOT', name + ' is stale or future-dated')
                    originals[name] = path.read_bytes()
                    (local/name).write_bytes(originals[name])
                opponents = read_opponents(local/names[0])
                stats = read_arena_stats(local/names[0])
                resources = read_player_resources(local/names[1])
                if any((folder/n).read_bytes() != originals[n] for n in names):
                    raise SnapshotError('SNAPSHOT_CHANGED_DURING_READ')
                if any(type(o.get('combat_power')) is not int or o['combat_power'] <= 0 or not o.get('player_id_bytes') for o in opponents):
                    raise SnapshotError('INCOMPLETE_SNAPSHOT')
                ids = [o['player_id_bytes'] for o in opponents]
                if len(ids) != len(set(ids)):
                    raise SnapshotError('AMBIGUOUS_SNAPSHOT_IDENTITY')
                balances = resources['current']['values']
                if any(type(balances.get(k)) is not int for k in ('Gem', 'Arena_Token')):
                    raise SnapshotError('RESOURCES_UNKNOWN')
                arena = {'opponents': opponents, 'stats': stats,
                         'candidate_source': 'PlayerArenaModel.field12',
                         'own_combat_power': {'value': self.config.arena_combat_power,
                                              'source': 'UserConfig.arena_combat_power'}}
                state = {'arena': {'status': 'available', 'value': arena},
                         'resources': {'status': 'available', 'value': resources}}
                digest = hashlib.sha256(b''.join(originals[n] for n in names)).hexdigest()
                return ArenaObservation(state, now, digest)
        except SnapshotError:
            raise
        except (OSError, ValueError, StopIteration) as error:
            raise SnapshotError('SNAPSHOT_UNREADABLE', str(error)) from error
