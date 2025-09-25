from flask import Flask, render_template, request, jsonify
import os
import sys
import pyautogui
import threading
import time
import math
import platform

# On Windows we can query the virtual screen bounds so the cursor can move across
# multiple monitors. Fall back to primary monitor size on other platforms.
virtual_left = 0
virtual_top = 0
screen_width = 0
screen_height = 0

# WebSocket support
from flask_socketio import SocketIO

# Support running from a PyInstaller one-file/one-folder bundle by resolving
# the runtime base directory. When bundled, PyInstaller exposes a temporary
# extraction dir at sys._MEIPASS where data files are placed.
base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, static_folder=os.path.join(base_dir, 'static'), template_folder=os.path.join(base_dir, 'templates'))
import traceback
import logging
try:
    # Monkey-patch Werkzeug serving logger to suppress access log lines with date/time
    from werkzeug import serving as _wz_serving
    _wz_serving._log = lambda *args, **kwargs: None  # type: ignore[attr-defined]
except Exception:
    pass

# Suppress verbose Werkzeg access logs (date/time, status lines) to keep console clean
try:
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
except Exception:
    pass

# Try to initialize SocketIO with a list of candidate async modes. If none
# succeed (common when the bundled environment is missing or incompatible
# async libraries), fall back to a lightweight stub that preserves the
# decorator API but runs a plain Flask HTTP server. This keeps the app
# functional (HTTP endpoints work) even when real WebSocket support isn't
# available inside a packaged exe.
socketio = None
async_candidates = ['eventlet', 'gevent', 'threading', 'asyncio']
for mode in async_candidates:
    try:
        socketio = SocketIO(app, cors_allowed_origins='*', async_mode=mode, logger=False, engineio_logger=False)
        print(f"SocketIO initialized with async_mode={mode}")
        break
    except Exception as e:
        print(f"SocketIO init failed for async_mode={mode}: {e}")
        traceback.print_exc()

if socketio is None:
    print('Warning: Unable to initialize a real SocketIO backend. Falling back to HTTP-only stub (no websockets).')
    class StubSocketIO:
        def on(self, *args, **kwargs):
            # return a decorator that leaves the function unchanged
            def decorator(f):
                return f
            return decorator
        def emit(self, *args, **kwargs):
            return None
        def run(self, app, host='0.0.0.0', port=51273, debug=False):
            # Run plain Flask server
            app.run(host=host, port=port, debug=debug)
    socketio = StubSocketIO()

# Configure pyautogui
pyautogui.FAILSAFE = True  # Move mouse to corner to stop
pyautogui.PAUSE = 0.0001   # Small pause between commands

# Server-side multiplier for incoming fractional scroll values. Increase if scroll feels weak.
SCROLL_MULTIPLIER = 2
# Server-side multiplier for incoming move deltas. Increase to amplify movement,
# decrease to make movement less sensitive. Client already applies sensitivity,
# but a server multiplier lets the server globally tune responsiveness.
MOVE_MULTIPLIER = 0.1
# Mouse acceleration settings (tweak to taste)
# BASE_SPEED_SCALE: baseline multiplier applied regardless of speed
# ACCEL_EXPONENT: exponent used in the acceleration curve (values >1 increase acceleration)
# ACCELERATION_FACTOR: scales the speed before applying exponent
# ACCEL_CAP: maximum multiplier allowed to avoid runaway motion
BASE_SPEED_SCALE = 0.2
ACCEL_EXPONENT = 1.1
ACCELERATION_FACTOR = 0.2
ACCEL_CAP = 40.0
# Toggle to print incoming scroll payloads (for troubleshooting); set False to silence
SCROLL_DEBUG = False
# Toggle to print incoming raw touch positions (down/move/up)
RAW_DEBUG = False
# If accumulated fractional scroll (after multiplying) exceeds this small value,
# force one wheel step in the appropriate direction. Helps small gestures move the page.
MIN_SCROLL_FRAC_TO_STEP = 0.05
# Accumulators and threshold for move deltas (so tiny client movements still result
# in eventual mouse movement). Works like scroll accumulators: we store fractional
# pixels until they add up to at least one pixel, or a small fractional threshold
# triggers a minimal one-pixel step.
move_accum_x = 0.0
move_accum_y = 0.0
move_lock = threading.Lock()
# If fractional accumulated move exceeds this, force a one-pixel move
MIN_MOVE_FRAC_TO_STEP = 0.05
# Tap detection thresholds (server-side)
TAP_TIMEOUT_MS = 200
TAP_MOVE_THRESHOLD = 4.0
# Speed-based scroll acceleration: larger finger deltas produce proportionally
# larger scroll amounts. Tune these constants to taste.
# SCROLL_ACCEL_FACTOR multiplies the effect of the measured delta magnitude.
# SCROLL_ACCEL_CAP prevents runaway amplification from noisy very large deltas.
SCROLL_ACCEL_FACTOR = 2
SCROLL_ACCEL_CAP = 2000.0
# Double-tap-and-hold safety: if a held mouseDown is not released by the client
# within this timeout, the server will auto-release to avoid a stuck mouse state.
DOUBLE_TAP_HOLD_TIMEOUT_MS = 3000
# Double-tap timing: max interval between taps and hold trigger duration
DOUBLE_TAP_MAX_INTERVAL_MS = 200
DOUBLE_TAP_HOLD_TRIGGER_MS = 200

