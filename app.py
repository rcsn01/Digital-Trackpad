from flask import Flask, render_template, request, jsonify
import pyautogui
import threading
import time
import math

# WebSocket support
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

# Configure pyautogui
pyautogui.FAILSAFE = True  # Move mouse to corner to stop
pyautogui.PAUSE = 0.001   # Small pause between commands

# Server-side multiplier for incoming fractional scroll values. Increase if scroll feels weak.
SCROLL_MULTIPLIER = 0.1
# Toggle to print incoming scroll payloads (for troubleshooting); set False to silence
SCROLL_DEBUG = False
# If accumulated fractional scroll (after multiplying) exceeds this small value,
# force one wheel step in the appropriate direction. Helps small gestures move the page.
MIN_SCROLL_FRAC_TO_STEP = 0.05

# Get screen size for scaling
screen_width, screen_height = pyautogui.size()

# Media control mappings
MEDIA_CONTROLS = {
    'play_pause': 'space',
    'volume_up': 'volumeup',
    'volume_down': 'volumedown',
    'mute': 'volumemute',
    'next_track': 'nexttrack',
    'prev_track': 'prevtrack',
    'stop': 'stop'
}

# Presentation control mappings
PRESENTATION_CONTROLS = {
    'next_slide': 'right',
    'prev_slide': 'left',
    'start_slideshow': 'f5',
    'exit_slideshow': 'esc',
    'black_screen': 'b',
    'white_screen': 'w'
}

# Application shortcuts (customizable)
APP_SHORTCUTS = {
    'chrome': ['win', '1'],
    'vscode': ['win', '2'],
    'explorer': ['win', 'e'],
    'notepad': ['win', 'r'],  # Will type notepad and enter
    'calculator': ['win', 'r'],  # Will type calc and enter
    'task_manager': ['ctrl', 'shift', 'esc']
}

# Accumulators to buffer fractional scrolls so very small client deltas still result in scrolling
scroll_accum_x = 0.0
scroll_accum_y = 0.0
scroll_lock = threading.Lock()

@app.route('/')
def index():
    """Main page - renders the trackpad interface"""
    return render_template('index.html')

@app.route('/move', methods=['POST'])
def move_mouse():
    """Move mouse cursor to specified coordinates"""
    try:
        data = request.json
        delta_x = float(data.get('deltaX', 0))
        delta_y = float(data.get('deltaY', 0))
        
        # Get current mouse position
        current_x, current_y = pyautogui.position()
        
        # Client-side should apply sensitivity. Server applies raw deltas.
        new_x = current_x + delta_x
        new_y = current_y + delta_y
        
        # Ensure mouse stays within screen bounds
        new_x = max(0, min(screen_width - 1, new_x))
        new_y = max(0, min(screen_height - 1, new_y))
        
        # Move mouse
        pyautogui.moveTo(new_x, new_y)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/click', methods=['POST'])
