import sys,types
pg=types.ModuleType('pyautogui'); pg.FAILSAFE=True; pg.PAUSE=0; sys.modules['pyautogui']=pg
sys.path.insert(0,'/mnt/data/workdeep/v4')
import arena_actor as a
items=[{'name':'Vinescia98','combat_power':2522,'arena_points':454},{'name':'Ellesher','combat_power':11141,'arena_points':685}]
screens=[
 [{'text':'Ellesher','conf':.99,'x':700,'y':400}], # top seek
 [{'text':'Ellesher','conf':.99,'x':700,'y':400}],
 [{'text':'Ellesher','conf':.99,'x':700,'y':400}],
 [{'text':'Ellesher','conf':.99,'x':700,'y':400}], # search down first
 [{'text':'Vinescia98','conf':.99,'x':700,'y':600}],
]
def ocr(): return screens.pop(0) if screens else [{'text':'Vinescia98','conf':.99,'x':700,'y':600}]
a._ocr_screen=ocr; a._scroll=lambda d: None; a.MAX_SCROLL_STEPS=4
pick,seen,meta=a.find_candidate_on_scrollable_list(items,True)
assert pick['name']=='Vinescia98',(pick,meta)
assert pick['combat_power']==2522
print('PASS target-priority:',pick['name'],pick['combat_power'],meta)