# Get screen size for scaling. Prefer virtual screen on Windows so multiple
# monitors are supported.
def detect_screen_bounds():
    global virtual_left, virtual_top, screen_width, screen_height
    try:
        if platform.system() == 'Windows':
            # Use Win32 GetSystemMetrics for virtual screen bounds
            import ctypes
            user32 = ctypes.windll.user32
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            virtual_left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
            virtual_top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
            screen_width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
            screen_height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
        else:
            # Non-Windows: fall back to pyautogui primary screen size and origin 0,0
            virtual_left = 0
            virtual_top = 0
            w, h = pyautogui.size()
            screen_width = int(w)
            screen_height = int(h)
    except Exception:
        # Last-resort fallback
        virtual_left = 0
        virtual_top = 0
        w, h = pyautogui.size()
        screen_width = int(w)
        screen_height = int(h)


# Initialize screen bounds
detect_screen_bounds()

# Accumulators to buffer fractional scrolls so very small client deltas still result in scrolling
scroll_accum_x = 0.0
scroll_accum_y = 0.0
scroll_lock = threading.Lock()


def _try_hscroll(amount):
    """Try a native horizontal scroll; fall back to shift+vertical scroll if unavailable."""
    try:
        pyautogui.hscroll(int(amount))
    except Exception:
        try:
            if amount > 0:
                pyautogui.keyDown('shift')
                pyautogui.scroll(int(abs(amount)))
                pyautogui.keyUp('shift')
            else:
                pyautogui.keyDown('shift')
                pyautogui.scroll(-int(abs(amount)))
                pyautogui.keyUp('shift')
        except Exception as e:
            print('_try_hscroll error', e)


def _press_key_combo(mods, key):
    """Press modifier keys + a key. Try pyautogui first, then a Windows ctypes fallback.

    mods: list of modifier names such as ['winleft'] or ['alt']
    key: single key name like 'tab' or 'esc'
    """
    try:
        for m in mods:
            pyautogui.keyDown(m)
        pyautogui.press(key)
        for m in reversed(mods):
            pyautogui.keyUp(m)
    except Exception:
        # Windows fallback using keybd_event for common keys
        try:
            import ctypes
            user32 = ctypes.windll.user32
            vk_map = {'winleft': 0x5B, 'alt': 0x12}
            key_map = {'tab': 0x09, 'esc': 0x1B}
            # press modifiers
            for m in mods:
                vk = vk_map.get(m)
                if vk:
                    user32.keybd_event(vk, 0, 0, 0)
            # press key
            k = key_map.get(key)
            if k:
                user32.keybd_event(k, 0, 0, 0)
                user32.keybd_event(k, 0, 2, 0)
            # release modifiers
            for m in reversed(mods):
                vk = vk_map.get(m)
                if vk:
                    user32.keybd_event(vk, 0, 2, 0)
        except Exception as e:
            print('_press_key_combo fallback failed', e)


def _press_single_key(key):
    """Press a single key, with ctypes fallback for Windows."""
    try:
        pyautogui.press(key)
    except Exception:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            key_map = {'esc': 0x1B, 'tab': 0x09}
            k = key_map.get(key)
            if k:
                user32.keybd_event(k, 0, 0, 0)
                user32.keybd_event(k, 0, 2, 0)
        except Exception as e:
            print('_press_single_key fallback failed', e)

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/click', methods=['POST'])
def click_mouse():
    try:
        data = request.json
        button = data.get('button', 'left')  # left, right, middle
        
        if button == 'left':
            pyautogui.click()
        elif button == 'right':
            pyautogui.rightClick()
        elif button == 'middle':
            pyautogui.middleClick()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/scroll', methods=['POST'])
