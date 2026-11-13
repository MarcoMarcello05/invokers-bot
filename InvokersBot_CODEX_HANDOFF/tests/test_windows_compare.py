from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from compare_snapshots import ComparisonError, compare_archive
from game_state import MODEL_TAGS, build_game_state
from memorypack import model
from arena_snapshot import read_opponents

from fixture_support import comparison_fixture


class WindowsComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_context=comparison_fixture()
        cls.archive_path,cls.private_profile=cls.fixture_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.fixture_context.__exit__(None,None,None)

    def test_manifest_integrity_and_actual_bytes_match_across_all_captures(self):
        report = compare_archive(self.archive_path)
        self.assertEqual(report['manifest_copies_verified'], 36)
        self.assertEqual(len(report['captures']), 3)
        self.assertEqual(len(report['comparisons']), 3)
        for comparison in report['comparisons']:
            self.assertEqual(comparison['changed'], [])
            self.assertEqual(comparison['added'], [])
            self.assertEqual(comparison['removed'], [])
            self.assertEqual(len(comparison['unchanged']), 12)

    def test_tampered_model_rejected_against_manifest(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'tampered.zip'
            with zipfile.ZipFile(self.archive_path) as source, zipfile.ZipFile(path, 'w') as target:
                for entry in source.infolist():
                    data = source.read(entry)
                    if entry.filename.replace('\\', '/') == 'B_FORMATION/PlayerBattleModel.dat':
                        data = data[:-1] + bytes([data[-1] ^ 1])
                    target.writestr(entry.filename, data)
            with self.assertRaisesRegex(ComparisonError, 'Manifest mismatch'):
                compare_archive(path)

    def test_new_capture_profile_and_unknowns_regressions(self):
        with zipfile.ZipFile(self.archive_path) as archive:
            entries = {n.replace('\\', '/'): n for n in archive.namelist()}
            for group in ('A_BEFORE_ARENA', 'B_FORMATION', 'C_AFTER_BACK'):
                with self.subTest(group=group), TemporaryDirectory() as directory:
                    root = Path(directory)
                    for name in MODEL_TAGS:
                        (root/name).write_bytes(archive.read(entries[group + '/' + name]))
                    state = build_game_state(root, static_path=ROOT/'raw/static/static-data.0.62.1655(1).dat')
                    for name in ('resources', 'campaign', 'arena', 'events', 'heroes', 'quests', 'relics'):
                        self.assertEqual(getattr(state, name).status, 'available')
                    arena = state.arena.value
                    self.assertIsNone(arena['own_combat_power']['value'])
                    self.assertFalse(arena['last_meta_battle_setup_present'])
                    self.assertEqual(arena['own_combat_power']['offset'], 47080 if self.private_profile else 46805)
                    self.assertEqual([s['hero_inventory_id'] for s in arena['attack_preset']['slots']], [166, 5, 167, 2])
                    self.assertEqual(arena['unresolved_hero_inventory_ids'], [])
                    collections = arena['opponent_collections']
                    self.assertEqual([len(c['records']) for c in collections], [10, 23 if self.private_profile else 21])
                    self.assertEqual([c['role'] for c in collections], ['current', 'other_stored'])
                    candidates = read_opponents(root/'PlayerArenaModel.dat')
                    self.assertEqual(len(candidates), 10)
                    self.assertEqual(candidates, collections[0]['records'])
                    self.assertNotIn('Vinescia98', {r['name'] for r in candidates})
                    self.assertEqual(min(r['combat_power'] for r in collections[0]['records']), 2500 if self.private_profile else 3567)
                    self.assertEqual(min(collections[1]['records'], key=lambda r: r['combat_power'])['name'], 'Vinescia98')
                    player_id = model((root/'PlayerModel.dat').read_bytes(), 1)[0].data.hex()
                    self.assertFalse(any(r['player_id_bytes'] == player_id for c in collections for r in c['records']))
                    self.assertEqual((len(state.heroes.value), len(state.quests.value), len(state.relics.value)), (30, 523 if self.private_profile else 524, 180 if self.private_profile else 313))
                    events = {r['tournament_id']: r for r in state.events.value['tournaments']}
                    self.assertEqual(events[935]['points'], 52880 if self.private_profile else 50700)
                    self.assertEqual(events[939]['points'], 88926 if self.private_profile else 86550)
                    self.assertEqual({r['union_tag'] for r in events.values()}, {1, 2, 3})
                    current = state.resources.value['current']['values']
                    gained = state.resources.value['gained']['values']
                    spent = state.resources.value['spent']['values']
                    for name in ('Gold', 'Energy', 'Memorium', 'Arena_Token', 'SI_WildStar'):
                        self.assertEqual(gained[name] - spent[name], current[name])


if __name__ == '__main__':
    unittest.main()
