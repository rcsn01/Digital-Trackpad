// 萬能PC遙控器 - 多模式控制客戶端
// 功能：
// - 觸控板模式：滑鼠移動、點擊、滾動
// - 媒體控制模式：音量、播放控制
// - 簡報控制模式：簡報導航
// - 應用程式模式：快速啟動應用程式

class UniversalRemote {
    constructor() {
        this.currentMode = 'trackpad';
        this.socket = null;
        this.pendingRequests = new Set();
        
        this.initSocket();
        this.initModeSwitcher();
        this.initTrackpad();
        this.initRemoteControls();
    }
    
    initSocket() {
        try {
            if (typeof io === 'function') {
                this.socket = io();
                this.socket.on('connect', () => {
                    console.log('Socket連接成功');
                });
                this.socket.on('disconnect', () => {
                    console.log('Socket連接斷開');
                });
            }
        } catch (e) {
            this.socket = null;
        }
    }
    
    initModeSwitcher() {
        const modeButtons = document.querySelectorAll('.mode-btn');
        const modeContainers = document.querySelectorAll('.mode-container');
        
        modeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                
                // 更新按鈕狀態
                modeButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // 更新模式容器
                modeContainers.forEach(container => {
                    container.classList.remove('active');
                });
                document.getElementById(`${mode}-mode`).classList.add('active');
                
                this.currentMode = mode;
                console.log(`切換到${this.getModeName(mode)}模式`);
            });
        });
    }
    
    getModeName(mode) {
        const names = {
            'trackpad': '觸控板',
            'media': '媒體控制',
            'presentation': '簡報控制',
            'apps': '應用程式'
        };
        return names[mode] || mode;
    }
    
    initTrackpad() {
        this.trackpad = new PhoneTrackpad(this.socket);
        
        // 綁定控制按鈕事件
        this.bindControlButtons();
    }
    
    bindControlButtons() {
        // 媒體控制
        document.querySelectorAll('[data-media]').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.media;
                this.sendMediaCommand(action);
                this.addButtonFeedback(btn);
            });
        });
        
        // 簡報控制
        document.querySelectorAll('[data-presentation]').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.presentation;
                this.sendPresentationCommand(action);
                this.addButtonFeedback(btn);
            });
        });
        
        // 應用程式控制
        document.querySelectorAll('[data-app]').forEach(btn => {
            btn.addEventListener('click', () => {
                const app = btn.dataset.app;
                this.sendAppCommand(app);
                this.addButtonFeedback(btn);
            });
        });
        
        // 鍵盤快捷鍵
        document.querySelectorAll('[data-keyboard]').forEach(btn => {
            btn.addEventListener('click', () => {
                const key = btn.dataset.keyboard;
                this.sendKeyboardCommand(key);
                this.addButtonFeedback(btn);
            });
        });
        
        // 系統控制
        document.querySelectorAll('[data-system]').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.system;
                this.sendSystemCommand(action);
                this.addButtonFeedback(btn);
            });
        });
    }
    
    addButtonFeedback(button) {
        button.classList.add('active');
        setTimeout(() => button.classList.remove('active'), 150);
    }
    
    initRemoteControls() {
        // 媒體控制
        const mediaButtons = document.querySelectorAll('#media-mode .control-btn');
        mediaButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.sendMediaControl(action);
            });
        });
        
        // 簡報控制
        const presentationButtons = document.querySelectorAll('#presentation-mode .control-btn');
        presentationButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.sendPresentationControl(action);
            });
        });
        
        // 應用程式控制
        const appButtons = document.querySelectorAll('#apps-mode .control-btn');
        appButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.sendAppControl(action);
            });
        });
    }
    
    sendMediaControl(action) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('media', { action });
            return;
        }
        
        this.sendHttpRequest('/media', { action });
    }
    
    sendPresentationControl(action) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('presentation', { action });
            return;
        }
        
        this.sendHttpRequest('/presentation', { action });
    }
    
    sendAppControl(app) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('app', { app });
            return;
        }
        
        this.sendHttpRequest('/app', { app });
    }
    
    sendSystemControl(action) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('system', { action });
            return;
        }
        
        this.sendHttpRequest('/system', { action });
    }
    
    sendKeyboardControl(keys) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('keyboard', { keys });
            return;
        }
        
        this.sendHttpRequest('/keyboard', { keys });
    }
    
    sendHttpRequest(endpoint, data) {
        const requestId = `${endpoint}-${Date.now()}-${Math.random()}`;
        if (this.pendingRequests.size > 10) return;
        
        this.pendingRequests.add(requestId);
        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).catch(() => {}).finally(() => {
            this.pendingRequests.delete(requestId);
        });
    }
}

