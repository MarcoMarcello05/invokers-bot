"""Arena actor v4: PlayerArenaModel decides; screen is navigation/confirmation only."""
from __future__ import annotations
import json,re,time
from pathlib import Path
import pyautogui
from arena_snapshot import read_opponents, signature, wait_for_change
try:
 from rapidocr_onnxruntime import RapidOCR
 OCR=RapidOCR()
except Exception: OCR=None
ROOT=Path(__file__).resolve().parent; RUNTIME=ROOT/'runtime'; STATE=RUNTIME/'arena_state.json'
MAX_REFRESHES_PER_JOB=3; MIN_CONF=.55; MAX_SCROLL_STEPS=14; SCROLL_CLICKS=5

def _load():
 try:return json.loads(STATE.read_text(encoding='utf-8'))
 except:return {'refreshes':0,'losses':{},'last_opponent':None}
def _save(s): RUNTIME.mkdir(exist_ok=True); STATE.write_text(json.dumps(s,indent=2,ensure_ascii=False),encoding='utf-8')
def reset_job(): s=_load(); s['refreshes']=0; s['session_rejected']=[]; _save(s)

def _ocr_screen():
 if OCR is None:return []
 im=pyautogui.screenshot(); import numpy as np
 a=np.array(im); gray=(a[:,:,0]*.299+a[:,:,1]*.587+a[:,:,2]*.114).astype('uint8')
 try:r=OCR(gray); r=r[0] if isinstance(r,tuple) else r
 except:return []
 out=[]
 for item in r or []:
  try:
   box,t,c=item; c=float(c)
   if c<MIN_CONF:continue
   xs=[p[0] for p in box]; ys=[p[1] for p in box]
   out.append({'text':str(t).strip(),'conf':c,'x':int(sum(xs)/len(xs)),'y':int(sum(ys)/len(ys))})
  except:pass
 return out

def _norm(s): return re.sub(r'[^a-z0-9]','',str(s).lower())
def _match_score(name,text):
 a,b=_norm(name),_norm(text)
 if len(a)<3 or len(b)<3:return 0
 if a==b:return 100
 if a in b or b in a:return 85-min(abs(len(a)-len(b)),20)
 # tolerate OCR dropping clan tags/punctuation: compare suffix/prefix chunks
 if len(a)>=5 and len(b)>=5 and (a[-5:]==b[-5:] or a[:5]==b[:5]):return 65
 return 0

def locate_name(name, rows):
 c=[]
 for r in rows:
  sc=_match_score(name,r['text'])
  if sc:c.append((sc,r['conf'],r))
 return max(c,key=lambda z:(z[0],z[1]))[2] if c else None

def visible_snapshot_items(items,rows):
 out=[]
 for x in items:
  hit=locate_name(x['name'],rows)
  if hit:
   y=hit['y']
   # arena opponent rows live in the central/right list, not top HUD
   if y>180:
    z=dict(x); z['screen_y']=y; z['screen_x']=hit['x']; z['ocr_text']=hit['text']; z['ocr_conf']=hit['conf']; out.append(z)
 return out

def locate_refresh(rows):
 c=[r for r in rows if 'aktualisier' in _norm(r['text']) or 'refresh' in _norm(r['text'])]
 return max(c,key=lambda r:r['conf']) if c else None

def ranked_candidates(items):
 s=_load(); losses=s.get('losses',{}); rejected=set(s.get('session_rejected',[]))
 ok=[x for x in items if int(losses.get(x['name'],0))<1 and x['name'] not in rejected]
 return sorted(ok,key=lambda x:(x['combat_power'],x['arena_points'],x['name'].lower()))

def parse_own_power(rows):
 labels=[r for r in rows if 'starke' in _norm(r['text'])]
 nums=[]
 for r in rows:
  t=r['text'].replace(' ','')
  if re.fullmatch(r'\d{1,3}(?:\.\d{3})+',t): nums.append((int(t.replace('.','')),r))
  elif re.fullmatch(r'\d{4,6}',t): nums.append((int(t),r))
 if not labels:return None
 cand=[]
 for v,r in nums:
  if not 500<=v<=1000000:continue
  d=min(abs(r['x']-l['x'])+abs(r['y']-l['y']) for l in labels)
  if d<280:cand.append((d,-r['conf'],v))
 return min(cand)[2] if cand else None

def _scroll(direction):
 w,h=pyautogui.size(); pyautogui.moveTo(int(w*.70),int(h*.63),duration=.08)
 pyautogui.scroll(SCROLL_CLICKS if direction=='up' else -SCROLL_CLICKS)
 time.sleep(.45)

