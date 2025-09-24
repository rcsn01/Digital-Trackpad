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

# Accumulators to buffer fractional scrolls so very small client deltas still result in scrolling
scroll_accum_x = 0.0
scroll_accum_y = 0.0
scroll_lock = threading.Lock()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move', methods=['POST'])
def move_mouse():
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


# SocketIO handlers - lower-latency path (client will emit these when connected)
@socketio.on('move')
def on_move(data):
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
    print(f"Access from your phone at: http://{local_ip}:5000")
    print(f"Or access locally at: http://localhost:5000")
    print(f"Screen size detected: {screen_width}x{screen_height}")
    
    # Run with SocketIO so WebSocket support is enabled. If eventlet/gevent isn't installed
    # this will still work with the default development server for HTTP fallback.
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except Exception:
        app.run(host='0.0.0.0', port=5000, debug=True)