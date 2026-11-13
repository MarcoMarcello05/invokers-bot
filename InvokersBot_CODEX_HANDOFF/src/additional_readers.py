"""Additional bounded readers backed by the shipped dump and real captures.

Wire profiles retain retired fields. No serialization/dictionary order is claimed
as UI order, and raw F64 relic values are not a sell/upgrade valuation model.
"""
from pathlib import Path
import uuid

from memorypack import DecodeError, field, int_list, model
from structured_state import dotnet_time

STAT_BONUSES = {
    0: 'Unknown', 1: 'AttackFlat', 2: 'DefenseFlat', 3: 'HealthFlat',
    4: 'AttackPercent', 5: 'DefensePercent', 6: 'HealthPercent',
    7: 'CriticalRatePercent', 8: 'CriticalDamagePercent', 9: 'AccuracyFlat',
    10: 'ResistanceFlat', 11: 'MoveSpeedFlat', 12: 'ComboSpeedFlat',
    13: 'SkillSpeedFlat', 14: 'SkillRecoveryFlat', 15: 'ManaGenerationFlat',
    16: 'InstinctRatingFlat', 21: 'IgnoreDefensePercent', 22: 'IncreaseHealingDone',
    23: 'IncreaseShieldDone', 24: 'DecreaseDamageTaken',
    25: 'BuffReductionDoneWithCombo3and5', 26: 'DodgeChance', 30: 'AnimaDuration',
    31: 'LifeStealByOtherSkills', 32: 'RunSpeedBonusOutOfCombat',
    33: 'LifeStealByCombos', 101: 'CrushTolerancePercent',
    102: 'ManaShockTolerancePercent', 103: 'FrostTolerancePercent',
    104: 'DazeTolerancePercent', 105: 'ParalysisTolerancePercent',
    106: 'NightmareTolerancePercent', 107: 'MindFogTolerancePercent',
    108: 'FatigueTolerancePercent', 109: 'BlightTolerancePercent',
    110: 'ManaBurnTolerancePercent', 111: 'AtrophyTolerancePercent',
    112: 'BloodRotTolerancePercent',
}
RELIC_SLOTS = {1: 'Weapon', 2: 'Shield', 3: 'Helmet', 4: 'Pauldrons',
               5: 'Gauntlets', 6: 'Chestplate', 7: 'Belt', 8: 'Boots'}
RELIC_SETS = {1: 'CrushTolerance', 2: 'ManaShockTolerance', 3: 'FrostTolerance',
              4: 'DazeTolerance', 5: 'ParalysisTolerance', 6: 'NightmareTolerance',
              7: 'MindFogTolerance', 8: 'FatigueTolerance', 9: 'BlightTolerance',
              10: 'ManaBurnTolerance', 11: 'AtrophyTolerance', 12: 'BloodRotTolerance',
              101: 'Attack', 102: 'Defense', 103: 'Health', 104: 'CriticalRate',
              105: 'CriticalDamage', 106: 'Accuracy', 107: 'Resistance',
              108: 'Instinct', 109: 'ManaGeneration', 110: 'SkillSpeed',
              111: 'SkillRecovery', 112: 'LifeSteal', 113: 'IgnoreDefense',
              114: 'Support', 115: 'ReduceBuffDuration', 116: 'EventSet1',
              117: 'EventSet2', 118: 'ClanBossSet1', 119: 'ClanBossSet2'}
RELIC_RARITY = {0: 'Unknown', 1: 'Common', 2: 'Uncommon', 3: 'Rare',
                4: 'Epic', 5: 'Legendary', 6: 'Greater'}


def _dictionary(span, key_fmt='i', value_fmt='i', sorted_keys=False):
    reader = span.reader()
    size = {'i': 4, 'q': 8}[key_fmt] + {'i': 4, 'q': 8}[value_fmt]
    result = {}
    previous = None
    for _ in range(reader.count(size)):
        key, value = reader.integer(key_fmt), reader.integer(value_fmt)
        if key in result or sorted_keys and previous is not None and key <= previous:
            raise DecodeError('Invalid/duplicate sorted dictionary key')
        result[key] = value
        previous = key
    reader.finish()
    return result


def _nullable_time(span):
    if len(span.data) != 16 or span.data[0] not in (0, 1):
        raise DecodeError('Invalid Nullable<DateTime> width/has-value byte')
    if not span.data[0]:
        return None
    from memorypack import Span
    return dotnet_time(Span(span.data[8:], span.offset + 8))


def _unknown_fields(fields, known):
    return [{'index': index, 'hex': span.data.hex(), 'offset': span.offset}
            for index, span in enumerate(fields) if index not in known and span.data]