def scroll_mouse():
    try:
        data = request.json
        scroll_x = float(data.get('scrollX', 0))
        scroll_y = float(data.get('scrollY', 0))
        if SCROLL_DEBUG:
            print(f"/scroll received: scroll_x={scroll_x:.4f}, scroll_y={scroll_y:.4f}")
        
        # Vertical scrolling (most common)
        if scroll_y != 0:
            # Accumulate fractional scroll amounts so small movements add up
            with scroll_lock:
                global scroll_accum_y
                scroll_accum_y += scroll_y * SCROLL_MULTIPLIER
                # If we've reached at least one whole wheel step, send that many
                scroll_amount = int(scroll_accum_y)
                if scroll_amount != 0:
                    pyautogui.scroll(scroll_amount)
                    scroll_accum_y -= scroll_amount
                else:
                    # If fractional accumulation is significant, send a minimal step
                    if abs(scroll_accum_y) >= MIN_SCROLL_FRAC_TO_STEP:
                        step = int(math.copysign(1, scroll_accum_y))
                        pyautogui.scroll(step)
                        scroll_accum_y -= step
        
        # Horizontal scrolling (less common, but supported on some systems)
        if scroll_x != 0:
            # Try native horizontal scroll if available; accumulate like vertical
            with scroll_lock:
                global scroll_accum_x
                scroll_accum_x += scroll_x * SCROLL_MULTIPLIER
                scroll_amount_x = int(scroll_accum_x)
                if scroll_amount_x != 0:
                    _try_hscroll(scroll_amount_x)
                    scroll_accum_x -= scroll_amount_x
                else:
                    if abs(scroll_accum_x) >= MIN_SCROLL_FRAC_TO_STEP:
                        step_x = int(math.copysign(1, scroll_accum_x))
                        _try_hscroll(step_x)
                        scroll_accum_x -= step_x
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})





@socketio.on('click')
def on_click(data):
    try:
        button = data.get('button', 'left')
        if button == 'left':
            pyautogui.click()
        elif button == 'right':
            pyautogui.rightClick()
        elif button == 'middle':
            pyautogui.middleClick()
    except Exception as e:
        print('on_click error', e)


@socketio.on('scroll')
def on_scroll(data):
    try:
        scroll_x = float(data.get('scrollX', 0))
        scroll_y = float(data.get('scrollY', 0))
        if SCROLL_DEBUG:
            print(f"[socket] /scroll received: scroll_x={scroll_x:.4f}, scroll_y={scroll_y:.4f}")

        # Accumulate vertical fractional scrolls like HTTP handler
        if scroll_y != 0:
            with scroll_lock:
                global scroll_accum_y
                scroll_accum_y += scroll_y * SCROLL_MULTIPLIER
                scroll_amount = int(scroll_accum_y)
                if scroll_amount != 0:
                    pyautogui.scroll(scroll_amount)
                    scroll_accum_y -= scroll_amount
                else:
                    # If fractional accumulation is significant, send a minimal step
                    if abs(scroll_accum_y) >= MIN_SCROLL_FRAC_TO_STEP:
                        step = int(math.copysign(1, scroll_accum_y))
                        pyautogui.scroll(step)
                        scroll_accum_y -= step

        # Accumulate horizontal fractional scrolls
        if scroll_x != 0:
            with scroll_lock:
                global scroll_accum_x
                scroll_accum_x += scroll_x * SCROLL_MULTIPLIER
                scroll_amount_x = int(scroll_accum_x)
                if scroll_amount_x != 0:
                    try:
                        pyautogui.hscroll(scroll_amount_x)
                    except Exception:
                        if scroll_amount_x > 0:
                            pyautogui.keyDown('shift')
                            pyautogui.scroll(int(abs(scroll_amount_x)))
                            pyautogui.keyUp('shift')
                        else:
                            pyautogui.keyDown('shift')
                            pyautogui.scroll(-int(abs(scroll_amount_x)))
                            pyautogui.keyUp('shift')
                    scroll_accum_x -= scroll_amount_x
    except Exception as e:
        print('on_scroll error', e)


# Per-connection touch state for raw events
touch_state = {}


def process_move_delta(delta_x, delta_y):
    """Apply a raw delta (in client pixels) to the host mouse using server-side
    multiplier and virtual-screen clamping. Always reflect any non-zero input
    immediately with at least a 1-pixel step in the appropriate direction.
    """
    try:
        # Time sampling
        now = time.time()
        last = getattr(process_move_delta, '_last_time', None)
        dt = 0.016 if last is None else max(1e-4, now - last)
        process_move_delta._last_time = now

        # Localize globals and math functions for speed
        mv_mul = MOVE_MULTIPLIER
        accel_factor = ACCELERATION_FACTOR
        accel_exp = ACCEL_EXPONENT
        base_scale = BASE_SPEED_SCALE
        cap = ACCEL_CAP

        # Scale raw client deltas
        dx_raw = float(delta_x) * mv_mul
        dy_raw = float(delta_y) * mv_mul

        # Speed magnitude (pixels/sec)
        speed = math.hypot(dx_raw, dy_raw) / dt if dt > 0 else 0.0

        # Acceleration multiplier (fast path for speed == 0 avoids pow)
        if speed > 0.0:
            accel_mult = base_scale + (accel_factor * speed) ** accel_exp
            if accel_mult > cap:
                accel_mult = cap
        else:
            accel_mult = base_scale

        dx_acc = dx_raw * accel_mult
        dy_acc = dy_raw * accel_mult

        # Accumulate and apply integer steps under lock
        with move_lock:
            global move_accum_x, move_accum_y
            move_accum_x += dx_acc
            move_accum_y += dy_acc

            # Use rounding to nearest to reduce bias for small fractions
            dx_apply = int(round(move_accum_x))
            dy_apply = int(round(move_accum_y))

            # Ensure minimal step when fractional accumulation passes threshold
            if dx_apply == 0 and abs(move_accum_x) >= MIN_MOVE_FRAC_TO_STEP:
                dx_apply = int(math.copysign(1, move_accum_x))
            if dy_apply == 0 and abs(move_accum_y) >= MIN_MOVE_FRAC_TO_STEP:
                dy_apply = int(math.copysign(1, move_accum_y))

            if dx_apply != 0:
                move_accum_x -= dx_apply
            if dy_apply != 0:
                move_accum_y -= dy_apply

        if dx_apply != 0 or dy_apply != 0:
            cx, cy = pyautogui.position()
            nx = cx + dx_apply
            ny = cy + dy_apply
            # Clamp to virtual screen bounds
            nx = max(virtual_left, min(virtual_left + screen_width - 1, nx))
            ny = max(virtual_top, min(virtual_top + screen_height - 1, ny))
            try:
                pyautogui.moveTo(nx, ny)
            except Exception:
                pass
    except Exception as e:
        # Keep a minimal, non-throwing error path
        print('process_move_delta error', e)


