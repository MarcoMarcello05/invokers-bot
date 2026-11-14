import ctypes,time
import win32api,win32con

class InputController:
    def click_screen(self,x,y):
        win32api.SetCursorPos((int(x),int(y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0,0,0); time.sleep(.035)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)
    def key(self,name):
        keys={"esc":win32con.VK_ESCAPE,"enter":win32con.VK_RETURN,"space":win32con.VK_SPACE}
        vk=keys.get(name.lower())
        if vk is None: raise ValueError(f"Unsupported key: {name}")
        win32api.keybd_event(vk,0,0,0); time.sleep(.035); win32api.keybd_event(vk,0,win32con.KEYEVENTF_KEYUP,0)

def f12_pressed(): return bool(ctypes.windll.user32.GetAsyncKeyState(win32con.VK_F12)&0x8000)
