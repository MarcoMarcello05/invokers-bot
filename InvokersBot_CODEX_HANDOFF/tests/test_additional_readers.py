from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from additional_readers import read_arena_stats, read_clan_state, read_hero_roster, read_quest_states, read_quests, read_relic_inventory
from memorypack import DecodeError, model
import invokers_core as legacy

FIXTURES = ROOT/'tests/fixtures'
from fixture_support import comparison_fixture


def pack_object(fields):
    lengths = b''.join(bytes([len(f)]) if len(f) <= 127 else b'\x82' + struct.pack('<i', len(f)) for f in fields)
    return bytes([len(fields)]) + lengths + b''.join(fields)


def envelope(tag, fields):
    return bytes([tag]) + pack_object([b'\0' * 8, b'\0' * 8, pack_object(fields)])


class AdditionalReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_context=comparison_fixture()
        cls.archive_path,cls.private_profile=cls.fixture_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.fixture_context.__exit__(None,None,None)

    def test_structural_roster_retains_all_thirty_records(self):
        result = read_hero_roster(FIXTURES/'PlayerHeroesModel.dat')
        heroes = result['heroes']
        self.assertEqual(len(heroes), 30)
        self.assertEqual(result['serialized_order_ids'][:6], [1, 2, 3, 5, 9, 17])
        self.assertIsNone(result['ui_order_ids'])
        self.assertIn('unknown', result['ui_order_status'])
        self.assertEqual(result['lobby_hero_ids'], [])
        low_id = next(h for h in heroes if h['inventory_id'] == 176)
        self.assertEqual(low_id['config_id'], 35)
        self.assertEqual(low_id['level'], 1)
        first = heroes[0]
        self.assertTrue(first['locked'])
        self.assertFalse(first['in_storage'])
        self.assertEqual(first['relic_id_by_slot'][3], 1)
        self.assertTrue(first['skills'])
        old = legacy.decode_heroes(FIXTURES/'PlayerHeroesModel.dat')
        # Legacy implementation may be replaced by the parent integration; compare shared data.
        by_id = {h['inventory_id']: h for h in heroes}
        for hero in old:
            for name in ('config_id', 'level', 'rank', 'experience', 'total_experience'):
                self.assertEqual(hero[name], by_id[hero['inventory_id']][name])

    def test_relic_bonus_fields_and_equipment_are_structural(self):
        relics = read_relic_inventory(FIXTURES/'PlayerRelicsModel.dat')
        self.assertEqual(len(relics), 313)
        first = relics[0]
        self.assertEqual(first['inventory_id'], 1)
        self.assertEqual(first['equipped_hero_id'], 1)
        self.assertEqual((first['slot'], first['set'], first['rarity']), ('Helmet', 'Health', 'Rare'))
        self.assertEqual(first['level'], 5)
        self.assertEqual(len(first['bonuses']), 4)
        bonus = first['bonuses'][0]
        self.assertEqual((bonus['stat_bonus_id'], bonus['stat_bonus']), (3, 'HealthFlat'))
        self.assertEqual(bonus['value_raw'], 1975684956160)
        self.assertEqual(bonus['rolls_sum_raw'], 0)
        self.assertIsNone(bonus['value'])
        self.assertIn('unknown', first['value_status'])
        self.assertEqual(sum(r['equipped_hero_id'] is not None for r in relics), 56)

    def test_windows_roster_relics_and_clan(self):
        with zipfile.ZipFile(self.archive_path) as archive:
            names = {n.replace('\\', '/'): n for n in archive.namelist()}
            for group in ('A_BEFORE_ARENA', 'B_FORMATION', 'C_AFTER_BACK'):
                with self.subTest(group=group), TemporaryDirectory() as directory:
                    root = Path(directory)
                    for filename in ('PlayerHeroesModel.dat', 'PlayerRelicsModel.dat', 'PlayerClanModel.dat'):
                        (root/filename).write_bytes(archive.read(names[group + '/' + filename]))
                    roster = read_hero_roster(root/'PlayerHeroesModel.dat')
                    relics = read_relic_inventory(root/'PlayerRelicsModel.dat')
                    clan = read_clan_state(root/'PlayerClanModel.dat')
                    self.assertEqual(len(roster['heroes']), 30)
                    self.assertEqual(len(relics), 180 if self.private_profile else 313)
                    self.assertEqual(clan['membership']['role_id'], 20)
                    self.assertIsInstance(clan['membership']['clan_abbreviation'], str)
                    self.assertEqual(clan['boss2']['replays_used'], 0)
                    self.assertEqual(clan['boss2']['started_difficulties'], [])
                    self.assertEqual(clan['boss2']['best_damage_by_difficulty'], {})
                    self.assertEqual(clan['boss2']['chests'], [])
                    self.assertIsNone(clan['boss2']['current_boss_hp'])
                    self.assertIsNone(clan['pending_boss_chest'])

    def test_truncation_and_tag_mismatch_fail_closed(self):
        for filename, read in [('PlayerHeroesModel.dat', read_hero_roster),
                               ('PlayerRelicsModel.dat', read_relic_inventory)]:
            original = (FIXTURES/filename).read_bytes()
            for data in (original[:-1], b'', bytes([0]) + original[1:]):
                with self.subTest(filename=filename), TemporaryDirectory() as directory:
                    path = Path(directory)/filename
                    path.write_bytes(data)
                    with self.assertRaises(DecodeError):
                        read(path)

    def test_arena_counters_have_validated_accounting_profile(self):
        stats = read_arena_stats(FIXTURES/'PlayerArenaModel.dat')
        self.assertEqual((stats['total_offense_battles'], stats['total_offense_wins']), (13, 13))
        self.assertEqual((stats['total_defense_battles'], stats['total_defense_wins']), (8, 0))
        self.assertEqual(stats['total_battles_by_league'], {11: 20, 12: 1})
        self.assertTrue(stats['league_accounting_matches'])
        self.assertEqual(stats['unknown_fields'], [])
        self.assertIsNone(stats['last_refresh_time'])
        with zipfile.ZipFile(self.archive_path) as archive, TemporaryDirectory() as directory:
            entry = next(n for n in archive.namelist() if n.endswith('PlayerArenaModel.dat'))
            path = Path(directory)/'arena.dat'
            path.write_bytes(archive.read(entry))
            later = read_arena_stats(path)
        self.assertEqual((later['total_offense_battles'], later['total_offense_wins']), (13, 13))
        self.assertEqual(later['total_defense_battles'], 10 if self.private_profile else 8)
        self.assertEqual(later['total_battles_by_league'], {11: 22 if self.private_profile else 20, 12: 1})
        self.assertTrue(later['league_accounting_matches'])
        self.assertEqual(stats['timestamp_fields']['7'], later['timestamp_fields']['7'])
        self.assertEqual(stats['timestamp_fields']['5'] == later['timestamp_fields']['5'], not self.private_profile)

    def test_impossible_arena_wins_fail_closed(self):
        fields = [span.data for span in model((FIXTURES/'PlayerArenaModel.dat').read_bytes(), 9)]
        from memorypack import Span
        stats = [span.data for span in Span(fields[10]).object()]
        stats[9] = struct.pack('<i', 999)
        fields[10] = pack_object(stats)
        with TemporaryDirectory() as directory:
            path = Path(directory)/'arena.dat'
            path.write_bytes(envelope(9, fields))
            with self.assertRaisesRegex(DecodeError, 'wins exceed'):
                read_arena_stats(path)

    def test_all_quest_subtypes_come_from_union_not_id_ranges(self):
        from collections import Counter
        result = read_quest_states(FIXTURES/'PlayerQuestsModel.dat')
        quests = result['quests']
        self.assertEqual(len(quests), 524)
        self.assertEqual(Counter(q['kind'] for q in quests), {'Periodic': 31, 'Achievement': 489, 'Book': 4})
        self.assertEqual(Counter(q['state'] for q in quests), {'New': 517, 'Completed': 7})
        self.assertEqual(Counter(q['group'] for q in quests if q['kind'] == 'Periodic'),
                         {'Daily': 8, 'Weekly': 4, 'Monthly': 7, 'Clan': 12})
        self.assertFalse(any(q['group'] == 'Advance' for q in quests))
        self.assertEqual(set(result['periodic_groups']), {1, 2, 3, 5})
        self.assertEqual(len(result['achievement_groups']), 491)
        achievement = next(q for q in quests if q['quest_id'] == 23)
        self.assertEqual((achievement['prototype_id'], achievement['kind'], achievement['group']),
                         (1002001, 'Achievement', 'Achievements'))
        self.assertEqual(next(q['page'] for q in quests if q['quest_id'] == 533), 2)
        self.assertTrue(all(q['reward_claimable'] is None for q in quests))
        self.assertTrue(all(q['unknown_fields'] == [] for q in quests))
        self.assertEqual(len(read_quests(FIXTURES/'PlayerQuestsModel.dat')), 524)

    def test_windows_quest_subtypes_and_reward_states(self):
        from collections import Counter
        with zipfile.ZipFile(self.archive_path) as archive, TemporaryDirectory() as directory:
            entry = next(n for n in archive.namelist() if n.endswith('PlayerQuestsModel.dat'))
            path = Path(directory)/'quests.dat'
            path.write_bytes(archive.read(entry))
            result = read_quest_states(path)
        self.assertEqual(len(result['quests']), 523 if self.private_profile else 524)
        self.assertEqual(Counter(q['kind'] for q in result['quests']), {'Periodic': 31, 'Achievement': 488 if self.private_profile else 489, 'Book': 4})
        self.assertEqual(Counter(q['state'] for q in result['quests']), {'New': 518 if self.private_profile else 517, 'Completed': 5 if self.private_profile else 7})
        self.assertTrue(all(q['reward_claimable'] is None for q in result['quests'] if q['state'] == 'Completed'))

    def test_unknown_quest_subtype_does_not_gain_known_semantics(self):
        fields = [s.data for s in model((FIXTURES/'PlayerQuestsModel.dat').read_bytes(), 8)]
        payload = bytearray(fields[1])
        # Count:Int32, key:Int32, union tag byte; reuse a bounded object under an unknown tag.
        payload[8] = 42
        fields[1] = bytes(payload)
        with TemporaryDirectory() as directory:
            path = Path(directory)/'quests.dat'
            path.write_bytes(envelope(8, fields))
            result = read_quest_states(path)
        quest = result['quests'][0]
        self.assertEqual(quest['kind'], 'Unknown')
        self.assertIsNone(quest['prototype_id'])
        self.assertIsNone(quest['progress'])
        self.assertTrue(quest['unknown_fields'])
        self.assertIsNone(quest['reward_claimable'])

    def test_quest_dictionary_identity_mismatch_fails_closed(self):
        fields = [s.data for s in model((FIXTURES/'PlayerQuestsModel.dat').read_bytes(), 8)]
        payload = bytearray(fields[1])
        payload[4:8] = struct.pack('<i', 999)
        fields[1] = bytes(payload)
        with TemporaryDirectory() as directory:
            path = Path(directory)/'quests.dat'
            path.write_bytes(envelope(8, fields))
            with self.assertRaisesRegex(DecodeError, 'Quest ID disagrees'):
                read_quest_states(path)

    def test_hero_key_identity_mismatch_is_rejected(self):
        fields = [s.data for s in model((FIXTURES/'PlayerHeroesModel.dat').read_bytes(), 2)]
        dictionary = bytearray(fields[1])
        dictionary[4:8] = struct.pack('<i', 999)
        fields[1] = bytes(dictionary)
        with TemporaryDirectory() as directory:
            path = Path(directory)/'heroes.dat'
            path.write_bytes(envelope(2, fields))
            with self.assertRaises(DecodeError):
                read_hero_roster(path)

    def test_relic_equipment_cross_links_match_hero_maps(self):
        heroes = read_hero_roster(FIXTURES/'PlayerHeroesModel.dat')['heroes']
        relics = {r['inventory_id']: r for r in read_relic_inventory(FIXTURES/'PlayerRelicsModel.dat')}
        for hero in heroes:
            for slot, relic_id in hero['relic_id_by_slot'].items():
                relic = relics[relic_id]
                self.assertEqual(relic['slot_id'], slot)
                self.assertEqual(relic['equipped_hero_id'], hero['inventory_id'])


if __name__ == '__main__':
    unittest.main()
