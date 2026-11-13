import time,threading,tkinter as tk,ctypes,re
from pathlib import Path
from dataclasses import dataclass
from enum import Enum,auto
import cv2,numpy as np,pyautogui
try:
 from rapidocr_onnxruntime import RapidOCR
 OCR_ENGINE=RapidOCR()
except Exception:
 OCR_ENGINE=None
from config import *
from knowledge_engine import Knowledge
from agents import AgentManager
KNOWLEDGE=Knowledge(); ROOT=Path(__file__).resolve().parent; T=ROOT/'templates'; LOG=ROOT/'bot.log'; RUN=True
pyautogui.FAILSAFE=True; pyautogui.PAUSE=.12

# v8: screen first, action second. No icon or unknown-screen click path.
TPL={
 'home_fight':('home_fight.png',.90),'home_quests':('home_quests.png',.82),
 'quest_screen':('quest_screen.png',.82),
 'quest_next':('quest_next_page_verified.png',.82),
 'back':('back.png',.86),'campaign_card':('campaign_card.png',.85),'next_level_map':('next_level_map.png',.86),
 'fight_level':('fight_level.png',.88),'fight_team':('fight_team.png',.88),'auto_off':('auto_off.png',.79),
 'victory':('victory.png',.86),'next_level_result':('next_level_result.png',.86),
 'profile':('profile_screen.png',.81),
 'green_star':('green_star.png',.86),'summon10':('summon_10_green.png',.88),'summon1':('summon_1_green.png',.88),
 'auto_select':('auto_select.png',.86),'level_button':('level_button.png',.86),
 'filter_screen':('filter_screen.png',.86),'filter_sort':('filter_sort.png',.86)
}
class Screen(Enum): UNKNOWN=auto(); HOME=auto(); QUESTS=auto(); PROFILE=auto(); CAMPAIGN=auto(); LEVEL_SELECT=auto(); TEAM=auto(); BATTLE=auto(); VICTORY=auto(); DEFEAT_BANNER=auto(); DEFEAT_RESULT=auto(); SUMMON=auto(); LEVELUP=auto(); FILTER=auto(); INVOKER_LIST=auto()
@dataclass
class Match: x:int; y:int; score:float

def log(m):
 line=time.strftime('[%H:%M:%S] ')+m; print(line,flush=True)
 with LOG.open('a',encoding='utf-8') as f:f.write(line+'\n')
 UI['action']=m[:100]
