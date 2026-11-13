"""Fail-closed geometry tests; runnable on Linux without Windows input."""
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena_windows import validate_client_geometry, WindowsArenaDesktop
from arena_autopilot import ArenaError


class ClientGeometryTests(unittest.TestCase):
    def test_exact_client_bounds_accepted(self):
        self.assertEqual(validate_client_geometry((0, 0, 1920, 1080), [1920, 1080], (1920, 1080)),
                         (0, 0, 1920, 1080))

    def test_client_size_and_position_fail_closed(self):
        cases = [
            ((0, 0, 1900, 1080), (1920, 1080)),
            ((8, 0, 1928, 1080), (1920, 1080)),
            ((0, -5, 1920, 1075), (1920, 1080)),
            ((0, 0, 1920, 1080), (1600, 900)),
        ]
        for rect, desktop in cases:
            with self.subTest(rect=rect, desktop=desktop):
                with self.assertRaises(ArenaError):
                    validate_client_geometry(rect, [1920, 1080], desktop)

    def test_clicks_translated_only_inside_verified_client_and_region(self):
        adapter = object.__new__(WindowsArenaDesktop)
        adapter.profile = {'size': [1920, 1080],
                           'regions': {'row_fight': [1610, 290, 1880, 1020]}}
        adapter._verified_geometry = Mock(return_value=(123, (0, 0, 1920, 1080)))
        self.assertEqual(adapter._screen_point((1700, 500), 'row_fight'), (1700, 500))
        for point in [(-1, 500), (1920, 500), (1700, 1080), (1500, 500)]:
            with self.subTest(point=point):
                with self.assertRaises(ArenaError):
                    adapter._screen_point(point, 'row_fight')


if __name__ == '__main__':
    unittest.main()
