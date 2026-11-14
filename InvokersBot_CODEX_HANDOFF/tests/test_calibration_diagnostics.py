import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from calibration_diagnostics import compare_geometry
from arena_windows import DEFAULT_PROFILE
from recognition_benchmark import benchmark


class DiagnosticTests(unittest.TestCase):
    def test_maximized_desktop_is_not_client(self):
        result=compare_geometry((1920,1080),(0,30,1920,1040),DEFAULT_PROFILE)
        self.assertFalse(result['matches_size'])
        self.assertEqual(result['client_size'],[1920,1010])
        self.assertEqual(result['size_delta'],[0,-70])
        self.assertTrue(result['inside_primary_desktop'])

    def test_offscreen_client_is_reported(self):
        self.assertFalse(compare_geometry((1920,1080),(-1,0,1919,1080),DEFAULT_PROFILE)['inside_primary_desktop'])

    def test_synthetic_scale_matching(self):
        fixed,multi=benchmark()
        self.assertEqual(multi['tp'],30)
        self.assertEqual(multi['fp'],0)
        self.assertGreater(multi['tp'],fixed['tp'])


if __name__=='__main__':
    unittest.main()
