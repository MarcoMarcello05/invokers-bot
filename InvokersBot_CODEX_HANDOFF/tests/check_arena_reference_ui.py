"""Offline OCR/template smoke; no desktop capture/input, using existing repo images."""
from pathlib import Path
import sys
import types
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    # Reuse screen_actor's OCR/templates while excluding the physical input module.
    pg=types.ModuleType('pyautogui');pg.FAILSAFE=True;pg.PAUSE=.1
    previous=sys.modules.get('pyautogui')
    sys.modules['pyautogui']=pg
    try:
        import screen_actor_v8 as screen
    finally:
        if previous is None:sys.modules.pop('pyautogui',None)
        else:sys.modules['pyautogui']=previous
    from arena_windows import DEFAULT_PROFILE,WindowsArenaDesktop
    backend=WindowsArenaDesktop.__new__(WindowsArenaDesktop)
    backend.screen=screen;backend.profile=DEFAULT_PROFILE
    backend.pg=types.SimpleNamespace(size=lambda:(1920,1080))
    backend.stopped=lambda:False;backend.foreground=lambda:True
    for name,state in [('arena_list.png','ARENA_LIST'),('arena_formation.png','FORMATION')]:
        image=screen.cv2.imread(str(ROOT/'reference/screenshots'/name),0)
        if image is None:raise RuntimeError('Reference images unavailable; run this smoke from the Git checkout')
        with patch.object(screen,'shot',return_value=image):frame=backend.observe()
        assert frame.state==state,(name,frame.state)
        if state=='FORMATION':
            assert frame.own_power==9368
            assert frame.selected_name=='oryius'
            assert frame.token_cost==1 and frame.token_currency_verified
            assert frame.controls.get('back') and frame.controls.get('start_battle')
        print(name+': OCR/state/token checks passed (offline image, no Windows input)',flush=True)
    # A marker-free image must not accidentally become an actionable game screen.
    import numpy as np
    with patch.object(screen,'shot',return_value=np.zeros((1080,1920),dtype=np.uint8)):
        assert backend.observe().state=='UNKNOWN'
    print('Blank/unknown image rejected',flush=True)


if __name__=='__main__':main()