def read_hero_roster(path: Path):
    fields = model(Path(path).read_bytes(), 2)
    reader = field(fields, 1).reader()
    heroes, previous = [], None
    for _ in range(reader.count(5)):
        key = reader.integer()
        if previous is not None and key <= previous:
            raise DecodeError('HeroesById must have unique ascending keys')
        previous = key
        hero = reader.object()
        inventory_id = field(hero, 0).integer()
        if inventory_id != key or inventory_id <= 0:
            raise DecodeError('Hero inventory ID disagrees with dictionary key')
        config_id = field(hero, 1).integer('q')
        record = {'inventory_id': inventory_id, 'config_id': config_id,
                  'config_id_hex': f'0x{config_id:016X}',
                  'rank': field(hero, 2).integer(), 'level': field(hero, 3).integer(),
                  'experience': field(hero, 4).integer(),
                  'total_experience': field(hero, 5).integer(),
                  'locked': field(hero, 6).boolean(),
                  'in_storage': field(hero, 7).boolean(),
                  'marker_id': field(hero, 8).integer(),
                  'recent_battle_time': _nullable_time(field(hero, 9)),
                  'relic_id_by_slot': _dictionary(field(hero, 11), sorted_keys=True),
                  'accessory_id_by_slot': _dictionary(field(hero, 12), sorted_keys=True),
                  'skills': [], 'record_offset': field(hero, 0).offset}
        if record['level'] < 0 or record['experience'] < 0 or record['total_experience'] < 0:
            raise DecodeError('Negative hero progression')
        # UpgradeableSkill is sequential { SkillKind:Int32, Level:Int32 }.
        skills = field(hero, 21).reader()
        seen_skills = set()
        for _ in range(skills.count(8)):
            kind, level = skills.integer(), skills.integer()
            if kind in seen_skills or level < 0:
                raise DecodeError('Invalid skill entry')
            seen_skills.add(kind)
            record['skills'].append({'kind_id': kind, 'level': level})
        skills.finish()
        # These reserved/late fields are preserved, not guessed as awakening/skin.
        record['unknown_fields'] = _unknown_fields(hero, set(range(10)) | {11, 12, 21})
        heroes.append(record)
    reader.finish()
    lobby = int_list(field(fields, 2))
    return {'heroes': heroes, 'last_id': field(fields, 0).integer(),
            'serialized_order_ids': [h['inventory_id'] for h in heroes],
            'lobby_hero_ids': lobby,
            'ui_order_ids': None,
            'ui_order_status': 'unknown: HeroesById is sorted by inventory ID; lobby IDs are not UI sort order',
            'method': 'structured'}


def read_relic_inventory(path: Path):
    fields = model(Path(path).read_bytes(), 4)
    reader = field(fields, 1).reader()
    relics, previous = [], None
    for _ in range(reader.count(5)):
        key = reader.integer()
        if previous is not None and key <= previous:
            raise DecodeError('RelicsById must have unique ascending keys')
        previous = key
        relic = reader.object()
        inventory_id = field(relic, 0).integer()
        if inventory_id != key or inventory_id <= 0:
            raise DecodeError('Relic inventory ID disagrees with dictionary key')
        slot, rarity, set_id = (field(relic, i).integer() for i in (1, 3, 4))
        record = {'inventory_id': inventory_id, 'slot_id': slot,
                  'slot': RELIC_SLOTS.get(slot, f'Unknown({slot})'),
                  'rank': field(relic, 2).integer(),
                  'rarity_id': rarity, 'rarity': RELIC_RARITY.get(rarity, f'Unknown({rarity})'),
                  'set_id': set_id, 'set': RELIC_SETS.get(set_id, f'Unknown({set_id})'),
                  'equipped_hero_id': field(relic, 5).nullable(),
                  'level': field(relic, 6).integer(),
                  'is_seen': field(relic, 7).boolean(), 'bonuses': [],
                  'record_offset': field(relic, 0).offset,
                  'value_status': 'unknown: bonus Raw values are not an evaluated item/cost model'}
        if record['level'] < 0 or record['rank'] < 0:
            raise DecodeError('Negative relic progression')
        bonuses = field(relic, 8).reader()
        seen_bonus = set()
        for _ in range(bonuses.count(1)):
            bonus = bonuses.object()
            bonus_id, stat = field(bonus, 0).integer(), field(bonus, 1).integer()
            if bonus_id in seen_bonus:
                raise DecodeError('Duplicate relic bonus ID')
            seen_bonus.add(bonus_id)
            record['bonuses'].append({'id': bonus_id, 'stat_bonus_id': stat,
                                      'stat_bonus': STAT_BONUSES.get(stat, f'Unknown({stat})'),
                                      'value_raw': field(bonus, 2).integer('q'),
                                      'level': field(bonus, 3).integer(),
                                      'rolls_sum_raw': field(bonus, 4).integer('q'),
                                      'value': None, 'offset': field(bonus, 0).offset,
                                      'scale_status': 'raw F64; conversion not fixture-validated'})
        bonuses.finish()
        relics.append(record)
    reader.finish()
    return relics