// 觸控板類別
class PhoneTrackpad {
    constructor(socket) {
        this.trackpad = document.getElementById('trackpad');
        this.socket = socket;
        this.touches = new Map();
        this.lastMove = 0;
        this.moveThrottle = 5;
        this.sensitivity = 6;
        this.moveSendThreshold = 0.35;
        this.scrollSensitivity = 30;
        this.scrollAccumX = 0;
        this.scrollAccumY = 0;
        this.scrollBatchThreshold = 0.02;
        
        this.debug = false;
        this.tapThreshold = 6;
        this.tapTimeout = 200;
        this.pendingRequests = new Set();
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        this.trackpad.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        this.trackpad.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        this.trackpad.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        this.trackpad.addEventListener('touchcancel', this.handleTouchEnd.bind(this), { passive: false });
        
        this.trackpad.addEventListener('contextmenu', e => e.preventDefault());
        this.trackpad.addEventListener('selectstart', e => e.preventDefault());
        
        if ('wakeLock' in navigator) {
            navigator.wakeLock.request('screen').catch(() => {});
        }
    }
    
    handleTouchStart(e) {
        e.preventDefault();
        
        for (let touch of e.changedTouches) {
            const touchData = {
                id: touch.identifier,
                startX: touch.pageX,
                startY: touch.pageY,
                lastX: touch.pageX,
                lastY: touch.pageY,
                startTime: Date.now(),
                hasMoved: false,
                totalDistance: 0
            };
            
            this.touches.set(touch.identifier, touchData);
            this.showTouchFeedback(touch.pageX, touch.pageY);
        }
    }
    
    handleTouchMove(e) {
        e.preventDefault();
        
        const now = Date.now();
        if (now - this.lastMove < this.moveThrottle) {
            return; // Throttle move events
        }
        this.lastMove = now;
        
        // Handle single finger movement (mouse movement)
        if (e.touches.length === 1) {
            this.handleMouseMovement(e.touches[0]);
        }
        // Handle two finger movement (scrolling)
        else if (e.touches.length === 2) {
            this.handleScrollGesture(e.touches[0], e.touches[1]);
        }
        
        // Update touch tracking data
        for (let touch of e.changedTouches) {
            const touchData = this.touches.get(touch.identifier);
            if (touchData) {
                const deltaX = touch.pageX - touchData.lastX;
                const deltaY = touch.pageY - touchData.lastY;
                const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
                
                touchData.lastX = touch.pageX;
                touchData.lastY = touch.pageY;
                touchData.totalDistance += distance;
                
                if (touchData.totalDistance > this.tapThreshold) {
                    touchData.hasMoved = true;
                }
            }
        }
    }
    
    handleTouchEnd(e) {
        e.preventDefault();
        
        for (let touch of e.changedTouches) {
            const touchData = this.touches.get(touch.identifier);
            if (touchData) {
                const duration = Date.now() - touchData.startTime;
                
                // Check if this was a tap gesture
                if (!touchData.hasMoved && duration < this.tapTimeout) {
                    this.handleTap(touch, e.touches.length + e.changedTouches.length - 1);
                }
                
                this.touches.delete(touch.identifier);
            }
        }
        
        // If two-finger gesture ended (touch count < 2), flush any residual scroll and reset accumulators
        if (e.touches.length < 2) {
            if (Math.abs(this.scrollAccumY) > 0.02) {
                this.sendScrollCommand(0, this.scrollAccumY);
            }
            this.scrollAccumX = 0;
            this.scrollAccumY = 0;
        }
    }
    
    handleMouseMovement(touch) {
        const touchData = this.touches.get(touch.identifier);
        if (!touchData) return;
        
        const deltaX = touch.pageX - touchData.lastX;
        const deltaY = touch.pageY - touchData.lastY;
        
        // Apply sensitivity scaling
        const scaledDeltaX = deltaX * this.sensitivity;
        const scaledDeltaY = deltaY * this.sensitivity;
        
        // Only send move command if there's meaningful movement (uses configurable threshold)
        if (Math.abs(scaledDeltaX) > this.moveSendThreshold || Math.abs(scaledDeltaY) > this.moveSendThreshold) {
            this.sendMoveCommand(scaledDeltaX, scaledDeltaY);
        }
    }

