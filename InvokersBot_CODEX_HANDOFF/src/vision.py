"""Vision locates an already decided UI target; it never chooses game policy."""
from dataclasses import dataclass
import re
import time


@dataclass(frozen=True)
class LocatedTarget:
    label: str
    x: int
    y: int
    confidence: float
    method: str = 'targeted_ocr'
    observed_at: float = 0
    screen_id: str | None = None


def locate_intended_label(label, rows, *, minimum_confidence=.85, observed_at=None, screen_id=None):
    """Return one exact normalized name/button match; ambiguity yields no click.

    Numeric OCR values are deliberately not exposed as combat/cost decisions.
    A planner has already selected the structured target before calling this.
    """
    normalize = lambda value: re.sub(r'[^\w]', '', str(value).casefold())
    expected = normalize(label)
    if not expected:
        return None
    candidates = [r for r in rows if normalize(r.get('text', '')) == expected
                  and isinstance(r.get('conf'), (float, int)) and r['conf'] >= minimum_confidence
                  and type(r.get('x')) is int and type(r.get('y')) is int]
    if len(candidates) != 1:
        return None
    row = candidates[0]
    return LocatedTarget(str(label), row['x'], row['y'], float(row['conf']),
                         observed_at=time.time() if observed_at is None else observed_at,
                         screen_id=screen_id)
