"""Read-only narrow formation sensor with calibrated local glyph templates.

No OCR engine, game input, screenshot persistence or synthetic live calibration.
Templates must be supplied from the actual client font by an operator.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
import time
import cv2
import numpy as np
from .arena_ranking import OwnPower, PowerSource

REFERENCE_ROI=(.521,.139,.651,.255)
REFERENCE_SIZE=(1536,864)
GLYPHS="0123456789."

def normalize_power(text):
    if not isinstance(text,str) or not re.fullmatch(r"(?:[1-9][0-9]{0,9}|[1-9][0-9]{0,2}(?:\.[0-9]{3}){1,3})",text):
        return None
    value=int(text.replace(".",""))
    return value if 0<value<=2147483647 else None


@dataclass(frozen=True,slots=True)
class Calibration:
    calibration_id: str
    client_size: tuple[int,int]
    dpi: int
    roi: tuple[float,float,float,float]
    minimum_score: float = .97
    minimum_margin: float = .08

    def __post_init__(self):
        x1,y1,x2,y2=self.roi
        if (not self.calibration_id or self.dpi<=0 or len(self.client_size)!=2
                or min(self.client_size)<=0 or not (0<=x1<x2<=1 and 0<=y1<y2<=1)
                or x2-x1>.15 or y2-y1>.12 or not .95<=self.minimum_score<=1
                or not .05<=self.minimum_margin<=1):
            raise ValueError("unsafe formation calibration")


def _mask(img):
    if img.ndim==3:
        img=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    _,mask=cv2.threshold(img,0,255,cv2.THRESH_BINARY|cv2.THRESH_OTSU)
    if np.count_nonzero(mask)>mask.size/2:
        raise ValueError("bright background/ambiguous polarity")
    return mask


def _trim(mask):
    pts=cv2.findNonZero(mask)
    if pts is None:
        raise ValueError("empty glyph")
    x,y,w,h=cv2.boundingRect(pts)
    return mask[y:y+h,x:x+w]


class GlyphReader:
    """Compare contiguous glyphs against all eleven calibrated templates."""
    def __init__(self,templates,calibration):
        if set(templates)!=set(GLYPHS):
            raise ValueError("complete digit and separator template set required")
        self.calibration=calibration
        self.templates={k:_trim(_mask(v)) for k,v in templates.items()}
        self.digest=sha256(b"".join(k.encode()+str(v.shape).encode()+v.tobytes()
                                  for k,v in sorted(self.templates.items()))).hexdigest()

    @classmethod
    def load(cls,directory,calibration):
        data={}
        for char in GLYPHS:
            path=Path(directory)/("dot.png" if char=="." else char+".png")
            img=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise ValueError("missing calibrated glyph")
            data[char]=img
        return cls(data,calibration)

    def read(self,crop):
        mask=_mask(crop)
        # Vertical projection, no background text or multi-line values accepted.
        cols=np.flatnonzero(np.any(mask,axis=0))
        if not len(cols):
            return None
        runs=np.split(cols,np.where(np.diff(cols)>1)[0]+1)
        if not 1<=len(runs)<=13:
            return None
        text=""
        boxes=[]
        gaps=[]
        for run in runs:
            x0,x1=int(run[0]),int(run[-1])+1
            ys=np.flatnonzero(np.any(mask[:,x0:x1],axis=1))
            y0,y1=int(ys[0]),int(ys[-1])+1
            glyph=mask[y0:y1,x0:x1]
            scores=[]
            for char,tpl in self.templates.items():
                if glyph.shape!=tpl.shape:
                    continue
                score=1-float(np.count_nonzero(glyph!=tpl))/glyph.size
                scores.append((score,char))
            scores.sort(reverse=True)
            if not scores or scores[0][0]<self.calibration.minimum_score:
                return None
            if len(scores)>1 and scores[0][0]-scores[1][0]<self.calibration.minimum_margin:
                return None
            if boxes:
                gaps.append(x0-boxes[-1][1])
            char=scores[0][1]
            text+=char
            boxes.append((x0,x1,y0,y1,char))
        digits=[b for b in boxes if b[4]!="."]
        if not digits or max(b[3] for b in boxes)-min(b[3] for b in boxes)>2:
            return None
        if max(b[2] for b in digits)-min(b[2] for b in digits)>2:
            return None
        if gaps and max(gaps)>max(3,round(max(b[1]-b[0] for b in digits)*.6)):
            return None
        return normalize_power(text)


def sense_formation(frame,*,state,confirmed,dpi,reader,context,observed_at=None,now=None):
    now=time.monotonic() if now is None else now
    observed_at=now if observed_at is None else observed_at
    unknown=OwnPower(None,PowerSource.UNKNOWN,observed_at)
    if state!="formation" or confirmed is not True or not 0<=now-observed_at<=2:
        return unknown
    c=reader.calibration
    h,w=frame.shape[:2]
    if (w,h)!=c.client_size or dpi!=c.dpi or not context:
        return unknown
    x1,y1,x2,y2=c.roi
    crop=frame[round(y1*h):round(y2*h),round(x1*w):round(x2*w)]
    try:
        value=reader.read(crop)
    except (ValueError,cv2.error):
        return unknown
    if value is None:
        return unknown
    # Digest binds the calibration ID and glyph set, not a Battle snapshot.
    digest=sha256((c.calibration_id+":"+reader.digest+":"+str(c)).encode()).hexdigest()
    return OwnPower(value,PowerSource.PREBATTLE_NUMERIC_ROI,observed_at,
                    digest=digest,confidence=1.0,exact=True,validated=True,context=context)