def read_clan_state(path: Path):
    fields = model(Path(path).read_bytes(), 12)
    membership = field(fields, 0).object()
    if membership is None:
        member = None
    else:
        clan_id = field(membership, 0)
        if len(clan_id.data) != 16:
            raise DecodeError('Invalid clan GUID')
        member = {'clan_id': str(uuid.UUID(bytes_le=clan_id.data)),
                  'role_id': field(membership, 1).integer(),
                  'joined_at': dotnet_time(field(membership, 2)),
                  'can_participate_at': _nullable_time(field(membership, 3)),
                  'clan_abbreviation': field(membership, 4).string()}
    boss = field(fields, 18).object()
    boss2 = None
    if boss is not None:
        chests_reader = field(boss, 3).reader()
        chests = []
        for _ in range(chests_reader.count(1)):
            # No nonempty chest fixture yet; retain bounded fields, never claimable.
            chest = chests_reader.object()
            chests.append({'fields': _unknown_fields(chest, set()) if chest is not None else None,
                           'status': 'unknown: no validated nonempty boss chest fixture'})
        chests_reader.finish()
        boss2 = {'day': dotnet_time(field(boss, 0)),
                 'replays_used': field(boss, 1).integer(),
                 'started_difficulties': int_list(field(boss, 2)),
                 'chests': chests,
                 'best_damage_by_difficulty': _dictionary(field(boss, 4), value_fmt='q'),
                 'current_boss_hp': None,
                 'current_boss_hp_status': 'unknown: not present in PlayerClanBoss2State schema'}
    nullable_objects = {}
    for index, name in [(6, 'daily_activity'), (7, 'pending_activity_chest'),
                        (8, 'daily_boss_activity'), (9, 'pending_boss_chest')]:
        obj = field(fields, index).object()
        nullable_objects[name] = None if obj is None else {
            'status': 'unknown: nonnull variant not fixture-validated',
            'fields': _unknown_fields(obj, set())}
    return {'membership': member, 'boss2': boss2, **nullable_objects,
            'method': 'structured', 'offset': field(fields, 18).offset}


def read_arena_stats(path: Path):
    """Read the captured ArenaBattleStats profile, preserving evidence limits.

    Slots 0..3 are retired; totals moved to 8..11. Counter semantics follow the
    dumped schema and are corroborated by league sums and offense quest progress.
    Real before/after battle/refresh transition validation remains a Windows gate.
    """
    arena = model(Path(path).read_bytes(), 9)
    fields = field(arena, 10).object()
    indices = {
        'defense_battles_this_week': 4, 'defense_wins_this_week': 5,
        'defense_battles_last_week': 6, 'defense_wins_last_week': 7,
        'total_offense_battles': 8, 'total_offense_wins': 9,
        'total_defense_battles': 10, 'total_defense_wins': 11,
        'max_league_reached': 12,
        'attack_battles_this_week': 14, 'attack_wins_this_week': 15,
        'attack_battles_last_week': 16, 'attack_wins_last_week': 17,
    }
    stats = {name: field(fields, index).integer() for name, index in indices.items()}
    if any(value < 0 for value in stats.values()):
        raise DecodeError('Negative Arena counter')
    for battles, wins in [
            ('total_offense_battles', 'total_offense_wins'),
            ('total_defense_battles', 'total_defense_wins'),
            ('defense_battles_this_week', 'defense_wins_this_week'),
            ('defense_battles_last_week', 'defense_wins_last_week'),
            ('attack_battles_this_week', 'attack_wins_this_week'),
            ('attack_battles_last_week', 'attack_wins_last_week')]:
        if stats[wins] > stats[battles]:
            raise DecodeError('Arena wins exceed battle count')
    stats['total_battles_by_league'] = _dictionary(field(fields, 13), sorted_keys=True)
    if any(value < 0 for value in stats['total_battles_by_league'].values()):
        raise DecodeError('Negative Arena league counter')
    stats['league_accounting_matches'] = sum(stats['total_battles_by_league'].values()) == (
        stats['total_offense_battles'] + stats['total_defense_battles'])
    stats['counter_offsets'] = {name: field(fields, index).offset for name, index in indices.items()}
    stats['unknown_fields'] = _unknown_fields(fields, set(indices.values()) | {13})
    stats['validation'] = 'captured_profile_schema_and_accounting_correlated'
    stats['transition_validation'] = 'unknown: no actual battle transition capture supplied'
    # Do not claim a timestamp change proves a refresh: field 7 is week-stable,
    # while field 5 follows list changes but has no independently captured refresh.
    stats['timestamp_fields'] = {str(index): dotnet_time(field(arena, index)) for index in (5, 7)}
    stats['last_refresh_time'] = None
    stats['last_refresh_time_status'] = 'unknown: field 5 is a correlated candidate; field 7 is week-stable'
    return stats


