"""One read-only snapshot boundary for readers and planner adapters.

Every section carries its method, exact input hashes, and unknown/error reason.
Hero/quest/relic inventories use bounded structural readers. Static-name and
quest-definition signature searches remain explicitly heuristic.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import invokers_core as core
from memorypack import DecodeError, model
from state_reader import campaign_summary, read_level_stats, read_player_resources
from structured_state import read_arena_collections, read_battle_state, read_events
from additional_readers import read_hero_roster, read_relic_inventory, read_clan_state, read_arena_stats, read_quest_states


@dataclass
class Observation:
    value: Any
    status: str
    method: str
    sources: list[str]
    reason: str | None = None


@dataclass
class GameState:
    schema_version: int
    captured_at_utc: str
    sources: dict
    resources: Observation
    campaign: Observation
    arena: Observation
    events: Observation
    heroes: Observation
    quests: Observation
    relics: Observation
    hero_internal_names: Observation
    quest_prototypes: Observation
    safety: dict
    hero_roster: Observation = field(default_factory=lambda: Observation(None, 'unknown', 'structured', [], 'Roster unavailable'))
    main_team: Observation = field(default_factory=lambda: Observation(None, 'unknown', 'user_config', [], 'Main Six not confirmed'))
    bosses: Observation = field(default_factory=lambda: Observation(None, 'unknown', 'structured', [], 'Clan model unavailable'))
    quest_log: Observation = field(default_factory=lambda: Observation(None, 'unknown', 'structured', [], 'Quest metadata unavailable'))

    def to_dict(self):
        return asdict(self)


MODEL_TAGS = {'PlayerModel.dat': 1, 'PlayerHeroesModel.dat': 2,
              'PlayerAnimasModel.dat': 3, 'PlayerRelicsModel.dat': 4,
              'PlayerAccessoriesModel.dat': 5, 'PlayerBattleModel.dat': 7,
              'PlayerQuestsModel.dat': 8, 'PlayerArenaModel.dat': 9,
              'PlayerGlobalEventsModel.dat': 10, 'PlayerClanModel.dat': 12}


def build_game_state(root: Path, dump_root: Path | None = None,
                     static_path: Path | None = None, user_config=None) -> GameState:
    if user_config is not None:
        user_config.validate()
    root = Path(root)
    snapshots = root/'aggregate_snapshots' if (root/'aggregate_snapshots').is_dir() else root
    sources, originals = {}, {}
    static_path = Path(static_path) if static_path else core.find_static_data(root)
    with TemporaryDirectory(prefix='invokers-state-') as directory:
        local = Path(directory)
        for name in MODEL_TAGS:
            path = snapshots/name
            if path.exists():
                data = path.read_bytes()
                (local/name).write_bytes(data)
                originals[name] = path
                sources[name] = {'path': str(path.resolve()), 'size': len(data),
                                 'sha256': hashlib.sha256(data).hexdigest()}
        if static_path is not None:
            data = static_path.read_bytes()
            (local/'static.dat').write_bytes(data)
            originals['static_data'] = static_path
            sources['static_data'] = {'path': str(static_path.resolve()), 'size': len(data),
                                      'sha256': hashlib.sha256(data).hexdigest()}

        def observe(names, method, read):
            missing = [name for name in names if name not in sources]
            if missing:
                return Observation(None, 'unknown', method, names, 'Missing: ' + ', '.join(missing))
            try:
                for name in names:
                    if name in MODEL_TAGS:
                        model((local/name).read_bytes(), MODEL_TAGS[name])
                return Observation(read(), 'available', method, names)
            except (DecodeError, OSError, ValueError, StopIteration) as error:
                return Observation(None, 'unknown', method, names, str(error))

        resources = observe(['PlayerModel.dat'], 'structured',
                            lambda: read_player_resources(local/'PlayerModel.dat', dump_root))
        def campaign():
            rows = read_level_stats(local/'PlayerBattleModel.dat')
            return {'level_stats': rows, 'summary': campaign_summary(rows)}
        campaigns = observe(['PlayerBattleModel.dat'], 'structured+derived', campaign)
        def arena():
            battle = read_battle_state(local/'PlayerBattleModel.dat')
            battle['opponent_collections'] = read_arena_collections(local/'PlayerArenaModel.dat')
            battle['stats'] = read_arena_stats(local/'PlayerArenaModel.dat')
            battle['opponents'] = next(c['records'] for c in battle['opponent_collections'] if c['role'] == 'current')
            battle['candidate_status'] = 'ui_correlated'
            battle['list_role_method'] = 'user_ui_correlated: Windows _SILVA00 / 6151'
            battle['field_methods'] = {'attack_preset': 'structured', 'opponents': 'structured',
                                       'opponent_collections': 'structured', 'own_combat_power': 'unknown'}
            if user_config is not None:
                battle['snapshot_own_combat_power'] = battle['own_combat_power']
                configured = user_config.arena_combat_power
                battle['own_combat_power'] = {
                    'value': configured, 'status': 'configured' if configured is not None else 'unknown',
                    'source': 'UserConfig.arena_combat_power', 'authoritative': configured is not None,
                    'reason': 'Manual UserConfig is authoritative until replaced by a validated source' if configured is not None else 'Arena power has not been configured'}
                battle['field_methods']['own_combat_power'] = 'user_config'
            by_id = {h['inventory_id']: h for h in heroes.value or []}
            mismatches = []
            for slot in (battle['attack_preset'] or {}).get('slots', []):
                hero = by_id.get(slot['hero_inventory_id'])
                slot['hero_link_status'] = 'matched' if hero and hero['config_id'] == slot['hero_config_id'] else 'unknown'
                if slot['hero_link_status'] == 'unknown' and slot['hero_inventory_id'] is not None:
                    mismatches.append(slot['hero_inventory_id'])
            battle['unresolved_hero_inventory_ids'] = mismatches
            return battle
        roster = observe(['PlayerHeroesModel.dat'], 'structured', lambda: read_hero_roster(local/'PlayerHeroesModel.dat'))
        heroes = Observation(roster.value['heroes'] if roster.value is not None else None,
                             roster.status, 'structured', list(roster.sources), roster.reason)
        arenas = observe(['PlayerBattleModel.dat', 'PlayerArenaModel.dat'], 'mixed', arena)
        if heroes.status == 'available':
            arenas.sources.append('PlayerHeroesModel.dat')
        events = observe(['PlayerGlobalEventsModel.dat'], 'structured', lambda: read_events(local/'PlayerGlobalEventsModel.dat'))
        quest_log = observe(['PlayerQuestsModel.dat'], 'structured', lambda: read_quest_states(local/'PlayerQuestsModel.dat'))
        quests = Observation(quest_log.value['quests'] if quest_log.value is not None else None,
                             quest_log.status, 'structured', list(quest_log.sources), quest_log.reason)
        relics = observe(['PlayerRelicsModel.dat'], 'structured', lambda: read_relic_inventory(local/'PlayerRelicsModel.dat'))
        bosses = observe(['PlayerClanModel.dat'], 'structured', lambda: read_clan_state(local/'PlayerClanModel.dat'))
        ids = list(user_config.main_six_ids) if user_config is not None else []
        known_ids = {h['inventory_id'] for h in heroes.value or []}
        main_team = Observation(ids, 'available', 'user_config', ['UserConfig.main_six_ids']) if len(ids) == 6 and set(ids) <= known_ids else Observation(None, 'unknown', 'user_config', [], 'Confirm six existing UI hero IDs in UserConfig; stored ID order is not UI order')

        def hero_names():
            return core.map_hero_internal_names(heroes.value, local/'static.dat')
        def quest_definitions():
            return core.decode_quest_prototypes(local/'static.dat', {q['prototype_id'] for q in quests.value if q['prototype_id'] is not None})
        # The legacy static decoders suppress decompression errors; validate first.
        static_valid = None
        if 'static_data' in sources:
            static_valid = core.extract_static_main_chunk(local/'static.dat') is not None
        names = observe(['PlayerHeroesModel.dat', 'static_data'], 'heuristic', hero_names) if heroes.value is not None else Observation(None, 'unknown', 'heuristic', [], 'Heroes unavailable')
        prototypes = observe(['PlayerQuestsModel.dat', 'static_data'], 'heuristic', quest_definitions) if quests.value is not None else Observation(None, 'unknown', 'heuristic', [], 'Quests unavailable')
        if static_valid is False:
            for observation in (names, prototypes):
                observation.value, observation.status, observation.reason = None, 'unknown', 'Static chunk cannot be decoded'
        if prototypes.status == 'available' and quests.status == 'available':
            quests.value = core.enrich_quests(quests.value, prototypes.value)
            quests.sources.append('static_data')

        # Read from private captured copies; reject a source changed during capture.
        # This does not claim that separately written game files share one game tick.
        for name, path in originals.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != sources[name]['sha256']:
                raise DecodeError(f'Snapshot changed during capture: {name}; retry after the game finishes writing')

    return GameState(2, datetime.now(timezone.utc).isoformat(), sources,
                     resources, campaigns, arenas, events, heroes, quests, relics, names, prototypes,
                     {'actor_enabled': False, 'gems_allowed': False, 'premium_spend_allowed': False,
                      'current_arena_power_verified': user_config is not None and user_config.arena_combat_power is not None,
                      'arena_power_source': 'UserConfig' if user_config is not None else 'unknown',
                      'capture_consistency': 'unchanged_during_read; cross-file game tick unknown'},
                     hero_roster=roster, main_team=main_team, bosses=bosses, quest_log=quest_log)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build a read-only, provenance-aware GameState')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1]/'tests/fixtures')
    parser.add_argument('--dump', type=Path)
    parser.add_argument('--static', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    state = build_game_state(args.root, args.dump, args.static)
    text = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + '\n', encoding='utf-8')
    else:
        print(text)
    return 0 if all(getattr(state, name).status == 'available'
                    for name in ('resources', 'campaign', 'arena', 'events', 'heroes', 'quests', 'relics')) else 1


if __name__ == '__main__':
    raise SystemExit(main())
