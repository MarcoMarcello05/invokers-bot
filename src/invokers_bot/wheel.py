"""Generic signed vertical wheel contract."""
WHEEL_DELTA = 120


def validate_wheel(delta, roi):
    if type(delta) is not int or delta == 0 or abs(delta) > 1200 or delta % WHEEL_DELTA:
        raise ValueError("wheel delta must be signed whole notches, at most ten")
    if not isinstance(roi, (list, tuple)) or len(roi) != 4:
        raise ValueError("wheel ROI required")
    x1,y1,x2,y2 = roi
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise ValueError("wheel ROI outside client")
    return delta, (x1,y1,x2,y2)
