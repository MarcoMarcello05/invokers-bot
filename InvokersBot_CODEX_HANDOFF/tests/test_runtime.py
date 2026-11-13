from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from runtime import main
from user_config import UserConfig, ModuleConfig


class RuntimeTests(unittest.TestCase):
    def test_cli_persists_baseline_and_reloads_manual_config_without_live_permission(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            config_path=root/'config.json';output=root/'plan.json';state_output=root/'state.json'
            config=UserConfig(game_root=str(ROOT/'tests/fixtures'),
                              static_path=str(ROOT/'raw/static/static-data.0.62.1655(1).dat'),
                              arena_combat_power=9368,main_six_ids=[1,2,3,5,9,17],
                              modules=ModuleConfig(automation=True))
            config.save(config_path)
            args=['--once','--config',str(config_path),'--output',str(output),'--state-output',str(state_output)]
            with redirect_stderr(StringIO()):self.assertEqual(main(args),0)
            first=json.loads(output.read_text());baseline=(root/'failure_memory.json').read_bytes()
            self.assertEqual(first['game_state']['arena']['value']['own_combat_power']['value'],9368)
            self.assertTrue(first['automation_requested'])
            self.assertFalse(first['actor_enabled'])
            self.assertFalse(first['runtime_gates']['production_handlers_enabled'])
            self.assertIn(first['execution_preview']['status'],('blocked','planned'))
            config.arena_combat_power=1;config.save(config_path)
            with redirect_stderr(StringIO()):self.assertEqual(main(args),0)
            second=json.loads(output.read_text())
            self.assertEqual(second['game_state']['arena']['value']['own_combat_power']['value'],1)
            self.assertEqual((root/'failure_memory.json').read_bytes(),baseline)
            self.assertFalse(any(j['kind']=='ARENA_BATTLE' for j in second['queue']))
            self.assertEqual(json.loads(state_output.read_text())['schema_version'],2)

    def test_invalid_config_stops_and_preserves_prior_plan(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);path=root/'config.json';output=root/'plan.json'
            path.write_text('{invalid');output.write_text('previous-good-plan')
            with redirect_stderr(StringIO()):result=main(['--once','--config',str(path),'--output',str(output)])
            self.assertEqual(result,2)
            self.assertEqual(path.read_text(),'{invalid')
            self.assertEqual(output.read_text(),'previous-good-plan')

    def test_legacy_live_launcher_cannot_bypass_new_actor(self):
        result=subprocess.run([sys.executable,str(ROOT/'src/arena_runner.py'),'--live'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('disabled',result.stdout)


if __name__=='__main__':unittest.main()