def click_mouse():
    """Perform mouse click actions"""
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
    """Handle mouse scroll wheel input with fractional accumulation"""
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
                    try:
                        # Some PyAutoGUI versions expose hscroll
                        pyautogui.hscroll(scroll_amount_x)
                    except Exception:
                        # Fallback: use shift+vertical scroll to emulate horizontal scroll
                        if scroll_amount_x > 0:
                            pyautogui.keyDown('shift')
                            pyautogui.scroll(int(abs(scroll_amount_x)))
                            pyautogui.keyUp('shift')
                        else:
                            pyautogui.keyDown('shift')
                            pyautogui.scroll(-int(abs(scroll_amount_x)))
                            pyautogui.keyUp('shift')
                    scroll_accum_x -= scroll_amount_x
                else:
                    if abs(scroll_accum_x) >= MIN_SCROLL_FRAC_TO_STEP:
                        step_x = int(math.copysign(1, scroll_accum_x))
                        try:
                            pyautogui.hscroll(step_x)
                        except Exception:
                            if step_x > 0:
                                pyautogui.keyDown('shift')
                                pyautogui.scroll(int(abs(step_x)))
                                pyautogui.keyUp('shift')
                            else:
                                pyautogui.keyDown('shift')
                                pyautogui.scroll(-int(abs(step_x)))
                                pyautogui.keyUp('shift')
                        scroll_accum_x -= step_x
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/media', methods=['POST'])
def media_control():
    """Media control functionality - play/pause, volume control, etc."""
    try:
        data = request.json
        action = data.get('action', '')
        
        if action in MEDIA_CONTROLS:
            key = MEDIA_CONTROLS[action]
            if action == 'play_pause':
                # Special handling for play/pause, depends on current application
                pyautogui.press(key)
            else:
                pyautogui.press(key)
            return jsonify({'status': 'success', 'action': action})
        else:
            return jsonify({'status': 'error', 'message': f'Unknown media action: {action}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/presentation', methods=['POST'])
def presentation_control():
    """Presentation control functionality - slide navigation, start presentation, etc."""
    try:
        data = request.json
        action = data.get('action', '')
        
        if action in PRESENTATION_CONTROLS:
            key = PRESENTATION_CONTROLS[action]
            pyautogui.press(key)
            return jsonify({'status': 'success', 'action': action})
        else:
            return jsonify({'status': 'error', 'message': f'Unknown presentation action: {action}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/app', methods=['POST'])
def app_control():
    """Application control - switch and launch common applications"""
    try:
        data = request.json
        app_name = data.get('app', '')
        
        if app_name in APP_SHORTCUTS:
            keys = APP_SHORTCUTS[app_name]
            if app_name == 'calculator':
                # Special handling for calculator - Win+R then type calc
                pyautogui.hotkey('win', 'r')
                time.sleep(0.5)
                pyautogui.typewrite('calc')
                pyautogui.press('enter')
            elif app_name == 'notepad':
                # Special handling for notepad - Win+R then type notepad
                pyautogui.hotkey('win', 'r')
                time.sleep(0.5)
                pyautogui.typewrite('notepad')
                pyautogui.press('enter')
            else:
                pyautogui.hotkey(*keys)
            return jsonify({'status': 'success', 'app': app_name})
        else:
            return jsonify({'status': 'error', 'message': f'Unknown app: {app_name}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/keyboard', methods=['POST'])
def keyboard_control():
    """Keyboard shortcut control - custom key combinations"""
    try:
        data = request.json
        keys = data.get('keys', [])
        
        if keys:
            pyautogui.hotkey(*keys)
            return jsonify({'status': 'success', 'keys': keys})
        else:
            return jsonify({'status': 'error', 'message': 'No keys provided'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/system', methods=['POST'])
def system_control():
    """System control - sleep, shutdown, restart, etc."""
    try:
        data = request.json
        action = data.get('action', '')
        
        if action == 'sleep':
            pyautogui.hotkey('win', 'x')
            time.sleep(0.5)
            pyautogui.press('u')
            time.sleep(0.5)
            pyautogui.press('s')
        elif action == 'shutdown':
            pyautogui.hotkey('alt', 'f4')
            time.sleep(0.5)
            pyautogui.press('enter')
        elif action == 'restart':
            pyautogui.hotkey('win', 'x')
            time.sleep(0.5)
            pyautogui.press('u')
            time.sleep(0.5)
            pyautogui.press('r')
        else:
            return jsonify({'status': 'error', 'message': f'Unknown system action: {action}'})
            
        return jsonify({'status': 'success', 'action': action})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# SocketIO handlers - lower-latency path (client will emit these when connected)
@socketio.on('move')
def on_move(data):
    """WebSocket mouse movement handler"""
    try:
        dx = float(data.get('deltaX', 0))
        dy = float(data.get('deltaY', 0))
        current_x, current_y = pyautogui.position()
        new_x = current_x + dx
        new_y = current_y + dy
        new_x = max(0, min(screen_width - 1, new_x))
        new_y = max(0, min(screen_height - 1, new_y))
        pyautogui.moveTo(new_x, new_y)
    except Exception as e:
        print('on_move error', e)

@socketio.on('click')
def on_click(data):
    """WebSocket mouse click handler"""
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
    """WebSocket mouse scroll handler with fractional accumulation"""
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

        # Accumulate horizontal fractional scrolls
        if scroll_x != 0:
            with scroll_lock:
                global scroll_accum_x
                scroll_accum_x += scroll_x * SCROLL_MULTIPLIER
                scroll_amount_x = int(scroll_accum_x)
                if scroll_amount_x != 0:
                    try:
                        # Some PyAutoGUI versions expose hscroll
                        pyautogui.hscroll(scroll_amount_x)
                    except Exception:
                        # Fallback: use shift+vertical scroll to emulate horizontal scroll
                        if scroll_amount_x > 0:
                            pyautogui.keyDown('shift')
                            pyautogui.scroll(int(abs(scroll_amount_x)))
                            pyautogui.keyUp('shift')
                        else:
                            pyautogui.keyDown('shift')
                            pyautogui.scroll(-int(abs(scroll_amount_x)))
                            pyautogui.keyUp('shift')
                    scroll_accum_x -= scroll_amount_x
                else:
                    if abs(scroll_accum_x) >= MIN_SCROLL_FRAC_TO_STEP:
                        step_x = int(math.copysign(1, scroll_accum_x))
                        try:
                            pyautogui.hscroll(step_x)
                        except Exception:
                            if step_x > 0:
                                pyautogui.keyDown('shift')
                                pyautogui.scroll(int(abs(step_x)))
                                pyautogui.keyUp('shift')
                            else:
                                pyautogui.keyDown('shift')
                                pyautogui.scroll(-int(abs(step_x)))
                                pyautogui.keyUp('shift')
                        scroll_accum_x -= step_x
    except Exception as e:
        print('on_scroll error', e)

# SocketIO handlers for universal remote
@socketio.on('media')
def on_media(data):
    """WebSocket media control handler"""
    try:
        action = data.get('action', '')
        if action in MEDIA_CONTROLS:
            key = MEDIA_CONTROLS[action]
            pyautogui.press(key)
            print(f"[Media] {action} -> {key}")
        else:
            print(f"[Media] Unknown action: {action}")
    except Exception as e:
        print(f'[Media] Error: {e}')

@socketio.on('presentation')
def on_presentation(data):
    """WebSocket presentation control handler"""
    try:
        action = data.get('action', '')
        if action in PRESENTATION_CONTROLS:
            key = PRESENTATION_CONTROLS[action]
            pyautogui.press(key)
            print(f"[Presentation] {action} -> {key}")
        else:
            print(f"[Presentation] Unknown action: {action}")
    except Exception as e:
        print(f'[Presentation] Error: {e}')

@socketio.on('app')
def on_app(data):
    """WebSocket application control handler"""
    try:
        app_name = data.get('app', '')
        if app_name in APP_SHORTCUTS:
            if app_name == 'calculator':
                pyautogui.hotkey('win', 'r')
                time.sleep(0.5)
                pyautogui.typewrite('calc')
                pyautogui.press('enter')
                print(f"[App] Opened calculator")
            elif app_name == 'notepad':
                pyautogui.hotkey('win', 'r')
                time.sleep(0.5)
                pyautogui.typewrite('notepad')
                pyautogui.press('enter')
                print(f"[App] Opened notepad")
            else:
                keys = APP_SHORTCUTS[app_name]
                pyautogui.hotkey(*keys)
                print(f"[App] {app_name} -> {keys}")
        else:
            print(f"[App] Unknown app: {app_name}")
    except Exception as e:
        print(f'[App] Error: {e}')

@socketio.on('keyboard')
def on_keyboard(data):
    """WebSocket keyboard shortcut handler"""
    try:
        keys = data.get('keys', [])
        if keys:
            pyautogui.hotkey(*keys)
            print(f"[Keyboard] {keys}")
        else:
            print("[Keyboard] No keys provided")
    except Exception as e:
        print(f'[Keyboard] Error: {e}')

@socketio.on('system')
def on_system(data):
    """WebSocket system control handler"""
    try:
        action = data.get('action', '')
        if action == 'sleep':
            pyautogui.hotkey('win', 'x')
            time.sleep(0.5)
            pyautogui.press('u')
            time.sleep(0.5)
            pyautogui.press('s')
            print("[System] Sleep mode activated")
        elif action == 'shutdown':
            pyautogui.hotkey('alt', 'f4')
            time.sleep(0.5)
            pyautogui.press('enter')
            print("[System] Shutdown initiated")
        elif action == 'restart':
            pyautogui.hotkey('win', 'x')
            time.sleep(0.5)
            pyautogui.press('u')
            time.sleep(0.5)
            pyautogui.press('r')
            print("[System] Restart initiated")
        else:
            print(f"[System] Unknown action: {action}")
    except Exception as e:
        print(f'[System] Error: {e}')

@app.route('/drag', methods=['POST'])
def drag_mouse():
    """Perform mouse drag operation"""
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
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Universal PC Remote Server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on (default: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()
    
    # Get the local IP address to display to user
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"Starting trackpad server...")
    print(f"Access from your phone at: http://{local_ip}:{args.port}")
    print(f"Or access locally at: http://localhost:{args.port}")
    print(f"Screen size detected: {screen_width}x{screen_height}")
    
    # Run with SocketIO so WebSocket support is enabled. If eventlet/gevent isn't installed
    # this will still work with the default development server for HTTP fallback.
    try:
        socketio.run(app, host=args.host, port=args.port, debug=True)
    except Exception:
        app.run(host=args.host, port=args.port, debug=True)