    // Allow runtime tuning from console
    setMoveSensitivity(mouseSensitivity) {
        this.sensitivity = Math.max(0.1, Math.min(10, mouseSensitivity));
    }

    setMoveSendThreshold(px) {
        this.moveSendThreshold = Math.max(0.01, px);
    }

    setTapThreshold(px) {
        this.tapThreshold = Math.max(0, px);
    }
    
    sendMoveCommand(deltaX, deltaY) {
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('move', { deltaX, deltaY });
                if (this.debug) console.debug('socket emit move', { deltaX, deltaY });
            } catch (e) {
                // fall through to HTTP fallback
            }
            return;
        }

        const requestId = `move-${Date.now()}-${Math.random()}`;
        if (this.pendingRequests.size > 5) return;
        this.pendingRequests.add(requestId);
        fetch('/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deltaX, deltaY })
        }).catch(() => {}).finally(() => {
            if (this.debug) console.debug('POST /move', { deltaX, deltaY });
            this.pendingRequests.delete(requestId);
        });
    }
    
    handleTap(touch, totalTouches) {
        // Determine click type based on number of fingers
        let button = 'left';
        
        if (totalTouches === 1) {
            button = 'left'; // Single finger tap = left click
        } else if (totalTouches === 2) {
            button = 'right'; // Two finger tap = right click
        } else if (totalTouches === 3) {
            button = 'middle'; // Three finger tap = middle click
        }
        
        this.sendClickCommand(button);
    }
    
    sendClickCommand(button) {
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('click', { button });
                if (this.debug) console.debug('socket emit click', { button });
            } catch (e) {}
            return;
        }

        const requestId = `click-${Date.now()}-${Math.random()}`;
        this.pendingRequests.add(requestId);
        fetch('/click', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ button }) })
            .catch(() => {})
            .finally(() => { this.pendingRequests.delete(requestId); });
    }
    
    handleScrollGesture(touch1, touch2) {
        const touch1Data = this.touches.get(touch1.identifier);
        const touch2Data = this.touches.get(touch2.identifier);
        
        if (!touch1Data || !touch2Data) return;
        
        // Calculate average movement of both fingers
        const avgDeltaX = ((touch1.pageX - touch1Data.lastX) + (touch2.pageX - touch2Data.lastX)) / 2;
        const avgDeltaY = ((touch1.pageY - touch1Data.lastY) + (touch2.pageY - touch2Data.lastY)) / 2;
        
        // Apply scroll sensitivity (vertical-only)
        const scrollY = -avgDeltaY * this.scrollSensitivity; // Invert Y for natural scrolling
        
        // Accumulate vertical only until we pass a batch threshold
        this.scrollAccumY += scrollY;
        
    const shouldFlushY = Math.abs(this.scrollAccumY) >= this.scrollBatchThreshold;
        
        if (shouldFlushY) {
            const sendY = this.scrollAccumY;
            // Reset accumulator before sending to avoid race on rapid events
            this.scrollAccumY = 0;
            if (this.debug) console.debug('Scroll flush (vertical only)', { sendY });
            this.sendScrollCommand(0, sendY);
        }
    }
    
    sendScrollCommand(scrollX, scrollY) {
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('scroll', { scrollX, scrollY });
                if (this.debug) console.debug('socket emit scroll', { scrollX, scrollY });
            } catch (e) {
                // fall through to HTTP fallback
            }
            return;
        }

        const requestId = `scroll-${Date.now()}-${Math.random()}`;
        if (this.pendingRequests.size > 5) return;
        this.pendingRequests.add(requestId);
        fetch('/scroll', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scrollX, scrollY }) })
            .catch(() => {})
            .finally(() => { if (this.debug) console.debug('POST /scroll', { scrollX, scrollY }); this.pendingRequests.delete(requestId); });
    }

    sendMediaCommand(action) {
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('media', { action });
                if (this.debug) console.debug('socket emit media', { action });
            } catch (e) {
                // fall through to HTTP fallback
            }
            return;
        }

        const requestId = `media-${Date.now()}-${Math.random()}`;
        if (this.pendingRequests.size > 5) return;
        this.pendingRequests.add(requestId);
        fetch('/media', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        }).catch(() => {}).finally(() => {
            if (this.debug) console.debug('POST /media', { action });
            this.pendingRequests.delete(requestId);
        });
    }

    sendPresentationCommand(action) {
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('presentation', { action });
                if (this.debug) console.debug('socket emit presentation', { action });
            } catch (e) {
                // fall through to HTTP fallback
            }
            return;
        }

        const requestId = `presentation-${Date.now()}-${Math.random()}`;
        if (this.pendingRequests.size > 5) return;
        this.pendingRequests.add(requestId);
        fetch('/presentation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        }).catch(() => {}).finally(() => {
            if (this.debug) console.debug('POST /presentation', { action });
            this.pendingRequests.delete(requestId);
        });
    }

    sendAppCommand(app) {
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('app', { app });
                if (this.debug) console.debug('socket emit app', { app });
            } catch (e) {
                // fall through to HTTP fallback
            }
            return;
        }

        const requestId = `app-${Date.now()}-${Math.random()}`;
        if (this.pendingRequests.size > 5) return;
        this.pendingRequests.add(requestId);
        fetch('/app', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ app })
        }).catch(() => {}).finally(() => {
            if (this.debug) console.debug('POST /app', { app });
            this.pendingRequests.delete(requestId);
        });
    }

    sendKeyboardCommand(key) {
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('keyboard', { key });
                if (this.debug) console.debug('socket emit keyboard', { key });
            } catch (e) {
                // fall through to HTTP fallback
            }
            return;
        }

        const requestId = `keyboard-${Date.now()}-${Math.random()}`;
        if (this.pendingRequests.size > 5) return;
        this.pendingRequests.add(requestId);
        fetch('/keyboard', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key })
        }).catch(() => {}).finally(() => {
            if (this.debug) console.debug('POST /keyboard', { key });
            this.pendingRequests.delete(requestId);
        });
    }

    sendSystemCommand(action) {
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('system', { action });
                if (this.debug) console.debug('socket emit system', { action });
            } catch (e) {
                // fall through to HTTP fallback
            }
            return;
        }

        const requestId = `system-${Date.now()}-${Math.random()}`;
        if (this.pendingRequests.size > 5) return;
        this.pendingRequests.add(requestId);
        fetch('/system', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        }).catch(() => {}).finally(() => {
            if (this.debug) console.debug('POST /system', { action });
            this.pendingRequests.delete(requestId);
        });
    }

    // Runtime tuning for scroll behavior
    setScrollSensitivity(val) {
        this.scrollSensitivity = Math.max(0.001, Math.min(10, val));
    }

    setScrollBatchThreshold(val) {
        this.scrollBatchThreshold = Math.max(0.0001, val);
    }
    
    showTouchFeedback(x, y) {
        const feedback = document.createElement('div');
        feedback.className = 'touch-feedback';
        feedback.style.left = x + 'px';
        feedback.style.top = y + 'px';
        
        this.trackpad.appendChild(feedback);
        
        // Remove the feedback element after animation completes
        setTimeout(() => {
            if (feedback.parentNode) {
                feedback.parentNode.removeChild(feedback);
            }
        }, 300);
    }
    
    // Add method to handle connection status and provide user feedback
    checkConnection() {
        const requestId = `health-${Date.now()}`;
        this.pendingRequests.add(requestId);
        
        return fetch('/move', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ deltaX: 0, deltaY: 0 })
        })
        .then(() => {
            // Connection is working
            document.body.style.backgroundColor = '#111';
            return true;
        })
        .catch(() => {
            // Connection failed - show visual indicator
            document.body.style.backgroundColor = '#330000';
            return false;
        })
        .finally(() => {
            this.pendingRequests.delete(requestId);
        });
    }
    
    // Method to adjust sensitivity (could be called from UI controls if added)
    setSensitivity(mouseSensitivity, scrollSensitivity) {
        this.sensitivity = Math.max(0.1, Math.min(10, mouseSensitivity));
        this.scrollSensitivity = Math.max(0.001, Math.min(1, scrollSensitivity));
    }
    
    // Cleanup method
    destroy() {
        this.trackpad.removeEventListener('touchstart', this.handleTouchStart);
        this.trackpad.removeEventListener('touchmove', this.handleTouchMove);
        this.trackpad.removeEventListener('touchend', this.handleTouchEnd);
        this.trackpad.removeEventListener('touchcancel', this.handleTouchEnd);
        this.touches.clear();
        this.pendingRequests.clear();
    }
}

window.addEventListener('DOMContentLoaded', () => {
    const remote = new UniversalRemote();
    // 暴露給控制台調試
    window.universalRemote = remote;
});

