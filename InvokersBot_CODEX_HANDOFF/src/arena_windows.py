"""Windows adapter over existing PyAutoGUI/OCR/template helpers; no game policy.

All input is gated. Calibrated 1920x1080 reference ROIs are examples, not a claim
that a different desktop/window layout is safe. Unknown states never get clicks.
"""
import ctypes
import hashlib
import json
from pathlib import Path
import re
import sys
import threading
import time

from arena_actor import _norm, locate_name, search_selected_candidate
from arena_autopilot import ArenaError, ArenaFrame


def button_norm(text):
    # German OCR commonly loses umlauts. This is for control labels only, not
    # opponent identity; ambiguous player names must never get fuzzy matched.
    return _norm(text).translate(str.maketrans({'ä':'a','ö':'o','ü':'u'}))


DEFAULT_PROFILE = {
    'size': [1920, 1080], 'window_title': 'Invokers', 'max_scroll_steps': 14,
    'regions': {
        'list_markers': [0, 130, 1905, 285], 'names': [480, 290, 915, 1020],
        'row_fight': [1610, 290, 1880, 1020], 'own_power': [810, 130, 1045, 210],
        'opponent_name': [1390, 126, 1720, 180], 'formation_marker': [750, 885, 1210, 995],
        'start_battle': [1425, 885, 1760, 990], 'token_cost': [1582, 938, 1622, 978],
        'back': [0, 30, 325, 135], 'arena_menu': [250, 160, 1900, 1000],
        'result_marker': [400, 80, 1600, 780],
        'refresh': [1600, 150, 1890, 280],
    },
    'token_reference': 'src/templates/arena_token.png',
    'token_reference_roi': [0, 0, 34, 37],
    'token_search_roi': [1535, 932, 1585, 982], 'token_threshold': .97,
    'operator_confirmed_auto_off': False,
}


def load_profile(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('size') != [1920, 1080]:
        raise ValueError('Calibration requires explicit supported 1920x1080 geometry')
    for key in DEFAULT_PROFILE['regions']:
        roi = data.get('regions', {}).get(key)
        if not isinstance(roi, list) or len(roi) != 4 or any(type(v) is not int for v in roi):
            raise ValueError('Invalid/missing calibrated ROI: ' + key)
        if not (0 <= roi[0] < roi[2] <= 1920 and 0 <= roi[1] < roi[3] <= 1080):
            raise ValueError('ROI outside desktop: ' + key)
    if type(data.get('max_scroll_steps')) is not int or not 0 <= data['max_scroll_steps'] <= 30:
        raise ValueError('Scroll budget must be bounded')
    if type(data.get('operator_confirmed_auto_off')) is not bool:
        raise ValueError('Explicit AUTO-off observation required in calibration')
    if not .95 <= data.get('token_threshold', 0) <= 1:
        raise ValueError('Token recognition threshold must be .95..1')
    if data.get('token_reference') != DEFAULT_PROFILE['token_reference'] or data.get('token_reference_roi') != DEFAULT_PROFILE['token_reference_roi']:
        raise ValueError('Token currency reference is fixed; calibration cannot substitute a premium icon')
    roi = data.get('token_search_roi')
    start = data['regions']['start_battle']
    if not isinstance(roi,list) or len(roi)!=4 or any(type(v) is not int for v in roi) or not (start[0] <= roi[0] < roi[2] <= start[2] and start[1] <= roi[1] < roi[3] <= start[3]):
        raise ValueError('Token search must remain inside the start-battle control')
    return data


def profile_fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()



def validate_client_geometry(client_rect, expected_size, desktop_size):
    """Validate screen-space client bounds; never scale an uncalibrated layout."""
    left, top, right, bottom = client_rect
    width, height = right-left, bottom-top
    if (width, height) != tuple(expected_size) or width <= 0 or height <= 0:
        raise ArenaError('GEOMETRY_MISMATCH')
    if left < 0 or top < 0 or right > desktop_size[0] or bottom > desktop_size[1]:
        raise ArenaError('CLIENT_OUTSIDE_DESKTOP')
    return (left, top, right, bottom)


def windows_client_rect(hwnd):
    """Physical client-area bounds in desktop coordinates (not window frame)."""
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    user32.GetClientRect.restype = wintypes.BOOL
    user32.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
    user32.ClientToScreen.restype = wintypes.BOOL
    rect = wintypes.RECT()
    origin = wintypes.POINT(0, 0)
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)) or not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        raise ArenaError('CLIENT_GEOMETRY_UNAVAILABLE')
    return (origin.x, origin.y, origin.x + rect.right-rect.left, origin.y + rect.bottom-rect.top)