# Raw input handlers - client emits raw.down, raw.move, raw.up (coalesced moves supported)
def _get_sid_for_http():
    # Use client IP as a stable key for HTTP fallback clients (so successive
    # /raw posts from the same device share state). If remote_addr is unavailable
    # fall back to a generic 'http' key.
    try:
        addr = request.remote_addr or 'unknown'
        return f'http:{addr}'
    except Exception:
        return 'http:unknown'


def process_raw_down(data, sid_key):
    try:
        if RAW_DEBUG:
            try:
                print(f"down id={data.get('id')} x={float(data.get('x', 0)):.1f} y={float(data.get('y', 0)):.1f}")
            except Exception:
                pass
        st = touch_state.setdefault(sid_key, {'touches': {}, 'threeFingerAccumY': 0.0, 'threeFingerTriggeredUp': False, 'threeFingerTriggeredDown': False, 'doubleTapHoldActive': False, 'suppressMoveUntil': 0, 'lastMouseDownTime': 0, 'lastMouseDownSid': None, 'lastTapTime': 0, 'pendingDoubleTap': False})
        # Clear any stale pending double-tap marker
        now_ms = time.time() * 1000
        if st.get('pendingDoubleTap') and (now_ms - st.get('lastTapTime', 0) > DOUBLE_TAP_MAX_INTERVAL_MS):
            st['pendingDoubleTap'] = False

        # If a pending double-tap exists and this down occurs quickly after the last tap,
        # treat this as the second tap's down; enter the "expect hold to start drag" state.
        if st.get('pendingDoubleTap') and (now_ms - st.get('lastTapTime', 0) <= DOUBLE_TAP_MAX_INTERVAL_MS):
            st['pendingDoubleTap'] = False
            st['doubleTapExpectHold'] = True
            st['doubleTapDownTime'] = now_ms
        tid = data.get('id')
        x = float(data.get('x', 0))
        y = float(data.get('y', 0))
        now = time.time() * 1000
        # Track per-touch recent deltas so two-finger scroll can use recent
        # movement instead of a cumulative start->last value which would
        # otherwise be re-applied repeatedly.
        st['touches'][tid] = {'lastX': x, 'lastY': y, 'startX': x, 'startY': y, 'startTime': now, 'hasMoved': False, 'totalDistance': 0.0, 'lastDeltaX': 0.0, 'lastDeltaY': 0.0}
        # Record how many touches were active at down time (used to decide click type)
        try:
            st['touches'][tid]['touchCountAtDown'] = len(st['touches'])
        except Exception:
            st['touches'][tid]['touchCountAtDown'] = 1
    except Exception as e:
        print('process_raw_down error', e)


