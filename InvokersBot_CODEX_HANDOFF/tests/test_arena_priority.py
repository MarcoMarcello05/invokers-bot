from pathlib import Path
import importlib.util
import sys,types,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

class ArenaPriorityTests(unittest.TestCase):
    def test_searches_for_weakest_even_when_stronger_is_visible(self):
        pg=types.ModuleType('pyautogui'); pg.FAILSAFE=True; pg.PAUSE=0
        with patch.dict(sys.modules,{'pyautogui':pg,'rapidocr_onnxruntime':None}):
            spec=importlib.util.spec_from_file_location('arena_priority_under_test',ROOT/'src/arena_actor.py')
            actor=importlib.util.module_from_spec(spec); spec.loader.exec_module(actor)
        items=[{'name':'Vinescia98','combat_power':2522,'arena_points':454},{'name':'Ellesher','combat_power':11141,'arena_points':685}]
        strong=[{'text':'Ellesher','conf':.99,'x':700,'y':400}]
        weak=[{'text':'Vinescia98','conf':.99,'x':700,'y':600}]
        screens=[strong]*4+[weak]
        with patch.object(actor,'_ocr_screen',side_effect=lambda:screens.pop(0) if screens else weak), patch.object(actor,'_scroll'), patch.object(actor,'MAX_SCROLL_STEPS',4), patch.object(actor,'_load',return_value={'losses':{},'session_rejected':[]}):
            pick,seen,meta=actor.find_candidate_on_scrollable_list(items,True)
        self.assertEqual((pick['name'],pick['combat_power']),('Vinescia98',2522))

if __name__=='__main__': unittest.main()