QUEST_PERIODIC_GROUPS = {0: 'Unknown', 1: 'Daily', 2: 'Weekly', 3: 'Monthly',
                         4: 'Advance', 5: 'Clan'}
QUEST_STATES = {0: 'Unknown', 1: 'New', 2: 'InProgress', 3: 'Completed'}


def read_quest_states(path: Path):
    """Read every active quest union record; subtype/group, never ID range, sets kind.

    A Completed state is not evidence that clicking a reward is safe: the actor
    still needs a confirmed ANNEHMEN button and post-action structural verification.
    """
    fields = model(Path(path).read_bytes(), 8)
    reader = field(fields, 1).reader()
    quests, previous = [], None
    for _ in range(reader.count(6)):
        key = reader.integer()
        if key <= 0 or previous is not None and key <= previous:
            raise DecodeError('Invalid/duplicate active quest key')
        previous = key
        tag = reader.integer('B')
        state = reader.object()
        if state is None:
            raise DecodeError('Active quest union payload cannot be null')
        if tag not in (1, 2, 3):
            quests.append({'quest_id': key, 'prototype_id': None, 'state_id': None,
                           'state': 'Unknown', 'progress': None, 'extra': None,
                           'group': None, 'kind': 'Unknown', 'union_tag': tag,
                           'reward_claimable': None,
                           'unknown_reason': 'Unrecognized quest subtype; no decisions from undecoded payload',
                           'unknown_fields': _unknown_fields(state, set())})
            continue
        quest_id = field(state, 0).integer()
        if quest_id != key:
            raise DecodeError('Quest ID disagrees with active dictionary key')
        prototype_id = field(state, 1).integer()
        state_id = field(state, 2).integer()
        progress, extra = field(state, 5).integer(), field(state, 50).integer()
        if prototype_id <= 0 or progress < 0:
            raise DecodeError('Invalid quest prototype/progress')
        record = {'quest_id': quest_id, 'prototype_id': prototype_id,
                  'state_id': state_id, 'state': QUEST_STATES.get(state_id, f'Unknown({state_id})'),
                  'time_started': dotnet_time(field(state, 3)), 'progress': progress,
                  'extra': extra, 'union_tag': tag,
                  'record_offset': field(state, 0).offset,
                  'kind': {1: 'Periodic', 2: 'Achievement', 3: 'Book'}[tag],
                  'group': QUEST_PERIODIC_GROUPS.get(extra) if tag == 1 else
                           'Achievements' if tag == 2 else 'Book',
                  'reward_claimable': None,
                  'reward_status': 'unknown: completion does not replace ANNEHMEN UI confirmation',
                  'unknown_fields': _unknown_fields(state, {0, 1, 2, 3, 5, 50})}
        if tag == 1:
            record['periodic_group_id'] = extra
        elif tag == 2:
            record['achievement_group_id'] = extra
        else:
            record['page'] = extra
        quests.append(record)
    reader.finish()

    completed_reader = field(fields, 2).reader()
    completed = [completed_reader.integer() for _ in range(completed_reader.count(4))]
    completed_reader.finish()
    # CompletedPrototypeIds is a List, not a set; preserve repeatable prototypes.
    periodic_reader = field(fields, 3).reader()
    periodic_groups = {}
    for _ in range(periodic_reader.count(5)):
        key = periodic_reader.integer()
        if key in periodic_groups:
            raise DecodeError('Duplicate periodic group key')
        group = periodic_reader.object()
        periodic_groups[key] = {'group': QUEST_PERIODIC_GROUPS.get(key),
                                'start_time': dotnet_time(field(group, 0)),
                                'finish_time': _nullable_time(field(group, 1))}
    periodic_reader.finish()
    achievement_reader = field(fields, 4).reader()
    achievement_groups = {}
    for _ in range(achievement_reader.count(5)):
        key = achievement_reader.integer()
        if key in achievement_groups:
            raise DecodeError('Duplicate achievement group key')
        group = achievement_reader.object()
        achievement_groups[key] = {'current_level': field(group, 0).integer(),
                                   'progress': field(group, 1).integer()}
    achievement_reader.finish()
    return {'quests': quests, 'last_quest_id': field(fields, 0).integer(),
            'completed_prototype_ids': completed, 'periodic_groups': periodic_groups,
            'achievement_groups': achievement_groups,
            'total_completed_quests': field(fields, 5).integer(), 'method': 'structured'}


def read_quests(path: Path):
    """List adapter for existing enrichment/planner call sites."""
    return read_quest_states(path)['quests']