def process_raw_move(data, sid_key):
    try:
        st = touch_state.setdefault(sid_key, {'touches': {}, 'threeFingerAccumY': 0.0, 'threeFingerTriggeredUp': False, 'threeFingerTriggeredDown': False, 'doubleTapHoldActive': False, 'suppressMoveUntil': 0, 'lastMouseDownTime': 0, 'lastMouseDownSid': None, 'lastTapTime': 0, 'pendingDoubleTap': False})
        tid = data.get('id')
        x = float(data.get('x', 0))
        y = float(data.get('y', 0))
        if RAW_DEBUG:
            try:
                print(f"move id={tid} x={x:.1f} y={y:.1f}")
            except Exception:
                pass

        touches = st['touches']
        touch = touches.get(tid)
        dx = dy = 0.0
        if touch is not None:
            lx = touch['lastX']
            ly = touch['lastY']
            dx = x - lx
            dy = y - ly
            dist = math.hypot(dx, dy)
            touch['lastX'] = x
            touch['lastY'] = y
            touch['totalDistance'] += dist
            touch['lastDeltaX'] = dx
            touch['lastDeltaY'] = dy
            if touch['totalDistance'] > 4:
                touch['hasMoved'] = True

        # Auto-release stale double-tap-hold
        now_check = time.time() * 1000
        if st.get('doubleTapHoldActive') and st.get('lastMouseDownTime', 0) and (now_check - st.get('lastMouseDownTime', 0) > DOUBLE_TAP_HOLD_TIMEOUT_MS):
            try:
                pyautogui.mouseUp()
            except Exception:
                pass
            st['doubleTapHoldActive'] = False
            st['lastMouseDownTime'] = 0

        # Handle double-tap-expect-hold
        now_ms = now_check
        if st.get('doubleTapExpectHold') and st.get('doubleTapDownTime', 0):
            if (now_ms - st.get('doubleTapDownTime', 0)) >= DOUBLE_TAP_HOLD_TRIGGER_MS:
                try:
                    pyautogui.mouseDown()
                except Exception:
                    pass
                st['doubleTapHoldActive'] = True
                st['lastMouseDownTime'] = now_ms
                st['lastMouseDownSid'] = sid_key
                st['doubleTapExpectHold'] = False

        # Suppress tiny moves after right-click
        if st.get('suppressMoveUntil', 0) > now_ms:
            if touch is not None:
                touch['lastDeltaX'] = 0.0
                touch['lastDeltaY'] = 0.0
            return

        n = len(touches)
        if n == 1:
            process_move_delta(dx, dy)
            return

        if n == 2:
            # Aggregate lastDeltaY across touches
            totalDelta = 0.0
            speed_acc = 0.0
            count = 0
            for td in touches.values():
                ldy = td.get('lastDeltaY', 0.0)
                totalDelta += ldy
                speed_acc += abs(ldy)
                count += 1
            if count:
                avgDy = totalDelta / float(count)
                speed = speed_acc / float(count)
                accel = 1.0 + min(SCROLL_ACCEL_CAP, speed) * SCROLL_ACCEL_FACTOR
                scroll_val = -avgDy * SCROLL_MULTIPLIER * accel
                with scroll_lock:
                    global scroll_accum_y
                    scroll_accum_y += scroll_val
                    scroll_amount = int(scroll_accum_y)
                    if scroll_amount != 0:
                        pyautogui.scroll(scroll_amount)
                        scroll_accum_y -= scroll_amount
                    else:
                        if abs(scroll_accum_y) >= MIN_SCROLL_FRAC_TO_STEP:
                            step = int(math.copysign(1, scroll_accum_y))
                            pyautogui.scroll(step)
                            scroll_accum_y -= step
                # zero out consumed per-touch deltas
                for td in touches.values():
                    td['lastDeltaY'] = 0.0
            return

        if n == 3:
            avgDeltaY = 0.0
            count = 0
            for td in touches.values():
                avgDeltaY += (td['lastY'] - td['startY'])
                count += 1
            if count:
                avg = avgDeltaY / count
                st['threeFingerAccumY'] += -avg
                if not st['threeFingerTriggeredUp'] and st['threeFingerAccumY'] >= 12:
                    st['threeFingerTriggeredUp'] = True
                    try:
                        _press_key_combo(['winleft'], 'tab')
                    except Exception:
                        pass
                if not st['threeFingerTriggeredDown'] and st['threeFingerAccumY'] <= -12:
                    st['threeFingerTriggeredDown'] = True
                    try:
                        _press_single_key('esc')
                    except Exception:
                        pass
            return
    except Exception as e:
        print('process_raw_move error', e)


