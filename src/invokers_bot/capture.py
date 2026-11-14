import cv2
import numpy as np
from mss import mss

try:
    import dxcam
except Exception:
    dxcam = None

class ScreenCapture:
    def __init__(self, target_fps=60):
        self._mss = mss()
        self._camera = None
        self._stream_region = None
        self._target_fps = int(target_fps)
        if dxcam is not None:
            try:
                self._camera = dxcam.create(output_color="BGR", max_buffer_len=8)
            except Exception:
                self._camera = None

    @property
    def backend(self):
        return "dxcam-stream" if self._camera is not None else "mss"

    def _ensure_stream(self, rect):
        if self._camera is None:
            return
        region = (rect.left, rect.top, rect.right, rect.bottom)
        if region == self._stream_region:
            return
        if self._stream_region is not None:
            try:
                self._camera.stop()
            except Exception:
                pass
        self._camera.start(region=region, target_fps=self._target_fps)
        self._stream_region = region

    def grab(self, rect):
        if self._camera is not None:
            self._ensure_stream(rect)
            frame = self._camera.get_latest_frame(copy=True)
            if frame is not None:
                return frame

        shot = self._mss.grab({
            "left": rect.left,
            "top": rect.top,
            "width": rect.width,
            "height": rect.height,
        })
        return cv2.cvtColor(np.asarray(shot), cv2.COLOR_BGRA2BGR)

    def close(self):
        try:
            if self._camera is not None:
                self._camera.stop()
        except Exception:
            pass
        try:
            self._mss.close()
        except Exception:
            pass
