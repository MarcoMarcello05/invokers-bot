import json,time
from pathlib import Path
import cv2
from .capture import ScreenCapture
from .input_win import InputController,f12_pressed
from .models import GameState
from .vision import Vision
from .window import GameWindow

class BotEngine:
    def __init__(self,config,live):
        self.config=config; self.live=live; self.window=GameWindow.find(config.window_title_contains)
        self.capture=ScreenCapture(); self.vision=Vision(config); self.input=InputController()
        self.runtime_dir=Path("runtime"); self.runtime_dir.mkdir(exist_ok=True)
        self.last_state=GameState.UNKNOWN; self.stable_count=0; self.handled_state=GameState.UNKNOWN; self.unknown_count=0
    def _observe(self):
        if not self.window.is_alive(): raise RuntimeError("Game window closed")
        rect=self.window.client_rect(); frame=self.capture.grab(rect); match=self.vision.classify(frame)
        return rect,frame,match,match.state if match else GameState.UNKNOWN
    def _stable(self,state):
        if state==self.last_state: self.stable_count+=1
        else: self.last_state=state; self.stable_count=1; self.handled_state=GameState.UNKNOWN
        return self.stable_count>=self.config.stable_frames
    def _perform(self,action,rect,frame):
        kind=str(action.get("type","wait"))
        if action.get("purchase",False) and not self.config.allow_purchase_actions:
            print("[safety] purchase action blocked"); return
        if kind=="wait": time.sleep(float(action.get("seconds",.5))); return
        if kind=="click_template":
            hit=self.vision.find_target(frame,action)
            if not hit: print("[action] target not found:",action.get("template")); return
            cx,cy=hit.center; sx,sy=rect.left+cx,rect.top+cy
            if self.live: self.window.activate(); self.input.click_screen(sx,sy)
            print(f"[{'LIVE' if self.live else 'DRY'}] click {action.get('template')} score={hit.score:.3f} at {sx},{sy}"); return
        if kind=="click_norm":
            sx=rect.left+round(rect.width*float(action["x"])); sy=rect.top+round(rect.height*float(action["y"]))
            if self.live: self.window.activate(); self.input.click_screen(sx,sy)
            print(f"[{'LIVE' if self.live else 'DRY'}] click_norm -> {sx},{sy}"); return
        if kind=="key":
            if self.live: self.window.activate(); self.input.key(str(action["key"]))
            print(f"[{'LIVE' if self.live else 'DRY'}] key {action['key']}"); return
        raise ValueError(f"Unknown action: {kind}")
    def _handle(self,state,match,rect,frame):
        actions=list(self.config.flows.get(state.value,{}).get("actions",[]))
        if not actions: return
        print(f"[state] {state.value} score={match.score if match else 0:.3f}")
        for action in actions:
            self._perform(action,rect,frame)
            if action.get("recapture",True):
                time.sleep(self.config.post_action_delay); rect=self.window.client_rect(); frame=self.capture.grab(rect)
    def run(self):
        print(json.dumps({"mode":"LIVE" if self.live else "DRY","window":self.window.title,"dpi":self.window.dpi(),"capture":self.capture.backend,"f12_abort":True}))
        period=1/max(.5,self.config.fps)
        try:
            while True:
                started=time.perf_counter()
                if f12_pressed(): print("[stop] F12"); break
                rect,frame,match,state=self._observe()
                if state==GameState.UNKNOWN:
                    self.unknown_count+=1; self.stable_count=0; self.last_state=state; self.handled_state=state
                    if self.unknown_count==self.config.unknown_dump_after:
                        p=self.runtime_dir/f"unknown-{time.strftime('%Y%m%d-%H%M%S')}.png"; cv2.imwrite(str(p),frame)
                        print("[vision] persistent UNKNOWN; screenshot saved; no input sent")
                else:
                    self.unknown_count=0
                    if self._stable(state) and self.handled_state!=state:
                        self._handle(state,match,rect,frame); self.handled_state=state
                delay=period-(time.perf_counter()-started)
                if delay>0: time.sleep(delay)
        finally: self.capture.close()