def process_raw_up(data, sid_key):
    try:
        if RAW_DEBUG:
            try:
                print(f"up   id={data.get('id')} x={float(data.get('x', 0)):.1f} y={float(data.get('y', 0)):.1f}")
            except Exception:
                pass
        st = touch_state.setdefault(sid_key, {'touches': {}, 'threeFingerAccumY': 0.0, 'threeFingerTriggeredUp': False, 'threeFingerTriggeredDown': False, 'doubleTapHoldActive': False, 'suppressMoveUntil': 0, 'lastMouseDownTime': 0, 'lastMouseDownSid': None, 'lastTapTime': 0, 'pendingDoubleTap': False})
        tid = data.get('id')
        # If touch exists, determine if it was a tap (short duration, little movement)
        touch = st['touches'].get(tid)
        if touch:
            duration = (time.time() * 1000) - float(touch.get('startTime', 0))
            moved = touch.get('hasMoved', False)
            total_dist = touch.get('totalDistance', 0.0)
            # Consider it a tap if it didn't move much and was quick
            if (not moved or total_dist <= TAP_MOVE_THRESHOLD) and duration <= TAP_TIMEOUT_MS:
                now_ms = time.time() * 1000
                # If we were expecting the second tap's hold but the user released before
                # the hold threshold, treat this as a double-click and clear the expect flag.
                if st.get('doubleTapExpectHold'):
                    try:
                        pyautogui.doubleClick()
                    except Exception:
                        pass
                    st['doubleTapExpectHold'] = False
                    st['pendingDoubleTap'] = False
                    st['lastTapTime'] = 0
                    # remove touch and return early
                    if tid in st['touches']:
                        del st['touches'][tid]
                    return
                # Decide click type by number of fingers that started the touch
                count = int(touch.get('touchCountAtDown', 1))
                try:
                    if count == 1:
                        pyautogui.click()
                        # mark this as a tap that could become the first half of a double-tap
                        st['lastTapTime'] = now_ms
                        st['pendingDoubleTap'] = True
                    elif count == 2:
                        pyautogui.rightClick()
                        # suppress tiny moves after right-click to avoid closing context menu
                        st['suppressMoveUntil'] = time.time() * 1000 + 300
                    else:
                        pyautogui.middleClick()
                except Exception:
                    pass
        # Remove touch state
        if tid in st['touches']:
            del st['touches'][tid]
        if len(st['touches']) < 3:
            st['threeFingerAccumY'] = 0.0
            st['threeFingerTriggeredUp'] = False
            st['threeFingerTriggeredDown'] = False
        if st.get('doubleTapHoldActive') and len(st['touches']) == 0:
            try:
                pyautogui.mouseUp()
            except Exception:
                pass
            # clear the hold flag after releasing
            st['doubleTapHoldActive'] = False
            st['lastMouseDownTime'] = 0
    except Exception as e:
        print('process_raw_up error', e)


@socketio.on('raw.down')
def on_raw_down_socket(data):
    try:
        sid = request.sid
        process_raw_down(data, sid)
    except Exception as e:
        print('on_raw_down error', e)


@socketio.on('raw.move')
def on_raw_move_socket(data):
    try:
        sid = request.sid
        process_raw_move(data, sid)
    except Exception as e:
        print('on_raw_move error', e)


@socketio.on('raw.up')
def on_raw_up_socket(data):
    try:
        sid = request.sid
        process_raw_up(data, sid)
    except Exception as e:
        print('on_raw_up error', e)


@socketio.on('raw.batch')
def on_raw_batch_socket(events):
    """Efficiently handle a batch of raw events sent in one socket message."""
    try:
        sid = request.sid
        if not isinstance(events, list):
            events = [events]
        for ev in events:
            etype = ev.get('type')
            if etype == 'down':
                process_raw_down(ev, sid)
            elif etype == 'move':
                process_raw_move(ev, sid)
            elif etype == 'up':
                process_raw_up(ev, sid)
    except Exception as e:
        print('on_raw_batch error', e)


# Log socket connections for debugging
@socketio.on('connect')
def on_client_connect():
    try:
        sid = request.sid
        transport = None
        try:
            transport = request.environ.get('wsgi.websocket') is not None and 'websocket' or None
        except Exception:
            transport = None
        print(f"Socket connected: sid={sid}")
    except Exception as e:
        print('connect handler error', e)


@socketio.on('disconnect')
def on_client_disconnect():
    try:
        sid = request.sid
        print(f"Socket disconnected: sid={sid}")
        # Clear any hold state for this client and release mouse if needed
        try:
            st = touch_state.get(sid)
            if st and st.get('doubleTapHoldActive'):
                try:
                    pyautogui.mouseUp()
                except Exception:
                    pass
                st['doubleTapHoldActive'] = False
            if st:
                st['lastMouseDownTime'] = 0
                st['lastMouseDownSid'] = None
                st['doubleTapExpectHold'] = False
                st['pendingDoubleTap'] = False
                st['touches'] = {}
        except Exception:
            pass
    except Exception as e:
        print('disconnect handler error', e)


def force_release_all_holds():
    """Force release any server-tracked mouse holds and clear state flags.

    This helps when a client disconnects unexpectedly or the server
    didn't receive an explicit 'mouseup'. It calls pyautogui.mouseUp()
    (which is no-op if mouse isn't held) and clears the per-connection
    double-tap hold flags so future interactions are clean.
    """
    try:
        # Attempt to release any OS-level mouse hold
        try:
            pyautogui.mouseUp()
        except Exception:
            pass
        # Clear internal flags for all connections
        now_ms = time.time() * 1000
        for sid_key, st in list(touch_state.items()):
            try:
                if st.get('doubleTapHoldActive'):
                    st['doubleTapHoldActive'] = False
                st['lastMouseDownTime'] = 0
                st['lastMouseDownSid'] = None
                st['doubleTapExpectHold'] = False
                st['pendingDoubleTap'] = False
            except Exception:
                pass
    except Exception as e:
        print('force_release_all_holds error', e)


