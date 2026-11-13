"""Schema/profile based battle and event readers, validated on captured fixtures.

Wire indices include retired members: TeamPresetData lead=4, BattleModel
AsyncPvpPreset=23; Participation derived members start at 50. See research/D1_DECODING.md.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from memorypack import DecodeError, field, int_list, model

POSITIONS = {0: 'Unknown', 11: 'Front1', 12: 'Front2', 21: 'Mid1',
             22: 'Mid2', 31: 'Back1', 32: 'Back2'}
TYPES = {1: 'Common', 2: 'GetLegendary', 3: 'Novice', 4: 'DailyBestScore'}


def dotnet_time(span):
    raw = span.integer('Q')
    ticks, kind = raw & ((1 << 62) - 1), raw >> 62
    if ticks > 3155378975999999999:
        raise DecodeError('DateTime ticks outside .NET range')
    value = datetime(1, 1, 1) + timedelta(microseconds=ticks // 10)
    # Keep the raw ticks: Python datetime has microsecond, not 100ns precision.
    if kind == 1:
        value = value.replace(tzinfo=timezone.utc)
    return {'iso': value.isoformat(), 'ticks': ticks, 'kind': kind}


def decode_preset(span):
    fields = span.object()
    if fields is None:
        return None
    formation = field(fields, 0).integer()
    lead = field(fields, 4).integer()
    if formation not in {*range(0, 10), *range(11, 20), *range(21, 28)} or lead not in POSITIONS:
        raise DecodeError('Invalid formation/lead position')
    slots_reader = field(fields, 1).reader()
    slots = []
    for _ in range(slots_reader.count(7)):
        start = slots_reader.offset + slots_reader.pos
        sf = slots_reader.object()
        position = field(sf, 0).integer()
        if position not in POSITIONS or position == 0:
            raise DecodeError('Invalid preset slot position')
        slot = {'position': position, 'position_name': POSITIONS[position],
                'hero_inventory_id': field(sf, 1).nullable(),
                'hero_config_id': field(sf, 2).nullable('q'),
                'anima_inventory_id': field(sf, 3).nullable(),
                'anima_config_id': field(sf, 4).nullable('q'),
                'anima_priority': field(sf, 5).integer(), 'offset': start}
        for name in ('hero_inventory_id', 'anima_inventory_id'):
            if slot[name] is not None and slot[name] <= 0:
                raise DecodeError('Invalid inventory ID')
        slots.append(slot)
    slots_reader.finish()
    if len({s['position'] for s in slots}) != len(slots):
        raise DecodeError('Duplicate formation position')
    if lead and lead not in {s['position'] for s in slots}:
        raise DecodeError('Lead is outside formation')
    return {'formation_id': formation, 'lead_position': lead,
            'lead_position_name': POSITIONS[lead], 'slots': slots,
            'offset': span.offset}


def read_battle_state(path: Path):
    fields = model(path.read_bytes(), 7)
    preset = decode_preset(field(fields, 23))
    last = field(fields, 2).object()
    # A historical battle power cannot establish the current Arena formation power.
    power = {'value': None, 'status': 'unknown', 'source': 'PlayerBattleModel.LastMetaBattleSetup',
             'reason': 'LastMetaBattleSetup is null' if last is None else
                       'Historical battle setup is not validated as current Arena power',
             'offset': field(fields, 2).offset}
    return {'attack_preset': preset, 'own_combat_power': power,
            'last_meta_battle_setup_present': last is not None}


def read_arena_collections(path: Path):
    """Keep current candidates separate from the other stored collection.

    Wire field 12 is UI-correlated by _SILVA00 / 6151 in the Windows comparison.
    Field 15's exact cache/history semantics remain unknown; exclude it from attacks.
    """
    fields = model(path.read_bytes(), 9)
    collections = []
    for index in (12, 15):
        span = field(fields, index)
        reader = span.reader()
        records = []
        for _ in range(reader.count(1)):
            opponent = reader.object()
            team = field(opponent, 4).object()
            power = field(team, 0).integer()
            player_id = field(team, 1)
            if power < 0 or len(player_id.data) != 16:
                raise DecodeError('Invalid BattlePlayerTeamSetup identity/power')
            records.append({'name': field(opponent, 0).string(),
                            'level': field(opponent, 1).integer(),
                            'arena_points': field(opponent, 3).integer(),
                            'combat_power': power, 'player_id_bytes': player_id.data.hex(),
                            'offset': field(opponent, 0).offset,
                            'combat_power_offset': field(team, 0).offset})
        reader.finish()
        collections.append({'wire_field': index,
                            'role': 'current' if index == 12 else 'other_stored',
                            'role_method': 'user_ui_correlated' if index == 12 else 'excluded_from_current',
                            'records': records})
    return collections


COMMON = [('bracket_id', 'nq'), ('points', 'i'), ('claimed_personal_reward_ids', 'set'),
          ('claimed_bracket_reward', 'bool'), ('claimed_global_reward', 'bool'),
          ('claimed_milestone_reward_ids', 'set'), ('unlocked_milestone_reward_ids', 'set'),
          ('final_bracket_rank', 'ni'), ('final_global_rank', 'ni'),
          ('liked_milestone_reward_ids', 'set'), ('seen_bracket_top_rank', 'i'),
          ('current_bracket_top_rank', 'i'), ('seen_global_top_rank', 'i'),
          ('current_global_top_rank', 'i'), ('small_bracket_reward_unavailable', 'nbool')]
LEGENDARY = [('points_by_source_type_id', 'map'), ('claimed_personal_reward_ids', 'set'),
             ('purchased_shop_items_by_id', 'map'), ('bracket_id', 'nq'),
             ('claimed_bracket_reward', 'bool'), ('claimed_global_reward', 'bool'),
             ('claimed_milestone_reward_ids', 'set'), ('unlocked_milestone_reward_ids', 'set'),
             ('final_bracket_rank', 'ni'), ('final_global_rank', 'ni'),
             ('liked_milestone_reward_ids', 'set'), ('seen_bracket_top_rank', 'i'),
             ('current_bracket_top_rank', 'i'), ('seen_global_top_rank', 'i'),
             ('current_global_top_rank', 'i')]
NOVICE = [('bracket_id', 'nq'), ('points', 'i'), ('bracket_started_at_utc', 'time'),
          ('scoring_ends_at_utc', 'time'), ('reward_period_ends_at_utc', 'time'),
          ('claimed_personal_reward_ids', 'set'), ('claimed_bracket_reward', 'bool'),
          ('seen_bracket_top_rank', 'i'), ('current_bracket_top_rank', 'i'),
          ('final_bracket_rank', 'ni')]
DAILY = [('bracket_id', 'nq'), ('period_score', 'q'), ('daily_best_score_activity_index', 'ni'),
         ('daily_best_score', 'q'), ('daily_reward_states', 'daily_rewards'),
         ('period_reward_state', 'reward'), ('generated_resource_daily_activity_index', 'ni'),
         ('claimed_milestone_reward_ids', 'set'), ('unlocked_milestone_reward_ids', 'set'),
         ('liked_milestone_reward_ids', 'set'), ('claimed_personal_reward_ids', 'set')]


def decode_reward(fields):
    if fields is None:
        return None
    return {name: decode_value(field(fields, i), kind) for i, (name, kind) in enumerate([
        ('final_bracket_rank', 'ni'), ('final_global_rank', 'ni'),
        ('claimed_bracket_reward', 'bool'), ('claimed_global_reward', 'bool'), ('score', 'q')])}


def decode_value(span, kind):
    if kind == 'reward':
        return decode_reward(span.object())
    if kind == 'daily_rewards':
        reader = span.reader()
        result = {}
        for _ in range(reader.count(5)):
            key = reader.integer()
            if key in result:
                raise DecodeError('Duplicate daily reward key')
            result[key] = decode_reward(reader.object())
        reader.finish()
        return result
    if kind == 'set':
        return int_list(span)
    if kind == 'map':
        reader = span.reader()
        result = {}
        for _ in range(reader.count(8)):
            key, value = reader.integer(), reader.integer()
            if key in result:
                raise DecodeError('Duplicate dictionary key')
            result[key] = value
        reader.finish()
        return result
    if kind == 'time':
        return dotnet_time(span)
    if kind == 'bool':
        return span.boolean()
    if kind == 'nbool':
        value = span.nullable('B')
        if value not in (None, 0, 1):
            raise DecodeError('Invalid nullable bool')
        return None if value is None else bool(value)
    if kind.startswith('n'):
        return span.nullable(kind[1:])
    return span.integer(kind)


def read_events(path: Path):
    fields = model(path.read_bytes(), 10)
    reader = field(fields, 0).reader()
    tournaments = []
    seen = set()
    for _ in range(reader.count(9)):
        key = reader.integer('q')
        if key in seen:
            raise DecodeError('Duplicate tournament ID')
        seen.add(key)
        start = reader.offset + reader.pos
        tag = reader.integer('B')
        if tag not in TYPES:
            raise DecodeError(f'Unsupported participation union tag {tag}')
        state = reader.object()
        tournament_id = field(state, 0).integer('q')
        if tournament_id != key:
            raise DecodeError('Participation ID disagrees with dictionary key')
        record = {'tournament_id': key, 'participation_type': TYPES[tag], 'union_tag': tag,
                  'joined_at_utc': dotnet_time(field(state, 2)),
                  'scoring_completed': field(state, 3).boolean(),
                  'group_id': field(state, 4).integer(), 'offset': start,
                  'definition': None,
                  'definition_status': 'unknown: runtime tournament catalog not included'}
        schema = {1: COMMON, 2: LEGENDARY, 3: NOVICE, 4: DAILY}[tag]
        record['status'] = 'decoded'
        record['validation'] = 'schema_only' if tag == 4 else 'captured_fixture'
        record['tournament_type_id'] = {2: 51, 3: 52, 4: 53}.get(tag)
        record['field_offsets'] = {}
        for index, (name, kind) in enumerate(schema, 50):
            span = field(state, index)
            record[name] = decode_value(span, kind)
            record['field_offsets'][name] = span.offset
        known_indices = {0, 2, 3, 4, *range(50, 50 + len(schema))}
        record['unknown_fields'] = [{'index': i, 'hex': s.data.hex()} for i, s in enumerate(state)
                                    if i not in known_indices and s.data]
        tournaments.append(record)
    reader.finish()
    return {'tournaments': tournaments,
            'finished_novice_tournament': field(fields, 1).boolean(),
            'completed_novice_tournament_group_ids': int_list(field(fields, 2))}
