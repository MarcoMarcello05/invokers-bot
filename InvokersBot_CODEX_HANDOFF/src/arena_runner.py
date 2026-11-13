from __future__ import annotations
import sys
import pyautogui
from arena_actor import dry_run, live_once, refresh_live
pyautogui.FAILSAFE=True
mode=(sys.argv[1].lower() if len(sys.argv)>1 else 'dry')
print('Arena Actor v4 | DATA decides -> scroll finds name -> own power verifies | mouse corner emergency stop')
try:
 if mode!='live': r=dry_run()
 else:
  r=live_once()
  if r.get('status')=='NEED_REFRESH':
   rr=refresh_live(); print(rr)
   r=live_once() if rr.get('status')=='REFRESHED' else rr
 print(r)
except Exception as e: print({'status':'ERROR','error':repr(e)})
input('Enter...')