# Watchdog thread to auto-release stale holds in case clients disconnect or
# fail to send mouseup events. Runs every 0.5s and releases holds that
# exceeded DOUBLE_TAP_HOLD_TIMEOUT_MS.
def _hold_watchdog_loop(interval=0.5):
    while True:
        try:
            now_ms = time.time() * 1000
            for sid_key, st in list(touch_state.items()):
                try:
                    if st.get('doubleTapHoldActive') and st.get('lastMouseDownTime', 0):
                        if (now_ms - st.get('lastMouseDownTime', 0)) > DOUBLE_TAP_HOLD_TIMEOUT_MS:
                            try:
                                pyautogui.mouseUp()
                            except Exception:
                                pass
                            st['doubleTapHoldActive'] = False
                            st['lastMouseDownTime'] = 0
                            st['lastMouseDownSid'] = None
                except Exception:
                    pass
        except Exception:
            pass
        try:
            time.sleep(interval)
        except Exception:
            break


# Start watchdog thread as a daemon so it doesn't block shutdown
try:
    watchdog_thread = threading.Thread(target=_hold_watchdog_loop, args=(), daemon=True)
    watchdog_thread.start()
except Exception:
    pass


@app.route('/raw', methods=['POST'])
def raw_http():
    try:
        data = request.json
        events = data if isinstance(data, list) else [data]
        sid_key = _get_sid_for_http()
        for ev in events:
            etype = ev.get('type')
            if etype == 'down':
                process_raw_down(ev, sid_key)
            elif etype == 'move':
                process_raw_move(ev, sid_key)
            elif etype == 'up':
                process_raw_up(ev, sid_key)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


# Handle Task View (Win+Tab) triggered by client three-finger gesture
@socketio.on('taskview')
def on_taskview(data):
    try:
        # On Windows send Win+Tab; pyautogui.hotkey('winleft', 'tab') works
        if platform.system() == 'Windows':
            try:
                _press_key_combo(['winleft'], 'tab')
            except Exception:
                try:
                    _press_key_combo(['winleft'], 'tab')
                except Exception as e:
                    print('taskview fallback failed', e)
        else:
            # Non-Windows: attempt Alt+Tab as a reasonable default
            try:
                _press_key_combo(['alt'], 'tab')
            except Exception:
                pass
    except Exception as e:
        print('on_taskview error', e)


@app.route('/taskview', methods=['POST'])
def taskview():
    try:
        # Mirror socket behavior for HTTP fallback
        if platform.system() == 'Windows':
            try:
                _press_key_combo(['winleft'], 'tab')
            except Exception:
                try:
                    _press_key_combo(['winleft'], 'tab')
                except Exception as e:
                    print('taskview fallback failed', e)
        else:
            try:
                _press_key_combo(['alt'], 'tab')
            except Exception:
                pass
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


# Handle exiting Task View (e.g., three-finger swipe down -> send Esc)
@socketio.on('taskview_exit')
def on_taskview_exit(data):
    try:
        # Send Escape to exit Task View; also ensure modifier keys are released
        try:
            _press_single_key('esc')
        except Exception:
            try:
                _press_single_key('esc')
            except Exception as e:
                print('taskview_exit fallback failed', e)
    except Exception as e:
        print('on_taskview_exit error', e)


@app.route('/taskview_exit', methods=['POST'])
def taskview_exit():
    try:
        try:
            _press_single_key('esc')
        except Exception:
            try:
                _press_single_key('esc')
            except Exception as e:
                print('taskview_exit fallback failed', e)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


# Mouse down/up handlers for double-tap-and-hold
@socketio.on('mousedown')
def on_mousedown(data):
    try:
        pyautogui.mouseDown()
        # mark server-side hold state for this socket so we can auto-release if needed
        try:
            sid = request.sid
            st = touch_state.setdefault(sid, {'touches': {}, 'threeFingerAccumY': 0.0, 'threeFingerTriggeredUp': False, 'threeFingerTriggeredDown': False, 'doubleTapHoldActive': False, 'suppressMoveUntil': 0, 'lastMouseDownTime': 0, 'lastMouseDownSid': None})
            st['doubleTapHoldActive'] = True
            st['lastMouseDownTime'] = time.time() * 1000
            st['lastMouseDownSid'] = sid
        except Exception:
            pass
    except Exception as e:
        print('on_mousedown error', e)


@socketio.on('mouseup')
def on_mouseup(data):
    try:
        pyautogui.mouseUp()
        try:
            sid = request.sid
            st = touch_state.setdefault(sid, {'touches': {}, 'threeFingerAccumY': 0.0, 'threeFingerTriggeredUp': False, 'threeFingerTriggeredDown': False, 'doubleTapHoldActive': False, 'suppressMoveUntil': 0, 'lastMouseDownTime': 0, 'lastMouseDownSid': None})
            st['doubleTapHoldActive'] = False
            st['lastMouseDownTime'] = 0
            st['lastMouseDownSid'] = None
        except Exception:
            pass
    except Exception as e:
        print('on_mouseup error', e)


