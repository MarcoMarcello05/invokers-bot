"""Read-only foreground window diagnostics. Never imports an input backend."""
import argparse
import ctypes
import json
from pathlib import Path
import sys
import time

from arena_windows import load_profile, windows_client_rect


def compare_geometry(desktop, rect, profile):
    left, top, right, bottom = rect
    size = [right-left, bottom-top]
    expected = profile['size']
    return {'desktop_size': list(desktop), 'client_rect': list(rect),
            'client_size': size, 'expected_client_size': expected,
            'size_delta': [a-b for a,b in zip(size, expected)],
            'matches_size': size == expected,
            'inside_primary_desktop': 0 <= left < right <= desktop[0] and 0 <= top < bottom <= desktop[1]}


def capture(profile, output):
    if sys.platform != 'win32':
        raise RuntimeError('Windows required')
    from ctypes import wintypes
    from PIL import ImageGrab, ImageDraw
    u = ctypes.windll.user32
    # Set per-monitor awareness before querying coordinates or taking screenshots.
    u.SetThreadDpiAwarenessContext.argtypes = (ctypes.c_void_p,)
    u.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    previous = u.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    if not previous:
        raise RuntimeError('Per-monitor DPI context unavailable')
    try:
        u.GetForegroundWindow.restype = wintypes.HWND
        u.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        u.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
        u.GetDpiForWindow.argtypes = (wintypes.HWND,)
        u.GetDpiForWindow.restype = wintypes.UINT
        hwnd = u.GetForegroundWindow()
        title = ctypes.create_unicode_buffer(512)
        u.GetWindowTextW(hwnd, title, len(title))
        if title.value.casefold() != profile['window_title'].casefold():
            raise RuntimeError('Game must be foreground; no screenshot taken')
        rect = windows_client_rect(hwnd)
        outer = wintypes.RECT()
        if not u.GetWindowRect(hwnd, ctypes.byref(outer)):
            raise RuntimeError('Window rectangle unavailable')
        desktop = (u.GetSystemMetrics(0), u.GetSystemMetrics(1))
        report = compare_geometry(desktop, rect, profile)
        dpi = u.GetDpiForWindow(hwnd)
        report.update(window_rect=[outer.left,outer.top,outer.right,outer.bottom],
                      window_dpi=dpi or None, dpi_percent=round(dpi/96*100,2) if dpi else None,
                      coordinate_context='per_monitor_v2', input_enabled=False)
        if report['inside_primary_desktop']:
            image = ImageGrab.grab(bbox=rect)
            if u.GetForegroundWindow() != hwnd or windows_client_rect(hwnd) != rect:
                raise RuntimeError('Window changed during capture')
            if list(image.size) != report['client_size']:
                raise RuntimeError('Screenshot dimensions differ')
            draw = ImageDraw.Draw(image)
            for name, roi in profile['regions'].items():
                x1,y1,x2,y2 = roi
                if x2 <= image.width and y2 <= image.height:
                    draw.rectangle((x1,y1,x2-1,y2-1),outline='yellow',width=2)
                    draw.text((x1,y1),name,fill='yellow',stroke_width=1,stroke_fill='black')
            output.mkdir(parents=True,exist_ok=True)
            image.save(output/'client_rois.png')
            report['overlay'] = 'client_rois.png'
        report['unscaled_outside_rois'] = [k for k,r in profile['regions'].items()
                                           if r[2]>report['client_size'][0] or r[3]>report['client_size'][1]]
        output.mkdir(parents=True,exist_ok=True)
        (output/'geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        return report
    finally:
        u.SetThreadDpiAwarenessContext(previous)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibration',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--delay',type=int,choices=range(0,16),default=5)
    args=parser.parse_args()
    profile=load_profile(args.calibration)
    time.sleep(args.delay)
    print(json.dumps(capture(profile,args.output),indent=2))


if __name__=='__main__':
    main()