def find_candidate_on_scrollable_list(items, dry=True):
    """Search candidates in DATA priority order. Never substitute a merely-visible stronger opponent."""
    candidates=ranked_candidates(items)
    if not candidates:return None,[],{'reason':'no_snapshot_candidates'}
    all_visible={}
    searched=[]
    # Each candidate gets a complete bounded list search. This is slower than picking the
    # weakest *visible* row, but preserves the planner decision and is safe.
    for cand in candidates:
        searched.append(cand['name'])
        seen_screens=set()
        # Normalize position: first reach the top, then search downward. Starting from an
        # arbitrary scroll position otherwise makes a down->up pass easy to terminate early.
        stable=0; last_sig=None
        for _ in range(MAX_SCROLL_STEPS+1):
            rows=_ocr_screen(); visible=visible_snapshot_items(items,rows)
            sig=tuple(sorted((x['name'],x['screen_y']) for x in visible))
            for x in visible: all_visible[x['name']]=x
            if sig==last_sig: stable+=1
            else: stable=0
            last_sig=sig
            if stable>=2: break
            _scroll('up')
        stable=0; last_sig=None
        for step in range(MAX_SCROLL_STEPS+1):
            rows=_ocr_screen(); visible=visible_snapshot_items(items,rows)
            sig=tuple(sorted((x['name'],x['screen_y']) for x in visible))
            for x in visible: all_visible[x['name']]=x
            hit=next((x for x in visible if x['name']==cand['name']),None)
            if hit:
                return hit,list(all_visible.values()),{'target':cand['name'],'direction':'down','steps':step,'candidates_tried':len(searched),'searched_names':searched}
            if sig==last_sig: stable+=1
            else: stable=0
            last_sig=sig; seen_screens.add(sig)
            if stable>=2: break
            _scroll('down')
    return None,list(all_visible.values()),{'reason':'candidate_not_found_after_scroll','candidates_tried':len(searched),'searched_names':searched}

def dry_run():
 items=read_opponents()
 if not items:return {'status':'SAFE_STOP','reason':'arena_snapshot_no_opponents'}
 pick,seen,meta=find_candidate_on_scrollable_list(items,dry=True)
 return {'status':'WOULD_PROBE_CANDIDATE' if pick else 'NO_CANDIDATE_FOUND','candidate':pick,
         'snapshot_count':len(items),'seen_count':len(seen),'search':meta,
         'weakest_snapshot':ranked_candidates(items)[:5]}

def _reject_for_session(name):
 s=_load(); a=s.setdefault('session_rejected',[])
 if name not in a:a.append(name)
 _save(s)

def live_once(log=print):
 items=read_opponents()
 if not items:return {'status':'SAFE_STOP','reason':'arena_snapshot_no_opponents'}
 pick,seen,meta=find_candidate_on_scrollable_list(items,dry=False)
 if not pick:return {'status':'NEED_REFRESH','reason':'no_candidate_found_on_scrollable_list','search':meta}
 rows=_ocr_screen(); hit=locate_name(pick['name'],rows)
 if not hit:return {'status':'SAFE_STOP','reason':'candidate_disappeared_before_click','candidate':pick}
 # click KÄMPFEN on same row; x is stable relative to game window width
 w,h=pyautogui.size(); pyautogui.click(int(w*.91),hit['y']); time.sleep(1.4)
 rows2=_ocr_screen(); own=parse_own_power(rows2)
 if own is None:
  pyautogui.hotkey('alt','left'); time.sleep(.8)
  return {'status':'SAFE_STOP','reason':'own_power_not_confirmed','candidate':pick}
 if pick['combat_power'] >= own:
  pyautogui.hotkey('alt','left'); time.sleep(.8); _reject_for_session(pick['name'])
  return {'status':'CANDIDATE_TOO_STRONG','own_power':own,'candidate':pick}
 # bottom-right formation fight button
 pyautogui.click(int(w*.83),int(h*.88)); s=_load(); s['last_opponent']=pick; _save(s)
 return {'status':'BATTLE_STARTED','own_power':own,'candidate':pick}

def refresh_live():
 s=_load()
 if s.get('refreshes',0)>=MAX_REFRESHES_PER_JOB:return {'status':'SAFE_STOP','reason':'refresh_limit'}
 # Return near top so refresh control is visible.
 for _ in range(5): _scroll('up')
 old=read_opponents(); oldsig=signature(old); rows=_ocr_screen(); r=locate_refresh(rows)
 if not r:return {'status':'SAFE_STOP','reason':'refresh_button_not_found'}
 pyautogui.click(r['x'],r['y']); s['refreshes']=s.get('refreshes',0)+1; s['session_rejected']=[]; _save(s)
 new=wait_for_change(oldsig,8.0)
 if not new:return {'status':'SAFE_STOP','reason':'snapshot_did_not_change_after_refresh','refreshes':s['refreshes']}
 return {'status':'REFRESHED','refreshes':s['refreshes'],'opponent_count':len(new),'weakest':ranked_candidates(new)[:5]}

def record_result(win:bool):
 s=_load(); p=s.get('last_opponent')
 if p and not win:s.setdefault('losses',{})[p['name']]=int(s.setdefault('losses',{}).get(p['name'],0))+1
 if win:s['refreshes']=0
 _save(s)
