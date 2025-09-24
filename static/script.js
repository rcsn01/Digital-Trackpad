// PhoneTrackpad - minimal, robust client
// Responsibilities:
// - Capture touch events and convert to move/scroll/click
// - Prevent clicks after any movement (movement wins)
// - Use fire-and-forget network calls to reduce perceived latency

class PhoneTrackpad {
    constructor() {
        this.trackpad = document.getElementById('trackpad');
        this.touches = new Map(); // Track multiple touches by identifier
        this.lastMove = 0; // Timestamp of last move to throttle
    this.moveThrottle = 5; // Minimum ms between move events (lower for more responsiveness)
    this.sensitivity = 6; // Mouse movement sensitivity multiplier
    // Threshold (in pixels after sensitivity) to consider movement worth sending
    this.moveSendThreshold = 0.35;
    this.scrollSensitivity = 30; // Scroll sensitivity (tuned so server int step > 0)
    // Accumulators to buffer small fractional scrolls until they are meaningful server-side
    this.scrollAccumX = 0;
    this.scrollAccumY = 0;
    // Batch threshold: lower means smaller movement triggers a send sooner
    // Default lowered so small movements are detected faster
    this.scrollBatchThreshold = 0.02;
        
    // Optional debug
    this.debug = false;
    this.tapThreshold = 6; // Max pixels moved to still count as tap (lowered to detect small moves)
        this.tapTimeout = 200; // Max ms for tap gesture
        this.pendingRequests = new Set(); // Track pending network requests
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        // Prevent default touch behaviors
        this.trackpad.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        this.trackpad.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        this.trackpad.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        this.trackpad.addEventListener('touchcancel', this.handleTouchEnd.bind(this), { passive: false });
        
        // Prevent context menu and other unwanted behaviors
        this.trackpad.addEventListener('contextmenu', e => e.preventDefault());
        this.trackpad.addEventListener('selectstart', e => e.preventDefault());
        
        // Keep screen awake if possible
        if ('wakeLock' in navigator) {
            navigator.wakeLock.request('screen').catch(() => {
                // Wake lock not supported or denied
            });
        }

        // Initialize socket.io connection if available
        try {
            if (typeof io === 'function') {
                this.socket = io();
                this.socket.on('connect', () => {
                    if (this.debug) console.debug('socket connected');
                });
                this.socket.on('disconnect', () => {
                    if (this.debug) console.debug('socket disconnected');
                });
            }
        } catch (e) {
            // Socket.IO not available - HTTP fallback will be used
            this.socket = null;
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
        // Prefer socket if connected
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('move', { deltaX, deltaY });
                if (this.debug) console.debug('socket emit move', { deltaX, deltaY });
            } catch (e) {
                // fall through to HTTP fallback
            }
            return;
        }

        // HTTP fallback
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
        // Prefer socket if connected
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
    const tp = new PhoneTrackpad();
    // Expose for debugging/tweaks from console
    window.phoneTrackpad = tp;
    // Optional: warm up and indicate connectivity
    tp.checkConnection().catch(() => {});
});

