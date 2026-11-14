import cv2
from .config import resolve_asset
from .models import GameState, Match, TargetMatch

def _crop_roi(frame,roi):
    if not roi: return frame,0,0
    h,w=frame.shape[:2]
    x1=max(0,min(w,round(w*roi[0]))); y1=max(0,min(h,round(h*roi[1])))
    x2=max(x1+1,min(w,round(w*roi[2]))); y2=max(y1+1,min(h,round(h*roi[3])))
    return frame[y1:y2,x1:x2],x1,y1

class Vision:
    def __init__(self,config): self.config=config; self._cache={}
    def _template(self,name):
        if name not in self._cache:
            path=resolve_asset(self.config,name)
            img=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
            if img is None: raise FileNotFoundError(f"Template missing: {path}")
            self._cache[name]=img
        return self._cache[name]
    def _best(self,frame,name,threshold,roi=None,scales=None):
        search,ox,oy=_crop_roi(frame,roi); gray=cv2.cvtColor(search,cv2.COLOR_BGR2GRAY); base=self._template(name); best=None
        for scale in (scales or [1.0]):
            if scale<=0: continue
            tpl=base if scale==1 else cv2.resize(base,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_LINEAR)
            th,tw=tpl.shape[:2]; sh,sw=gray.shape[:2]
            if tw>sw or th>sh: continue
            result=cv2.matchTemplate(gray,tpl,cv2.TM_CCOEFF_NORMED)
            _,score,_,loc=cv2.minMaxLoc(result)
            hit=TargetMatch(float(score),ox+loc[0],oy+loc[1],tw,th,name)
            if best is None or hit.score>best.score: best=hit
        return best if best is not None and best.score>=threshold else None
    def classify(self,frame):
        winner=None
        for state_name,spec in self.config.states.items():
            if not spec.get("enabled",True): continue
            try: state=GameState(state_name)
            except ValueError: continue
            hit=self._best(frame,str(spec["template"]),float(spec.get("threshold",.88)),spec.get("roi"),spec.get("scales",[.9,1,1.1]))
            if hit:
                m=Match(state,hit.score,hit.x,hit.y,hit.width,hit.height,hit.template)
                if winner is None or m.score>winner.score: winner=m
        return winner
    def find_target(self,frame,spec):
        return self._best(frame,str(spec["template"]),float(spec.get("threshold",.88)),spec.get("roi"),spec.get("scales",[.9,1,1.1]))
