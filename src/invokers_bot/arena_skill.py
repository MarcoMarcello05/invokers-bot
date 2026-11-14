"""Runtime adapter for calibrated arena card observation, not opponent selection."""
from dataclasses import asdict
from hashlib import sha256
import cv2
import numpy as np

from .arena_traversal import Bounds, Row, View, traverse
from .action_verification import ActionResult
from .models import GameState
from .wheel import validate_wheel


def observe_cards(frame, roi, template, threshold=0.9):
    """A full-card visual anchor template locates bounded card regions.

    Use a calibrated anchor and card dimensions; exact normalized pixel hashes
    are fallback observations only, never stable opponent identifiers.
    """
    h,w = frame.shape[:2]
    x1,y1,x2,y2 = round(w*roi[0]),round(h*roi[1]),round(w*roi[2]),round(h*roi[3])
    crop = frame[y1:y2,x1:x2]
    gray = cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
    th,tw = template.shape[:2]
    if th > gray.shape[0] or tw > gray.shape[1] or min(th,tw)<2:
        raise ValueError("card template outside calibrated ROI")
    scores = cv2.matchTemplate(gray,template,cv2.TM_CCOEFF_NORMED)
    rows=[]
    # Bound NMS work; each accepted region suppresses overlapping matches.
    for _ in range(100):
        _,score,_,(x,y)=cv2.minMaxLoc(scores)
        if score < threshold:
            break
        card=gray[y:y+th,x:x+tw]
        rows.append(Row(sha256(cv2.resize(card,(64,32),interpolation=cv2.INTER_AREA).tobytes()).hexdigest(),
                        (x+x1,y+y1,tw,th)))
        scores[max(0,y-th+1):y+th,max(0,x-tw+1):x+tw]=-1
    return sha256(gray.tobytes()).hexdigest(),tuple(sorted(rows,key=lambda row:row.region[1]))


def run_arena_traversal(engine, action, cancelled):
    if not action.get("calibrated") or not action.get("starts_at_top"):
        return ActionResult(False,"TRAVERSAL_CALIBRATION_REQUIRED")
    if not engine.live:
        return ActionResult(False,"DRY_RUN")
    try:
        roi=action["roi"]
        bounds=Bounds(**action.get("bounds",{}))
        validate_wheel(bounds.delta,roi)
        template=engine.vision._template(action["card_template"])
        threshold=float(action.get("card_threshold",0.9))
        if not 0.5 <= threshold <= 1:
            raise ValueError("invalid card threshold")
    except (KeyError,ValueError,TypeError,OSError):
        return ActionResult(False,"TRAVERSAL_CALIBRATION_REQUIRED")
    latest=[None,None]

    def observe():
        rect,frame,_,state=engine._observe()
        latest[:]=[rect,frame]
        account=engine._refresh_account(force=True,sources={"arena"})
        item=account.sources.get("arena") if account else None
        if state!=GameState.ARENA_LIST or item is None or not item.fresh(2):
            return View(state,None,None,None,"",())
        fingerprint,rows=observe_cards(frame,roi,template,threshold)
        return View(state,item.digest,item.model.version,item.model.opponents.count,fingerprint,rows)

    def scroll(delta):
        return engine._perform({"type":"scroll_wheel","delta":delta,"roi":roi},*latest)

    inventory=traverse(observe,scroll,cancelled,bounds)
    engine.world_state.facts["arena_traversal"]=inventory
    print("[arena_traversal]",asdict(inventory))
    # This is a diagnostic inventory, never a target locator or start permission.
    return ActionResult(inventory.reason in ("END_UNCHANGED","NO_NEW_ROWS","COUNT_REACHED"),
                        "TRAVERSAL_"+inventory.reason)


def discard_stale_inventory(facts, account):
    old=facts.get("arena_traversal")
    if old is None:
        return False
    item=account.sources.get("arena") if account else None
    if not old.matches(item):
        facts.pop("arena_traversal",None)
        return True
    return False
