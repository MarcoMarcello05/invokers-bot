"""Compatibility entry point for the GameState-only planner runtime.

Legacy OCR/planner scoring and executable command adaptation are retired.
"""
from pathlib import Path
from game_state import build_game_state
from failure_memory import FailureMemory
from runtime import atomic_json, main, tick
from user_config import UserConfig, default_config_path

ROOT = Path(__file__).resolve().parent
GAME_ROOT = Path.home()/'AppData/LocalLow/Hit_Zone/Invokers'
PLAN_FILE = ROOT/'runtime/action_plan.json'


def build_plan(config=None, memory=None, now=None):
    config = config or UserConfig.load(default_config_path())
    memory = memory or FailureMemory()
    if config.game_root == UserConfig().game_root:
        config.game_root = str(GAME_ROOT)
    output, state = tick(config, memory, now=now, reader=build_game_state)
    atomic_json(PLAN_FILE, output)
    return output


if __name__ == '__main__':
    raise SystemExit(main())


def plan_arena(snapshot, config, excluded=()):
    """Arena-only adapter using the existing structured priority/Safety contract."""
    from bot_actions import Action, section_value
    import hashlib
    import json
    arena = section_value(snapshot.state, 'arena') or {}
    power = config.arena_combat_power
    if type(power) is not int or power <= 0:
        raise ValueError('OWN_POWER_UNKNOWN')
    excluded = set(excluded)
    candidates = [o for o in arena.get('opponents', [])
                  if o['combat_power'] < power and o['player_id_bytes'] not in excluded]
    candidates.sort(key=lambda o: (o['combat_power'], o['arena_points'], o['name'].casefold()))
    if not candidates:
        return None
    pick = candidates[0]
    target = {key: pick[key] for key in ('name', 'player_id_bytes', 'combat_power')}
    identity = json.dumps(target, sort_keys=True)
    return Action(hashlib.sha256(identity.encode()).hexdigest()[:20], 'ARENA_BATTLE', 'arena',
                  target=target, resource_costs={'Arena_Token': 1},
                  preconditions={'costs_verified': False}, expected_effects={'type': 'arena_battle'},
                  reasons=('Weakest eligible opponent from authoritative current field 12',))