class WindowsArenaDesktop:
    simulated = False

    def __init__(self, profile, *, allow_navigation=False, allow_battle=False, stop_file=None):
        if sys.platform != 'win32':
            raise ArenaError('WINDOWS_REQUIRED')
        import pyautogui
        import screen_actor_v8 as screen
        self.pg, self.screen, self.profile = pyautogui, screen, profile
        self.pg.FAILSAFE = True
        self.pg.PAUSE = .1
        if screen.OCR_ENGINE is None:
            raise ArenaError('OCR_UNAVAILABLE')
        self.allow_navigation, self.allow_battle = allow_navigation, allow_battle
        self.stop_file = Path(stop_file) if stop_file else None
        self.stop_event = threading.Event()
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self._watch_stop, daemon=True)
        self.thread.start()
        try:
            self._baseline = self._verified_geometry()
        except Exception:
            self.close()
            raise

    def _watch_stop(self):
        while not self.closed.wait(.05):
            if ctypes.windll.user32.GetAsyncKeyState(0x77) & 0x8000:  # F8 globally, no admin hook.
                self.stop_event.set()

    def close(self):
        self.closed.set()
        self.thread.join(timeout=.2)

    def stopped(self):
        return self.stop_event.is_set() or bool(self.stop_file and self.stop_file.exists())

    def foreground(self):
        handle = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(handle)
        buffer = ctypes.create_unicode_buffer(length+1)
        ctypes.windll.user32.GetWindowTextW(handle, buffer, length+1)
        return buffer.value.casefold() == self.profile['window_title'].casefold()

    def _verified_geometry(self):
        """Fail closed if focus, client origin, size or DPI coordinate space changes."""
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        hwnd = user32.GetForegroundWindow()
        if not hwnd or not self.foreground():
            raise ArenaError('FOREGROUND_LOST')
        if user32.IsIconic(hwnd) or not user32.IsWindowVisible(hwnd):
            raise ArenaError('WINDOW_NOT_VISIBLE')
        desktop = tuple(self.pg.size())
        # PyAutoGUI and Win32 must agree about coordinate units. No silent DPI scaling.
        if desktop != (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)):
            raise ArenaError('DPI_COORDINATE_MISMATCH')
        rect = validate_client_geometry(windows_client_rect(hwnd), self.profile['size'], desktop)
        result = (hwnd, rect)
        if hasattr(self, '_baseline') and result != self._baseline:
            raise ArenaError('WINDOW_GEOMETRY_CHANGED')
        return result

    def _screen_point(self, point, region=None):
        """Translate verified client-local OCR/template points to desktop input."""
        if not isinstance(point, (tuple, list)) or len(point) != 2:
            raise ArenaError('CONTROL_UNCONFIRMED')
        x, y = point
        if not all(type(v) in (int, float) and v == v for v in (x, y)):
            raise ArenaError('CONTROL_UNCONFIRMED')
        if not (0 <= x < self.profile['size'][0] and 0 <= y < self.profile['size'][1]):
            raise ArenaError('CONTROL_OUTSIDE_CLIENT')
        if region is not None:
            x1, y1, x2, y2 = self.profile['regions'][region]
            if not (x1 <= x < x2 and y1 <= y < y2):
                raise ArenaError('CONTROL_OUTSIDE_REGION')
        _, (left, top, right, bottom) = self._verified_geometry()
        sx, sy = left + int(x), top + int(y)
        if not (left <= sx < right and top <= sy < bottom):
            raise ArenaError('CONTROL_OUTSIDE_CLIENT')
        return sx, sy

    def _client_image(self):
        _, (left, top, right, bottom) = self._verified_geometry()
        image = self.screen.shot()
        if image.shape[0] < bottom or image.shape[1] < right:
            raise ArenaError('SCREENSHOT_GEOMETRY_MISMATCH')
        self._verified_geometry()
        return image[top:bottom, left:right]

    def _rows(self, image, name):
        rows = self.screen.ocr_region(image, self.profile['regions'][name])
        return [{**r, 'conf': r['score']} for r in rows if r['score'] >= .85]

    @staticmethod
    def button(rows, *labels):
        wanted = {button_norm(label) for label in labels}
        hits = [r for r in rows if button_norm(r['text']) in wanted]
        return (hits[0]['x'], hits[0]['y']) if len(hits) == 1 else None

    def _token_icon(self, image):
        cv = self.screen.cv2
        root = Path(__file__).resolve().parents[1]
        path = Path(self.profile['token_reference'])
        path = path if path.is_absolute() else root/path
        if hashlib.sha256(path.read_bytes()).hexdigest() != '6be9ba022cebf3f75f9a9c06481d8e02bb6230ab66200180995f54aeb8b6dfae':
            return False
        reference = cv.imread(str(path), 0)
        if reference is None:
            return False
        x1,y1,x2,y2 = self.profile['token_reference_roi']
        template = reference[y1:y2, x1:x2]
        x1,y1,x2,y2 = self.profile['token_search_roi']
        crop = image[y1:y2, x1:x2]
        if not template.size or crop.shape[0] < template.shape[0] or crop.shape[1] < template.shape[1]:
            return False
        _, score, _, _ = cv.minMaxLoc(cv.matchTemplate(crop, template, cv.TM_CCOEFF_NORMED))
        return score >= self.profile['token_threshold']

    def observe(self):
        if self.stopped():
            raise ArenaError('STOP_REQUESTED')
        if not self.foreground():
            return ArenaFrame('UNKNOWN', safe_foreground=False)
        image = self._client_image()
        # First inspect potential modal labels. Never confirm an unknown overlay.
        all_rows = self.screen.ocr_region(image, (0, 30, 1920, 1028))
        if any(_norm(r['text']) in {_norm(x) for x in ('KAUFEN', 'BESTÄTIGEN', 'WIEDERBELEBEN', 'ABBRECHEN', 'OK')}
               and r['score'] >= .85 for r in all_rows):
            return ArenaFrame('DIALOG')
        back = self.button(self._rows(image, 'back'), 'ZURÜCK', 'BACK')
        controls = {'back': back} if back else {}
        # The original template means AUTO is OFF. It is never clicked to enable AUTO.
        auto_marker = self.screen.match('auto_off', image)
        if auto_marker and auto_marker.score >= .95:
            return ArenaFrame('BATTLE', auto_off=True)
        result_rows = self._rows(image, 'result_marker')
        victory_marker = self.screen.match('victory', image)
        if victory_marker and victory_marker.score >= .95:
            return ArenaFrame('VICTORY', controls={**controls, 'return_to_arena': back} if back else controls)
        if self.button(result_rows, 'NIEDERLAGE', 'DEFEAT'):
            return ArenaFrame('DEFEAT', controls={**controls, 'return_to_arena': back} if back else controls)
        marker = self._rows(image, 'formation_marker')
        start = self.button(self._rows(image, 'start_battle'), 'KÄMPFEN', 'KAMPFEN', 'FIGHT')
        if start and any(button_norm(r['text']) == button_norm('Unterstützung') for r in marker):
            power_rows = self._rows(image, 'own_power')
            values = [int(r['text'].replace('.', '').replace(' ', '')) for r in power_rows
                      if re.fullmatch(r'\d{1,3}(?:\.\d{3})+|\d{3,7}', r['text'].replace(' ', ''))]
            names = [r['text'] for r in self._rows(image, 'opponent_name')
                     if not re.fullmatch(r'[\d\s.,]+', r['text'])]
            cost = self._rows(image, 'token_cost')
            one = len(cost) == 1 and cost[0]['text'].strip() == '1'
            return ArenaFrame('FORMATION', selected_name=names[0] if len(names)==1 else None,
                              own_power=values[0] if len(values)==1 else None,
                              token_cost=1 if one else None, token_currency_verified=self._token_icon(image),
                              controls={**controls, 'start_battle': start})
        markers = {_norm(r['text']) for r in self._rows(image, 'list_markers')}
        if _norm('ANGRIFF') in markers and _norm('AKTUALISIEREN') in markers:
            names = self._rows(image, 'names')
            fights = self._rows(image, 'row_fight')
            refresh_rows = self._rows(image, 'refresh')
            refresh = self.button(refresh_rows, 'AKTUALISIEREN')
            free = bool(refresh and self.button(refresh_rows, 'KOSTENLOS', 'FREE'))
            return ArenaFrame('ARENA_LIST', rows=names, free_refresh_verified=free,
                              controls={**controls, 'row_buttons': fights, **({'refresh': refresh} if free else {})})
        arena = self.button(self._rows(image, 'arena_menu'), 'ARENA')
        if arena:
            return ArenaFrame('BATTLE_MENU', controls={'open_arena': arena})
        home = self.screen.match('home_fight', image)
        if home:
            return ArenaFrame('HOME', controls={'open_battles': (home.x, home.y)})
        return ArenaFrame('UNKNOWN')

    def locate(self, target, observe, check_stop):
        from arena_actor import _norm
        def checked():
            frame = observe()
            if frame.state != 'ARENA_LIST':
                raise ArenaError('LIST_SCREEN_LOST')
            return frame
        def scroll(direction):
            check_stop()
            if not self.allow_navigation or not self.foreground():
                raise ArenaError('NAVIGATION_NOT_AUTHORIZED')
            # Scroll in the verified list area, never at a desktop-global coordinate.
            x1, y1, x2, y2 = self.profile['regions']['names']
            point = self._screen_point(((x1+x2)//2, (y1+y2)//2), 'names')
            self.pg.moveTo(*point, duration=.1)
            self._verified_geometry()
            if self.stopped():
                raise ArenaError('STOP_REQUESTED')
            self.pg.scroll(5 if direction == 'up' else -5)
            time.sleep(.45)
        found, meta = search_selected_candidate(target, checked, scroll, self.stopped,
                                                 self.profile['max_scroll_steps'])
        if not found:
            return None
        frame, name = found
        # Only the unique fight button on that exact row may open formation.
        buttons = [r for r in frame.controls.get('row_buttons', [])
                   if _norm(r['text']) in {_norm('KÄMPFEN'), _norm('KAMPFEN'), _norm('FIGHT')}
                   and abs(r['y'] - name['y']) <= 70]
        if len(buttons) != 1:
            raise ArenaError('ROW_BUTTON_AMBIGUOUS', 'No unique active fight button for the selected identity')
        return frame, (buttons[0]['x'], buttons[0]['y'])

    def perform(self, command, frame, target=None):
        if self.stopped():
            raise ArenaError('STOP_REQUESTED')
        if not self.allow_navigation or (command == 'start_battle' and not self.allow_battle):
            raise ArenaError('INPUT_NOT_AUTHORIZED')
        time.sleep(.15)
        fresh = self.observe()
        if fresh.state != frame.state:
            raise ArenaError('UI_CHANGED_BEFORE_CLICK')
        if command == 'open_formation':
            hit = locate_name(target['opponent']['name'], fresh.rows)
            if hit is None:
                raise ArenaError('IDENTITY_DISAPPEARED')
            buttons = [r for r in fresh.controls.get('row_buttons', [])
                       if _norm(r['text']) in {_norm('KÄMPFEN'), _norm('KAMPFEN'), _norm('FIGHT')}
                       and abs(r['y']-hit['y']) <= 70]
            if len(buttons) != 1:
                raise ArenaError('ROW_BUTTON_AMBIGUOUS')
            point = (buttons[0]['x'], buttons[0]['y'])
            if any(abs(a-b)>3 for a,b in zip(point, target['point'])):
                raise ArenaError('CONTROL_MOVED')
        else:
            point = fresh.controls.get(command)
            if not point or point != frame.controls.get(command):
                raise ArenaError('CONTROL_UNCONFIRMED', command)
        if command == 'start_battle':
            if not self.profile['operator_confirmed_auto_off']:
                raise ArenaError('AUTO_NOT_CONFIRMED_OFF')
            if _norm(fresh.selected_name or '') != _norm(target['name']) or fresh.own_power != frame.own_power or fresh.token_cost != 1 or not fresh.token_currency_verified:
                raise ArenaError('FORMATION_CHANGED_BEFORE_CLICK')
        if command == 'refresh' and not fresh.free_refresh_verified:
            raise ArenaError('REFRESH_COST_UNVERIFIED')
        if not self.foreground() or self.stopped():
            raise ArenaError('FOREGROUND_LOST')
        region = {
            'open_battles': None, 'open_arena': 'arena_menu',
            'open_formation': 'row_fight', 'start_battle': 'start_battle',
            'refresh': 'refresh', 'back': 'back', 'return_to_arena': 'back',
        }.get(command)
        if command not in ('open_battles', 'open_arena', 'open_formation',
                           'start_battle', 'refresh', 'back', 'return_to_arena'):
            raise ArenaError('UNKNOWN_COMMAND')
        # Templates may be elsewhere within the client, but never outside it.
        screen_point = self._screen_point(point, region)
        if self.stopped():
            raise ArenaError('STOP_REQUESTED')
        self.pg.click(*screen_point)

    def screenshot(self, path):
        self._verified_geometry()
        self.pg.screenshot().save(path)
        return str(path)
