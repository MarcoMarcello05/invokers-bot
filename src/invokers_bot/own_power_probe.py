"""Small calibrated formation number ROI, diagnostic only.

A reader is injected explicitly; this module does not invoke broad OCR or
promote unvalidated visual values to exact/autonomous power.
"""
from dataclasses import asdict
import re
import time
from .arena_ranking import OwnPower, PowerSource, team_context


def numeric_roi(frame, roi, reader, *, observed_at=None, context=()):
    if not isinstance(roi,(tuple,list)) or len(roi)!=4:
        raise ValueError("numeric ROI required")
    x1,y1,x2,y2=roi
    if not (0<=x1<x2<=1 and 0<=y1<y2<=1 and x2-x1<=.25 and y2-y1<=.12):
        raise ValueError("numeric ROI must be small and within client")
    h,w=frame.shape[:2]
    crop=frame[round(y1*h):round(y2*h),round(x1*w):round(x2*w)]
    if not crop.size:
        raise ValueError("empty numeric ROI")
    text,confidence=reader(crop)
    # Strict ASCII digits only; ambiguous separators/labels are rejected.
    if not isinstance(text,str) or not re.fullmatch(r"[0-9]{1,10}",text.strip()):
        return OwnPower(None,PowerSource.UNKNOWN,time.monotonic() if observed_at is None else observed_at)
    value=int(text)
    return OwnPower(value if value>0 else None,PowerSource.PREBATTLE_NUMERIC_ROI,
        time.monotonic() if observed_at is None else observed_at,
        confidence=float(confidence),exact=False,validated=False,context=context)


def manual_probe_sample(facts, frame, state, config, reader):
    """Explicit manual diagnostic only, not a background OCR service."""
    if state != "formation" or not config.get("enabled"):
        return None
    sample=numeric_roi(frame,config.get("roi"),reader,context=team_context(facts.get("account")))
    facts["arena_own_power_diagnostic"]=sample
    return sample
