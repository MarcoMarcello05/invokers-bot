import cv2, numpy as np
from mss import mss
try:
    import dxcam
except Exception:
    dxcam=None

class ScreenCapture:
    def __init__(self):
        self._mss=mss(); self._camera=None
        if dxcam is not None:
            try: self._camera=dxcam.create(output_color="BGR")
            except Exception: self._camera=None
    @property
    def backend(self): return "dxcam" if self._camera is not None else "mss"
    def grab(self,rect):
        if self._camera is not None:
            frame=self._camera.grab(region=(rect.left,rect.top,rect.right,rect.bottom),new_frame_only=False)
            if frame is not None: return frame.copy()
        shot=self._mss.grab({"left":rect.left,"top":rect.top,"width":rect.width,"height":rect.height})
        return cv2.cvtColor(np.asarray(shot),cv2.COLOR_BGRA2BGR)
    def close(self):
        try:
            if self._camera is not None: self._camera.stop()
        except Exception: pass
        try: self._mss.close()
        except Exception: pass
