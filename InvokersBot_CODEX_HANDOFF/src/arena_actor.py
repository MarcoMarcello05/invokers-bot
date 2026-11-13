"""Arena actor v4: PlayerArenaModel decides; screen is navigation/confirmation only."""
from __future__ import annotations
import json,re,time
from pathlib import Path
pyautogui=None
from arena_snapshot import read_opponents, signature, wait_for_change
OCR=None

def _ensure_desktop():
 global pyautogui,OCR
 if pyautogui is None:
  import pyautogui as pg
  pyautogui=pg;pyautogui.FAILSAFE=True
 if OCR is None:
  from rapidocr_onnxruntime import RapidOCR
  OCR=RapidOCR()

ROOT=Path(__file__).resolve().parent; RUNTIME=ROOT/'runtime'; STATE=RUNTIME/'arena_state.json'
MAX_REFRESHES_PER_JOB=3; MIN_CONF=.55; MAX_SCROLL_STEPS=14; SCROLL_CLICKS=5

def _load():
 try:return json.loads(STATE.read_text(encoding='utf-8'))
 except:return {'refreshes':0,'losses':{},'last_opponent':None}
def _save(s): RUNTIME.mkdir(exist_ok=True); STATE.write_text(json.dumps(s,indent=2,ensure_ascii=False),encoding='utf-8')
def reset_job(): s=_load(); s['refreshes']=0; s['session_rejected']=[]; _save(s)

def _ocr_screen():
 _ensure_desktop()
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

def _norm(s):
 import unicodedata
 s=re.sub(r'^\s*\[[^]]+\]\s*','',str(s))
 return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if c.isalnum())

def _match_score(name,text):
 a,b=_norm(name),_norm(text)
 return 100 if a and a==b else 0

def locate_name(name, rows):
 matches=[r for r in rows if _match_score(name,r.get('text','')) and r.get('conf',0)>=.85]
 return matches[0] if len(matches)==1 else None


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
 _ensure_desktop()
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
 return {'status':'SAFE_STOP','reason':'Legacy live execution retired; use the tested Actor/Verification boundary. No production handler is enabled.'}

def refresh_live():
 return {'status':'SAFE_STOP','reason':'Legacy refresh retired; verified costs and current-field-12 reread are required.'}


def record_result(win:bool):
 s=_load(); p=s.get('last_opponent')
 if p and not win:s.setdefault('losses',{})[p['name']]=int(s.setdefault('losses',{}).get(p['name'],0))+1
 if win:s['refreshes']=0
 _save(s)


def search_selected_candidate(candidate, observe, scroll, stopped=lambda:False, max_steps=14):
    """Handoff top-normalization + bounded downward pass for one planned target.

    Never substitutes a stronger visible opponent. observe must return a verified
    list-screen observation; caller owns state/modal/foreground validation.
    """
    if not 0 <= max_steps <= 30:
        raise ValueError('Scroll limit must be between 0 and 30')
    seen=[]
    for direction in ('up','down'):
        stable=0;previous=None
        for step in range(max_steps+1):
            if stopped():return None,{'reason':'STOP_REQUESTED','screens':len(seen)}
            view=observe()
            rows=view.rows
            signature=tuple(sorted((str(r.get('text','')),r.get('x'),r.get('y')) for r in rows))
            seen.append(signature)
            hit=locate_name(candidate['name'],rows)
            # Search the selected candidate even while normalizing to the top.
            if hit:return (view,hit),{'direction':direction,'steps':step,'screens':len(seen)}
            stable=stable+1 if signature==previous else 0
            previous=signature
            if stable>=2:break
            if step<max_steps:scroll(direction)
    return None,{'reason':'TARGET_NOT_FOUND','screens':len(seen)}
