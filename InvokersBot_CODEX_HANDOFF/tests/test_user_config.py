from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from user_config import ConfigError, ModuleConfig, UserConfig


class UserConfigTests(unittest.TestCase):
    def test_defaults_have_no_guessed_power_or_main_six_and_cannot_enable_live(self):
        config = UserConfig()
        self.assertIsNone(config.arena_combat_power)
        self.assertEqual(config.main_six_ids, [])
        self.assertFalse(config.modules.automation)
        self.assertEqual(config.mode, 'DRY_RUN')
        self.assertFalse(config.actor_enabled)
        self.assertTrue(config.module_enabled('arena'))
        self.assertFalse(config.module_enabled('arena', require_automation=True))
        for forbidden in ('actor_enabled', 'allow_gems', 'allow_premium_spend', 'mode'):
            with self.subTest(forbidden=forbidden), self.assertRaises(ConfigError):
                UserConfig.from_dict({forbidden: True})

    def test_manual_power_modules_order_and_reserves_roundtrip(self):
        config = UserConfig(arena_combat_power=9368, main_six_ids=[1, 2, 3, 5, 9, 17],
                            modules=ModuleConfig(automation=True, arena=False),
                            resource_reserves={'Energy': 50, 'Gold': 1000}, main_team_interval_seconds=180)
        with TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            config.save(path)
            loaded = UserConfig.load(path)
            self.assertEqual(loaded.to_dict(), config.to_dict())
            self.assertEqual(loaded.arena_combat_power, 9368)
            self.assertFalse(loaded.module_enabled('arena'))
            self.assertTrue(loaded.module_enabled('quests', require_automation=True))
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])

    def test_reject_invalid_types_and_values(self):
        for data in ({'arena_combat_power': True}, {'arena_combat_power': 0}, {'arena_combat_power': 3.5},
                     {'arena_combat_power': '9368'}, {'main_six_ids': [1, 2]},
                     {'main_six_ids': [1, 2, 3, 4, 5, 5]}, {'main_six_ids': [1, 2, 3, 4, 5, True]},
                     {'modules': {'arena': 'false'}}, {'modules': {'shop': True}},
                     {'resource_reserves': {'Energy': -1}}, {'resource_reserves': {'Energy': False}},
                     {'main_team_interval_seconds': 0}, {'game_root': ''}, {'schema_version': True}):
            with self.subTest(data=data), self.assertRaises(ConfigError):
                UserConfig.from_dict(data)

    def test_failed_atomic_replace_keeps_previous_file(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            UserConfig(arena_combat_power=100).save(path)
            original = path.read_bytes()
            with patch('user_config.os.replace', side_effect=OSError('disk error')), self.assertRaises(OSError):
                UserConfig(arena_combat_power=200).save(path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])

    def test_missing_returns_defaults_but_invalid_file_is_not_replaced(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            self.assertIsNone(UserConfig.load(path).arena_combat_power)
            self.assertFalse(path.exists())
            path.write_text('{bad')
            with self.assertRaises(ConfigError):
                UserConfig.load(path)
            self.assertEqual(path.read_text(), '{bad')


if __name__ == '__main__':
    unittest.main()
