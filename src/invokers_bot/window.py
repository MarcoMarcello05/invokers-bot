import ctypes
from dataclasses import dataclass
import win32con, win32gui
from .models import Rect

@dataclass
class GameWindow:
    hwnd:int
    @classmethod
    def find(cls,title_contains):
        needle=title_contains.lower().strip(); hits=[]
        def cb(hwnd,_):
            if win32gui.IsWindowVisible(hwnd):
                title=win32gui.GetWindowText(hwnd)
                if needle in title.lower(): hits.append((hwnd,title))
        win32gui.EnumWindows(cb,None)
        if not hits: raise RuntimeError(f"No visible window contains title: {title_contains!r}")
        return cls(hits[0][0])
    @property
    def title(self): return win32gui.GetWindowText(self.hwnd)
    def client_rect(self):
        l,t,r,b=win32gui.GetClientRect(self.hwnd)
        x1,y1=win32gui.ClientToScreen(self.hwnd,(l,t)); x2,y2=win32gui.ClientToScreen(self.hwnd,(r,b))
        return Rect(x1,y1,x2-x1,y2-y1)
    def dpi(self):
        try: return int(ctypes.windll.user32.GetDpiForWindow(self.hwnd))
        except Exception: return 96
    def activate(self):
        if win32gui.IsIconic(self.hwnd): win32gui.ShowWindow(self.hwnd,win32con.SW_RESTORE)
        try: win32gui.SetForegroundWindow(self.hwnd)
        except Exception: pass
    def is_alive(self): return bool(win32gui.IsWindow(self.hwnd))
