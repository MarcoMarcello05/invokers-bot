import ctypes
from ctypes import wintypes
import win32con

ULONG_PTR = wintypes.WPARAM

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", INPUTUNION)]

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
KEYEVENTF_KEYUP = 0x0002

_user32 = ctypes.windll.user32
_send_input = _user32.SendInput
_send_input.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
_send_input.restype = wintypes.UINT

def _send(events):
    arr = (INPUT * len(events))(*events)
    sent = _send_input(len(events), arr, ctypes.sizeof(INPUT))
    if sent != len(events):
        raise OSError(ctypes.get_last_error(), f"SendInput inserted {sent}/{len(events)} events")

class InputController:
    def _absolute(self, x, y):
        vx = _user32.GetSystemMetrics(76)
        vy = _user32.GetSystemMetrics(77)
        vw = max(1, _user32.GetSystemMetrics(78) - 1)
        vh = max(1, _user32.GetSystemMetrics(79) - 1)
        ax = round((int(x) - vx) * 65535 / vw)
        ay = round((int(y) - vy) * 65535 / vh)
        return ax, ay

    def click_screen(self, x, y):
        ax, ay = self._absolute(x, y)
        move = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(
            ax, ay, 0,
            MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
            0, 0
        ))
        down = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0))
        up = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0))
        _send([move, down, up])

    def key(self, name):
        keys = {"esc": win32con.VK_ESCAPE, "enter": win32con.VK_RETURN, "space": win32con.VK_SPACE}
        vk = keys.get(name.lower())
        if vk is None:
            raise ValueError(f"Unsupported key: {name}")
        down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, 0, 0, 0))
        up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, 0))
        _send([down, up])

def f12_pressed():
    return bool(_user32.GetAsyncKeyState(win32con.VK_F12) & 0x8000)