# Receive key events via socket
@socketio.on('key')
def on_key(data):
    try:
        # data expected: { type: 'char'|'key', value: 'a' } or for key: {type:'key', key:'Enter'...}
        if not data:
            return
        if data.get('type') == 'char':
            ch = data.get('value')
            if ch:
                try:
                    pyautogui.typewrite(ch)
                except Exception:
                    pass
        elif data.get('type') == 'key':
            k = data.get('key')
            # Map some common special keys
            special_map = {
                'Enter': 'enter',
                'Backspace': 'backspace',
                'Tab': 'tab',
                'Escape': 'esc',
                'ArrowLeft': 'left',
                'ArrowRight': 'right',
                'ArrowUp': 'up',
                'ArrowDown': 'down'
            }
            mapped = special_map.get(k)
            try:
                if mapped:
                    pyautogui.press(mapped)
                else:
                    # Fallback: send the raw key string if pyautogui supports it
                    if k and len(k) == 1:
                        pyautogui.typewrite(k)
            except Exception:
                pass
    except Exception as e:
        print('on_key error', e)


@app.route('/key', methods=['POST'])
def http_key():
    try:
        data = request.json or {}
        # Mirror socket handler behavior
        if data.get('type') == 'char':
            ch = data.get('value')
            if ch:
                try:
                    pyautogui.typewrite(ch)
                except Exception:
                    pass
        elif data.get('type') == 'key':
            k = data.get('key')
            special_map = {
                'Enter': 'enter',
                'Backspace': 'backspace',
                'Tab': 'tab',
                'Escape': 'esc',
                'ArrowLeft': 'left',
                'ArrowRight': 'right',
                'ArrowUp': 'up',
                'ArrowDown': 'down'
            }
            mapped = special_map.get(k)
            try:
                if mapped:
                    pyautogui.press(mapped)
                else:
                    if k and len(k) == 1:
                        pyautogui.typewrite(k)
            except Exception:
                pass
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/mousedown', methods=['POST'])
def http_mousedown():
    try:
        pyautogui.mouseDown()
        try:
            sid_key = _get_sid_for_http()
            st = touch_state.setdefault(sid_key, {'touches': {}, 'threeFingerAccumY': 0.0, 'threeFingerTriggeredUp': False, 'threeFingerTriggeredDown': False, 'doubleTapHoldActive': False, 'suppressMoveUntil': 0, 'lastMouseDownTime': 0, 'lastMouseDownSid': None})
            st['doubleTapHoldActive'] = True
            st['lastMouseDownTime'] = time.time() * 1000
            st['lastMouseDownSid'] = sid_key
        except Exception:
            pass
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/mouseup', methods=['POST'])
def http_mouseup():
    try:
        pyautogui.mouseUp()
        try:
            sid_key = _get_sid_for_http()
            st = touch_state.setdefault(sid_key, {'touches': {}, 'threeFingerAccumY': 0.0, 'threeFingerTriggeredUp': False, 'threeFingerTriggeredDown': False, 'doubleTapHoldActive': False, 'suppressMoveUntil': 0, 'lastMouseDownTime': 0, 'lastMouseDownSid': None})
            st['doubleTapHoldActive'] = False
            st['lastMouseDownTime'] = 0
            st['lastMouseDownSid'] = None
        except Exception:
            pass
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/drag', methods=['POST'])
def drag_mouse():
    try:
        data = request.json
        start_x = float(data.get('startX', 0))
        start_y = float(data.get('startY', 0))
        end_x = float(data.get('endX', 0))
        end_y = float(data.get('endY', 0))
        
        # Get current mouse position
        current_x, current_y = pyautogui.position()
        
        # Client should send already-scaled coordinates (or deltas). Apply raw drag delta.
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=0.1)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # Get the local IP address to display to user
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"Starting trackpad server...")
    print(f"Access from your phone at: http://{local_ip}:51273")
    print(f"Or access locally at: http://localhost:51273")
    print(f"Virtual screen detected: left={virtual_left}, top={virtual_top}, size={screen_width}x{screen_height}")
    
    # Run with SocketIO so WebSocket support is enabled. If eventlet/gevent isn't installed
    # this will still work with the default development server for HTTP fallback.
    try:
        socketio.run(app, host='0.0.0.0', port=51273, debug=True, log_output=False)
    except Exception:
        # request_handler can't be passed through here reliably, rely on the monkey-patch above
        app.run(host='0.0.0.0', port=51273, debug=True)


@app.route('/versions')
def versions():
    """Return versions of socket-related libraries installed on the server to help debug client/server protocol compatibility."""
    try:
        import socketio as pysocketio
        import engineio as pyengineio
        import flask_socketio as flasksocketio
        return jsonify({
            'python-socketio': getattr(pysocketio, '__version__', 'unknown'),
            'python-engineio': getattr(pyengineio, '__version__', 'unknown'),
            'flask-socketio': getattr(flasksocketio, '__version__', 'unknown')
        })
    except Exception as e:
        return jsonify({'error': str(e)})