def shot(): return cv2.cvtColor(np.array(pyautogui.screenshot()),cv2.COLOR_RGB2GRAY)
def match(k,s,region=None):
 fn,th=TPL[k]; tp=cv2.imread(str(T/fn),0)
 if tp is None:return None
 x0=y0=0; roi=s
 if region:
  x1,y1,x2,y2=region; roi=s[y1:y2,x1:x2]; x0,y0=x1,y1
 if roi.shape[0]<tp.shape[0] or roi.shape[1]<tp.shape[1]:return None
 r=cv2.matchTemplate(roi,tp,cv2.TM_CCOEFF_NORMED); _,sc,_,pt=cv2.minMaxLoc(r)
 if float(sc)<th:return None
 h,w=tp.shape; return Match(x0+pt[0]+w//2,y0+pt[1]+h//2,float(sc))
def click(m,label,wait=1.3): pyautogui.click(m.x,m.y); log(label); time.sleep(wait)

def classify(s):
 # Highly specific result/modal states first.
 if match('victory',s): return Screen.VICTORY
 if match('profile',s,(1690,110,1920,430)): return Screen.PROFILE
 if match('filter_screen',s): return Screen.FILTER
 if match('quest_screen',s): return Screen.QUESTS
 if match('fight_team',s): return Screen.TEAM
 if match('fight_level',s): return Screen.LEVEL_SELECT
 if match('auto_off',s): return Screen.BATTLE
 if match('home_fight',s): return Screen.HOME
 if match('green_star',s): return Screen.SUMMON
 if match('auto_select',s) or match('level_button',s): return Screen.LEVELUP
 if match('filter_sort',s): return Screen.INVOKER_LIST
 if match('next_level_map',s) or match('campaign_card',s): return Screen.CAMPAIGN
 return Screen.UNKNOWN

def ocr_region(s,region):
 if OCR_ENGINE is None:return []
 x1,y1,x2,y2=region; crop=s[y1:y2,x1:x2]
 try:
  raw=OCR_ENGINE(crop); result=raw[0] if isinstance(raw,tuple) else raw
 except Exception as e: log('🔤 OCR Fehler: '+repr(e)); return []
 out=[]
 for item in result or []:
  try:
   box,text,score=item; score=float(score)
   if score<OCR_MIN_CONFIDENCE: continue
   xs=[float(p[0]) for p in box]; ys=[float(p[1]) for p in box]
  except Exception: continue
  out.append({'text':str(text).strip(),'x':int(sum(xs)/len(xs))+x1,'y':int(sum(ys)/len(ys))+y1,'score':score,
              'x1':int(min(xs))+x1,'x2':int(max(xs))+x1,'y1':int(min(ys))+y1,'y2':int(max(ys))+y1})
 return out

def ocr_rows(s):
 # Navigation links is part of the quest UI. Keep it in OCR; quest text filtering happens in text_near().
 return ocr_region(s,(0,80,1885,1010))
def norm(t): return re.sub(r'[^A-ZÄÖÜ0-9]+','',str(t).upper())
def word(rows,*words,region=None):
 wanted={norm(w) for w in words}
 cand=[]
 for r in rows:
  if region:
   x1,y1,x2,y2=region
   if not (x1<=r['x']<=x2 and y1<=r['y']<=y2): continue
  n=norm(r['text'])
  # Exact OCR remains the default. Only German umlaut transliterations are accepted aliases.
  aliases={n,n.replace('Ä','A').replace('Ö','O').replace('Ü','U')}
  wanted_alias={w.replace('Ä','A').replace('Ö','O').replace('Ü','U') for w in wanted}
  if aliases & (wanted|wanted_alias): cand.append(r)
 return max(cand,key=lambda z:z['score']) if cand else None

def left_progress(rows):
 # OCR may return the two-line label as one token or as "Fortschritt-" + "Quests".
 for names in (('FORTSCHRITT-QUESTS','FORTSCHRITTQUESTS'),('FORTSCHRITT-','FORTSCHRITT')):
  p=word(rows,*names,region=(0,170,400,320))
  if p:return p
 return None
def click_word(r,label,wait=1.3):
 pyautogui.click(r['x'],r['y']); log(label+f" [OCR={r['text']!r} {r['score']:.2f}]"); time.sleep(wait)
def text_near(rows,y,r=82):
 # Never mix left navigation labels into a quest sentence.
 return ' '.join(x['text'] for x in rows if abs(x['y']-y)<r and 400<=x['x']<1580)
UI={'task':'Bildschirm analysieren','decision':'Noch keine Entscheidung','action':'Start','stats':'S 0 | N 0'}
def overlay():
 try:
  w=tk.Tk(); w.attributes('-topmost',True); w.attributes('-alpha',.91); sw=w.winfo_screenwidth(); w.geometry(f'460x225+{max(5,(sw-460)//2)}+18'); w.configure(bg='#0b1220'); w.resizable(False,False)
  f=tk.Frame(w,bg='#0b1220',padx=14,pady=10); f.pack(fill='both',expand=True); tk.Label(f,text=f'🧠 Invokers Bot v{VERSION}',font=('Segoe UI',14,'bold'),bg='#0b1220',fg='white').pack(anchor='w')
  labs={}
  for k,title in [('task','👁 AUFGABE'),('decision','🎯 ENTSCHEIDUNG'),('action','🤖 AKTION')]:
   tk.Label(f,text=title,font=('Segoe UI',9,'bold'),bg='#0b1220',fg='#a5b4fc').pack(anchor='w',pady=(6,0)); labs[k]=tk.Label(f,text='',font=('Segoe UI',9),bg='#0b1220',fg='white',wraplength=425,justify='left'); labs[k].pack(anchor='w')
  labs['stats']=tk.Label(f,text='',font=('Segoe UI',9),bg='#0b1220',fg='#cbd5e1'); labs['stats'].pack(anchor='e',pady=(8,0))
  w.update_idletasks()
  try:
   hwnd=ctypes.windll.user32.GetParent(w.winfo_id()); G=-20; st=ctypes.windll.user32.GetWindowLongW(hwnd,G); ctypes.windll.user32.SetWindowLongW(hwnd,G,st|0x80000|0x20|0x80)
  except Exception:pass
  def tick():
   for k,v in labs.items():v.config(text=UI[k])
   w.after(200,tick)
  tick();w.mainloop()
 except Exception as e:print('Overlay',e)

class Bot:
 def __init__(self):
  self.quest_checked=False; self.last_ocr=[]; self.last_ocr_t=0
  self.plan_summons=0
  self.current_target=None; self.failures={}; self.loss_pending=False; self.wins=0; self.losses=0; self.last_unknown=0
  # Planner state: collect first, decide second, revisit exact quest third.
  self.scan_sections=[('progress','ALLGEMEIN'),('progress','BESCHWÖRUNG'),('progress','ENTWICKLUNG'),('progress','AUSRÜSTUNG'),('progress','KAMPF'),('side','ERRUNGENSCHAFTEN'),('side','TÄGLICH'),('side','WÖCHENTLICH'),('side','MONATLICH')]
  self.scan_index=0; self.quest_candidates=[]; self.quest_keys=set(); self.scan_started=False; self.progress_actions_seen=0; self.progress_scanned=set()
  self.nav_target=None; self.nav_stage=None; self.event_seen={}; self.victory_latch=False; self.plan_wins=0; self.recoveries=0; self.stuck_state=None; self.current_plan=None; self.current_agent=None; self.level_state='idle'; self.same_state_key=None; self.same_state_count=0
  self.agents=AgentManager()
 def result(self,win):
  if win:self.wins+=1
  else:self.losses+=1
  UI['stats']=f'✅ {self.wins} | ❌ {self.losses}'
 def reset_scan(self):
  self.scan_index=0; self.quest_candidates=[]; self.quest_keys=set(); self.scan_started=True; self.nav_target=None; self.nav_stage=None; self.progress_actions_seen=0; self.progress_scanned=set()
 def remember_events(self,rows):
  blob=' '.join(r['text'] for r in rows).lower()
  aliases=KNOWLEDGE.data.get('event_aliases',{})
  for name in KNOWLEDGE.data.get('events',{}).get('types',{}):
   names=[name.lower()]+[x.lower() for x in aliases.get(name,[])]
   if any(x in blob for x in names): self.event_seen[name]=time.time()
 def live_events(self):
  now=time.time()
  for n in [n for n,t in self.event_seen.items() if now-t>EVENT_TTL]: del self.event_seen[n]
  return tuple(self.event_seen)
 def collect_page(self,rows):
  section=self.scan_sections[self.scan_index][1]
  typ,_=self.scan_sections[self.scan_index]
  los_items=[r for r in rows if norm(r['text'])=='LOS' and 1600<=r['x']<=1885 and 170<=r['y']<=1000]
  if typ=='progress':
   self.progress_actions_seen += len(los_items)
   self.progress_scanned.add(section)
  for go in sorted(los_items,key=lambda z:z['y']):
   txt=text_near(rows,go['y']); plan=KNOWLEDGE.parse_quest(txt)
   key=(section,norm(txt))
   if key in self.quest_keys:continue
   self.quest_keys.add(key); self.quest_candidates.append({'section_index':self.scan_index,'section':section,'text':txt,'plan':plan})
   log(f'🧾 Gelesen [{section} | aktive Fortschrittsstufe] {plan["kind"]}: {txt[:100]}') if typ=='progress' else log(f'🧾 Gelesen [{section}] {plan["kind"]}: {txt[:100]}')
 def goto_section(self,idx,rows):
  typ,name=self.scan_sections[idx]
  if typ=='progress':
   p=word(rows,name,region=(380,90,1880,210))
   if not p:
    parent=left_progress(rows)
    if parent:
     # Some progress pages (notably Allgemein stage view) hide the five category tabs.
     # Re-open Fortschritt-Quests first, then retry the SAME category on the next frame.
     click_word(parent,f'↩️ Fortschritt-Navigation öffnen für {name.title()}',1.4)
     self.last_ocr_t=0
     return 'retry'
    log(f'🛡️ Bereich {name} nicht gelesen und Fortschritt-Navigation fehlt -> kein Blindklick'); return False
  else:
   p=word(rows,name,region=(0,200,400,950))
   if not p:
    log(f'🛡️ Bereich {name} nicht gelesen -> kein Blindklick'); return False
  click_word(p,f'🔎 Scan-Bereich: {name.title()}',1.4); self.last_ocr_t=0; return True
 def finish_scan(self):
  # Fortschrittsstufen werden strikt nacheinander abgearbeitet. Wenn in allen fünf
  # Fortschritts-Kategorien keine offene LOS-Aufgabe mehr existiert (Claims werden
  # vorher sofort eingesammelt), versuchen wir genau einmal die nächste freigeschaltete
  # Stufe zu öffnen und scannen danach alles neu.
  required={'ALLGEMEIN','BESCHWÖRUNG','ENTWICKLUNG','AUSRÜSTUNG','KAMPF'}
  missing=required-self.progress_scanned
  if self.progress_actions_seen==0 and not missing:
   self.scan_started=False
   self.nav_target={'advance_progress':True}; self.nav_stage='advance_progress_section'
   UI['task']='Fortschrittsstufe abgeschlossen'; UI['decision']='Prüfe nächste freigeschaltete Stufe'
   log('🏁 Alle 5 Fortschrittsbereiche sicher gelesen und ohne offene LOS-Aufgabe -> nächste Stufe prüfen')
   return True
  if self.progress_actions_seen==0 and missing:
   log('🛡️ Fortschrittsstufe NICHT als fertig gewertet; nicht sicher gelesen: '+', '.join(sorted(missing)))
  best=KNOWLEDGE.choose_best(self.quest_candidates,self.failures,self.live_events(),self.agents.can_execute)
  self.scan_started=False
  if not best:
   UI['task']='Questscan abgeschlossen'; UI['decision']='Keine sichere automatische Quest'; self.quest_checked=True; return False
  self.nav_target=best; self.nav_stage='section'
  p=best['plan']; why=', '.join(best.get('planner_reasons') or []) or 'höchste sichere Priorität'
  UI['task']=best['text'][:95]; UI['decision']=f'{p.get("target",p.get("kind"))} | Score {best["planner_score"]:.0f} | {why}'
  log(f'🧠 PLAN -> {p.get("target",p.get("kind"))} | Score {best["planner_score"]:.0f} | {why}')
  return True
 def navigate_to_best(self,s,rows):
  t=self.nav_target
  if not t:return False
  if self.nav_stage=='advance_progress_section':
   parent=left_progress(rows)
   if parent:
    click_word(parent,'🏁 Fortschritt fertig -> Fortschritt-Quests öffnen',1.4); self.nav_stage='advance_progress_click'; self.last_ocr_t=0; return True
   # Wenn die Fortschritt-Tabs bereits sichtbar sind, sind wir schon im richtigen Bereich.
   if word(rows,'ALLGEMEIN',region=(380,90,1880,210)):
    self.nav_stage='advance_progress_click'; return True
   log('🛡️ Nächste Fortschrittsstufe nicht sicher erreichbar'); self.nav_target=None; self.quest_checked=True; return True
  if self.nav_stage=='advance_progress_click':
   nxt=match('quest_next',s,(1710,160,1905,340))
   if nxt:
    click(nxt,'➡️ Nächste freigeschaltete Fortschrittsstufe',1.5)
    self.nav_target=None; self.quest_checked=False; self.scan_started=False; self.scan_index=0; self.progress_actions_seen=0; self.progress_scanned=set(); self.last_ocr_t=0
    return True
   log('🛡️ Kein bestätigter Weiter-Pfeil -> Fortschrittsstufe bleibt aktiv'); self.nav_target=None; self.quest_checked=True; return True
  if self.nav_stage=='section':
   typ,name=self.scan_sections[t['section_index']]
   if typ=='progress':
    top=word(rows,name,region=(380,90,1880,210))
    if not top:
     parent=left_progress(rows)
     if parent: click_word(parent,'↩️ Zurück zu Fortschritt-Quests',1.3); return True
     log('🛡️ Fortschritt-Navigation nicht sicher erkannt'); self.nav_target=None; self.quest_checked=True; return True
    click_word(top,f'🎯 Zielbereich: {name.title()}',1.3); self.nav_stage='pages'; self.last_ocr_t=0; return True
   if self.goto_section(t['section_index'],rows): self.nav_stage='pages'
   else: log('🛡️ Zielbereich nicht sicher erreichbar'); self.nav_target=None; self.quest_checked=True
   return True
  if self.nav_stage=='pages':
   # Fortschrittsseiten sind Progressionsstufen, keine frei scanbare Pagination.
   # Wir führen nur Quests der aktuell freigeschalteten Stufe aus.
   self.nav_stage='execute'; return True
  if self.nav_stage=='execute':
   # Re-read the page and bind LOS to the quest line again. Never reuse old coordinates.
   los_items=[r for r in rows if norm(r['text'])=='LOS' and 1600<=r['x']<=1885 and 170<=r['y']<=1000]
   best=None; bestscore=-1
   for go in los_items:
    txt=text_near(rows,go['y']); score=KNOWLEDGE.quest_similarity(t['text'],txt)
    if score>bestscore: bestscore=score; best=(go,txt)
   log(f'🔎 Quest-Rebind beste Ähnlichkeit: {bestscore:.2f}')
   if best and bestscore>=QUEST_MATCH_MIN:
    go,txt=best; plan=KNOWLEDGE.parse_quest(txt)
    if self.agents.can_execute(plan['kind']):
     self.current_plan=plan; self.plan_wins=0; self.plan_summons=0; self.current_target=plan.get('target') or plan['kind']; a=self.agents.assign(plan); self.current_agent=a.agent; log(f'🤖 {a.agent} übernimmt: {a.reason}'); click_word(go,f'📜 {a.agent} -> {self.current_target}',2.0); self.quest_checked=True; self.nav_target=None; return True
   log('🛡️ Geplante Quest nicht sicher wiedergefunden -> kein LOS'); self.nav_target=None; self.quest_checked=True; return True
  return False
 def clear_plan(self):
  self.quest_checked=False; self.scan_started=False; self.nav_target=None; self.current_plan=None; self.current_target=None; self.current_agent=None; self.level_state='idle'; self.plan_wins=0; self.plan_summons=0
 def recover(self,s,st):
  global RUN
  self.same_state_count=0
  if st.name!=self.stuck_state: self.stuck_state=st.name; self.recoveries=0
  self.recoveries+=1
  try:
   D=ROOT/'debug'; D.mkdir(exist_ok=True); fn=D/(time.strftime('stuck_%H%M%S_')+f'{self.recoveries}_'+st.name+'.png'); cv2.imwrite(str(fn),s)
   log(f'🆘 Watchdog: {st.name} hängt (Versuch {self.recoveries}/3) -> Screenshot {fn.name}')
  except Exception as e: log('Debug-Screenshot Fehler: '+repr(e))
  if self.recoveries>=3:
   log('🛑 Recovery erfolglos -> Bot stoppt. Schick mir den Screenshot aus dem Ordner debug/ und bot.log'); RUN=False; return
  self.clear_plan()
  b=match('back',s)
  if b: click(b,'🆘 Recovery -> ZURÜCK',1.5)
 def step(self):
  s=shot(); rows=ocr_region(s,(0,40,1910,1010)); self.remember_events(rows); st=classify(s)
  state_key=(st.name, norm(' '.join(r['text'] for r in rows))[:180])
  if state_key==self.same_state_key: self.same_state_count+=1
  else: self.same_state_key=state_key; self.same_state_count=0
  if st==Screen.BATTLE: self.same_state_count=0  # langer Auto-Kampf ist kein Hänger
  limit=WATCHDOG_UNSUPPORTED if st in (Screen.INVOKER_LIST,Screen.FILTER) else WATCHDOG_SAME_SCREEN  # Screens ohne Aktor nicht 72 Loops abwarten
  if self.same_state_count>=limit:
   self.recover(s,st); return
  lossword=word(rows,'NIEDERLAGE',region=(450,80,1750,900)); homeword=word(rows,'STARTSEITE',region=(1450,700,1905,1030))
  if lossword and homeword: st=Screen.DEFEAT_RESULT
  elif lossword: st=Screen.DEFEAT_BANNER
  if st!=Screen.VICTORY: self.victory_latch=False
  if st!=Screen.LEVELUP: self.level_state='idle'
  ok=word(rows,'OKAY',region=(650,700,1200,980))
  if ok: click_word(ok,'📘 Popup -> OKAY',1.5); return
  if st==Screen.DEFEAT_BANNER:
   if not self.loss_pending:
    self.loss_pending=True; self.result(False); key=self.current_target or 'unbekannt'; self.failures[key]=self.failures.get(key,0)+1
   UI['decision']=f'{self.current_target or "Kampf"} nicht wiederholen'; click_word(lossword,'❌ Niederlage -> fortfahren',1.8); return
  if st==Screen.DEFEAT_RESULT:
   if homeword:
    click_word(homeword,'🏠 Niederlage -> STARTSEITE',2.2); self.quest_checked=False; self.loss_pending=False; self.current_target=None; self.current_plan=None; self.current_agent=None; self.scan_started=False
   else: log('🛡️ Niederlage erkannt, aber STARTSEITE nicht gelesen -> kein Klick')
   return
  if st==Screen.VICTORY:
   if self.loss_pending:self.loss_pending=False
   if not self.victory_latch:
    self.victory_latch=True; self.result(True); self.plan_wins+=1
   # A planned quest must be re-read after every win. "Nächstes Level" can move away
   # from an exact farm target (e.g. Chapter 1 Level 6), so never use it for a quest plan.
   if self.current_plan:
    if self.current_target in self.failures:self.failures[self.current_target]=0
    # ACHTUNG: quantity ist NICHT zwingend die Anzahl Siege (z.B. '3 Handschuhe' != 3 Kämpfe).
    # Es ist nur eine Obergrenze für Wiederholungen; danach wird der Questfortschritt per OCR neu gelesen.
    cap=min(max(1,int(self.current_plan.get('quantity') or 1)),REPLAY_SOFT_MAX)
    replay=self.agents.campaign_result_action(self.current_plan,rows,norm)
    if replay and self.plan_wins<cap:
     click_word(replay,f'🔁 CampaignAgent -> wiederholen ({self.plan_wins}/{cap}, danach Quest neu prüfen)',2.2); return
    b=match('back',s)
    if b:
     click(b,'🏆 Quest-Sieg -> zurück und Questfortschritt neu prüfen',2.0)
     self.clear_plan()
    else:
     if replay and self.plan_wins<REPLAY_HARD_MAX: click_word(replay,'🔁 kein ZURÜCK sichtbar -> wiederholen (harte Grenze beachtet)',2.2)
     else: log('🛡️ Quest-Sieg: weder Replay noch sicherer ZURÜCK-Button -> kein Blindklick')
    return
   p=match('next_level_result',s)
   if p: click(p,'🏆 Freies Farmen -> nächstes Level',2.2)
   else: log('🏆 Sieg erkannt, aber kein sicherer Weiter-Button')
   return
  if st==Screen.BATTLE:
   p=match('auto_off',s)
   if p: click(p,'🤖 AUTO einschalten',1.5)
   return
  if st==Screen.TEAM:
   k=word(rows,'KÄMPFEN',region=(1450,650,1910,1030))
   if k: click_word(k,'⚔️ Team -> KÄMPFEN',2.6)
   else: log('🛡️ TEAM erkannt, KÄMPFEN nicht gelesen -> kein Klick')
   return
  if st==Screen.LEVEL_SELECT:
   k=word(rows,'KÄMPFEN',region=(1450,650,1910,1030))
   if k: click_word(k,'⚔️ Level -> KÄMPFEN',2.0)
   else: log('🛡️ LEVEL erkannt, KÄMPFEN nicht gelesen -> kein Klick')
   return
  if st==Screen.PROFILE:
   take=word(rows,'ANNEHMEN',region=(650,690,1200,930))
   if take: click_word(take,'🎁 Profil: ANNEHMEN',1.2); return
   b=match('back',s)
   if b: click(b,'↩️ Profil -> ZURÜCK',1.2)
   return
  if st==Screen.HOME:
   if not self.quest_checked:
    q=match('home_quests',s)
    if q: click(q,'📋 Zuerst Quests vollständig scannen',1.8); UI['task']='Alle Quests sammeln'; self.reset_scan(); return
    log('🛡️ HOME: Questbutton nicht erkannt -> kein Klick'); return
   p=match('home_fight',s)
   if p: click(p,'⚔️ Keine sichere Quest -> KAMPF',1.8)
   else: log('🛡️ HOME: KAMPF nicht erkannt -> kein Klick')
   return
  if st==Screen.QUESTS:
   if time.time()-self.last_ocr_t>1.0:self.last_ocr=ocr_rows(s);self.last_ocr_t=time.time()
   qr=self.last_ocr; self.remember_events(qr)
   # Safe rewards may be claimed immediately; then re-read the same page.
   take=word(qr,'ANNEHMEN',region=(1600,170,1885,1000))
   if take:
    click_word(take,'🎁 Quest: ANNEHMEN',1.0); self.last_ocr_t=0
    # Belohnungen können die nächste Fortschrittsstufe freischalten. Danach immer neu scannen.
    self.scan_started=False; self.quest_candidates=[]; self.quest_keys=set(); self.scan_index=0; self.progress_actions_seen=0; self.progress_scanned=set()
    return
   if self.nav_target:
    if self.navigate_to_best(s,qr): return
   if not self.scan_started:self.reset_scan()
   self.collect_page(qr)
   # KEIN Weiterblättern innerhalb der Fortschritt-Quests: Seite 2/3/... sind
   # nacheinander freigeschaltete Progressionsstufen. Wir scannen nur die aktive Stufe.
   self.scan_index+=1
   while self.scan_index<len(self.scan_sections):
    nav=self.goto_section(self.scan_index,qr)
    if nav: return
    log(f'⚠️ Scan-Bereich übersprungen: {self.scan_sections[self.scan_index][1]}'); self.scan_index+=1
   if self.finish_scan(): return
   b=match('back',s)
   if b:click(b,'↩️ Keine sichere Quest -> ZURÜCK',1.5)
   else:log('🛡️ Questscan fertig, ZURÜCK nicht erkannt -> kein Klick')
   return
  if st==Screen.CAMPAIGN:
   if self.current_plan and self.current_plan.get('kind')=='campaign':
    # GO/LOS is authoritative for exact chapter/stage. Never drift with generic next-level navigation.
    p=match('campaign_card',s)
    if p: click(p,'⚔️ Geplante Kampagne öffnen (LOS-Ziel beibehalten)',1.8); return
    log('🛡️ Geplantes Campaign-Ziel: kein sicherer zielerhaltender Control -> kein Nächstes-Level-Blindklick'); return
   p=match('next_level_map',s)
   if p:self.current_target=self.current_target or 'Kampagne nächstes Level';click(p,'⚔️ Freies Farmen -> nächstes Level',1.8);return
   p=match('campaign_card',s)
   if p:click(p,'⚔️ Kampagne öffnen',1.8);return
  if st==Screen.SUMMON:
   p10=match('summon10',s); p1=match('summon1',s)
   # Nur mit aktivem SummonAgent-Plan und nur bis zur Quest-Menge. Ohne Plan: KEIN Klick (Screen wurde manuell geöffnet).
   need=max(1,int((self.current_plan or {}).get('quantity') or 1)); left=need-self.plan_summons
   count=self.agents.summon_count(self.current_plan,bool(p10),bool(p1),left)
   p=p10 if count==10 else (p1 if count==1 else None)
   if p:
    self.plan_summons+=count
    click(p,f'🟢 {count}x Stern der Wildnis ({self.plan_summons}/{need})',1.8)
   elif self.current_plan and self.current_plan.get('kind')=='summon' and left<=0:
    b=match('back',s)
    if b: click(b,'🎴 Beschwörungsmenge erreicht -> zurück, Quest neu prüfen',1.5); self.clear_plan()
    else: log('🛡️ Beschwörungsmenge erreicht, ZURÜCK nicht erkannt -> kein Klick')
   else: log('🛡️ Beschwörung: kein aktiver Summon-Plan oder 1x/10x-Button nicht sicher erkannt -> kein Klick')
   return
  if st==Screen.LEVELUP:
   auto=match('auto_select',s); level=match('level_button',s)
   if auto and self.level_state in ('idle','done'):
    click(auto,'⬆️ Automatische Auswahl',1.2); self.level_state='selected'; return
   if level and self.level_state=='selected':
    click(level,'⬆️ LEVELN nach automatischer Auswahl',1.5); self.level_state='done'; return
   log(f'🛡️ Leveln: Zustand {self.level_state}; erwartete sichere Reihenfolge nicht bestätigt')
   return
  if st==Screen.INVOKER_LIST:
   log('🛡️ Invokerliste: observe-only (Wegschicken nicht implementiert) -> kein Klick')
   return
  if st==Screen.FILTER:
   log('🛡️ Filter-Screen: observe-only (Wegschicken nicht implementiert) -> kein Klick')
   return
  if time.time()-self.last_unknown>7:log('👀 Unbekannter Zustand -> KEIN KLICK');self.last_unknown=time.time()
  time.sleep(.5)

def stop():
 global RUN
 try:
  import keyboard;keyboard.wait('f8');RUN=False;log('STOP F8')
 except Exception:pass
def main():
 global RUN
 LOG.write_text('',encoding='utf-8')
 sw,sh=pyautogui.size()
 if (sw,sh)!=(SCREEN_W,SCREEN_H):
  log(f'🛑 Bildschirm {sw}x{sh}; erwartet {SCREEN_W}x{SCREEN_H}. Bot startet aus Sicherheitsgründen nicht.')
  return
 log(f'Invokers Bot v{VERSION} gestartet | QuestScanner -> Knowledge -> Planner -> Spezial-Agent -> Safe Actor')
 log('🧠 OCR sammelt Daten; Knowledge bewertet; Aktor klickt nur bestätigte Controls')
 threading.Thread(target=overlay,daemon=True).start();threading.Thread(target=stop,daemon=True).start();b=Bot()
 while RUN:
  try:b.step()
  except pyautogui.FailSafeException:log('NOT-AUS: Maus oben links');break
  except Exception as e:log('Fehler: '+repr(e));time.sleep(2)
if __name__=='__main__':main()
