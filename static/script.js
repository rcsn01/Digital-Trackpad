// PhoneTrackpad - minimal, robust client
// Responsibilities:
// - Capture touch events and convert to move/scroll/click
// - Prevent clicks after any movement (movement wins)
// - Use fire-and-forget network calls to reduce perceived latency

class PhoneTrackpad {
    constructor() {
        this.trackpad = document.getElementById('trackpad');
        this.socket = null;
        this.kbInput = document.getElementById('kbInput');
        this.kbToggle = document.getElementById('kbToggle');
        // Config: scale finger positions by devicePixelRatio to amplify tiny motions
        this.useDPRScale = true;
        // Track active touches/pointers by id with latest absolute coordinates
        this.activeContacts = new Map(); // id -> { id, x, y, pointerType, time }
        this.streaming = false;
        this._rafId = null;
        this.initSocket();
        this.initEventListeners();
        this.initKeyboardUI();
    }

    initSocket() {
        try {
            if (typeof io === 'function') {
                // Prefer WebSocket transport; Socket.IO will fall back if websocket isn't available.
                try {
                    this.socket = io({ transports: ['websocket'], reconnectionAttempts: 5, timeout: 2000 });
                } catch (e) {
                    // Fallback to default initialization
                    this.socket = io();
                }

                // Basic handlers for connection lifecycle
                this.socket.on('connect', () => {
                    console.debug && console.debug('socket connected (transport=' + this.socket.io.engine.transport.name + ')');
                });
                this.socket.on('connect_error', (err) => {
                    console.debug && console.debug('socket connect_error', err);
                });
                this.socket.on('disconnect', (reason) => {
                    console.debug && console.debug('socket disconnected', reason);
                });
            }
        } catch (e) {
            this.socket = null;
        }
    }

    initKeyboardUI() {
        if (!this.kbInput || !this.kbToggle) return;

        // When toggle pressed, focus the hidden input to raise mobile keyboard
        this.kbToggle.addEventListener('click', (e) => {
            e.preventDefault();
            // Simply focus the hidden input to trigger the mobile keyboard
            this.kbInput.focus();
        });

        // Capture input events and send characters to server
        this.kbInput.addEventListener('input', (e) => {
            const val = e.target.value || '';
            if (val.length > 0) {
                for (const ch of val) this.sendKey({ type: 'char', value: ch });
            }
            // keep input value minimal to avoid showing selections; clear after short timeout
            setTimeout(() => { try { e.target.value = ''; } catch (e) {} }, 10);
        });

        // Capture special keys via keydown
        this.kbInput.addEventListener('keydown', (e) => {
            // Prevent default to avoid local side-effects
            e.preventDefault();
            const keyEvent = { type: 'key', key: e.key, code: e.code, altKey: e.altKey, ctrlKey: e.ctrlKey, shiftKey: e.shiftKey, metaKey: e.metaKey };
            this.sendKey(keyEvent);
            // For printable keys, let input handler send the character via 'input'
        });

        // When input loses focus, hide it again (move offscreen)
        this.kbInput.addEventListener('blur', () => {
            this.kbInput.style.position = 'fixed';
            this.kbInput.style.left = '-9999px';
            this.kbInput.style.bottom = '-9999px';
        });
    }

    sendKey(keyObj) {
        // Attempt socket first
        if (this.socket && this.socket.connected) {
            try {
                this.socket.emit('key', keyObj);
                return;
            } catch (e) {
                // fallback to HTTP
            }
        }

        // HTTP fallback: post to /key
        fetch('/key', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(keyObj) }).catch(() => {});
    }

    initEventListeners() {
        // Keep screen awake if possible
        if ('wakeLock' in navigator) {
            navigator.wakeLock.request('screen').catch(() => {});
        }

        // Prevent context menu
        this.trackpad.addEventListener('contextmenu', e => e.preventDefault());

        if (window.PointerEvent) {
            this.trackpad.addEventListener('pointerdown', (e) => { this.onPointerDown(e); }, { passive: false });
            this.trackpad.addEventListener('pointermove', (e) => { this.onPointerMove(e); }, { passive: false });
            // Prefer raw updates if available (higher frequency); we still send immediately
            this.trackpad.addEventListener('pointerrawupdate', (e) => { this.onPointerRawUpdate(e); }, { passive: false });
            this.trackpad.addEventListener('pointerup', (e) => { this.onPointerUp(e); }, { passive: false });
            this.trackpad.addEventListener('pointercancel', (e) => { this.onPointerUp(e); }, { passive: false });
        } else {
            this.trackpad.addEventListener('touchstart', (e) => { this.onTouchStart(e); }, { passive: false });
            this.trackpad.addEventListener('touchmove', (e) => { this.onTouchMove(e); }, { passive: false });
            this.trackpad.addEventListener('touchend', (e) => { this.onTouchEnd(e); }, { passive: false });
            this.trackpad.addEventListener('touchcancel', (e) => { this.onTouchEnd(e); }, { passive: false });
        }
    }

    _scaleXY(x, y) {
        const s = this.useDPRScale ? (window.devicePixelRatio || 1) : 1;
        return { x: x * s, y: y * s };
    }

    // PointerEvent handlers (we still emit 'down'/'up' immediately; 'move' is streamed)
    onPointerDown(e) {
        if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
        e.preventDefault();
        const now = Date.now();
        const id = e.pointerId;
        const scaled = this._scaleXY(e.pageX, e.pageY);
        const pt = { id, x: scaled.x, y: scaled.y, pointerType: e.pointerType, time: now };
        this.activeContacts.set(id, pt);
        // Send down immediately
        this._sendRaw({ type: 'down', ...pt });
        this._ensureStreaming();
    }

    onPointerMove(e) {
        if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
        e.preventDefault();
        const id = e.pointerId;
        const now = Date.now();
        // Prefer coalesced events for more samples in a single frame
        const events = (typeof e.getCoalescedEvents === 'function') ? e.getCoalescedEvents() : [e];
        const batch = [];
        for (const ev of events) {
            const ex = (ev.pageX != null ? ev.pageX : ev.clientX);
            const ey = (ev.pageY != null ? ev.pageY : ev.clientY);
            const scaled = this._scaleXY(ex, ey);
            const pt = { id, x: scaled.x, y: scaled.y, pointerType: e.pointerType, time: now };
            this.activeContacts.set(id, pt);
            batch.push({ type: 'move', ...pt });
        }
        if (batch.length) this._sendRaw(batch);
    }

    onPointerRawUpdate(e) {
        if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
        e.preventDefault();
        const id = e.pointerId;
        const now = Date.now();
        const events = (typeof e.getCoalescedEvents === 'function') ? e.getCoalescedEvents() : [e];
        const batch = [];
        for (const ev of events) {
            const ex = (ev.pageX != null ? ev.pageX : ev.clientX);
            const ey = (ev.pageY != null ? ev.pageY : ev.clientY);
            const scaled = this._scaleXY(ex, ey);
            const pt = { id, x: scaled.x, y: scaled.y, pointerType: e.pointerType, time: now };
            this.activeContacts.set(id, pt);
            batch.push({ type: 'move', ...pt });
        }
        if (batch.length) this._sendRaw(batch);
    }

    onPointerUp(e) {
        if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
        e.preventDefault();
        const now = Date.now();
        const id = e.pointerId;
        const scaled = this._scaleXY(e.pageX, e.pageY);
        const pt = { id, x: scaled.x, y: scaled.y, pointerType: e.pointerType, time: now };
        // Send up immediately
        this._sendRaw({ type: 'up', ...pt });
        this.activeContacts.delete(id);
        this._maybeStopStreaming();
    }

    // Touch event fallbacks
    onTouchStart(e) {
        e.preventDefault();
        const now = Date.now();
        const batch = [];
        for (const t of e.changedTouches) {
            const id = t.identifier;
            const scaled = this._scaleXY(t.pageX, t.pageY);
            const pt = { id, x: scaled.x, y: scaled.y, pointerType: 'touch', time: now };
            this.activeContacts.set(id, pt);
            batch.push({ type: 'down', ...pt });
        }
        if (batch.length) this._sendRaw(batch);
        this._ensureStreaming();
    }

    onTouchMove(e) {
        e.preventDefault();
        const now = Date.now();
        const batch = [];
        for (const t of e.changedTouches) {
            const id = t.identifier;
            const scaled = this._scaleXY(t.pageX, t.pageY);
            const pt = { id, x: scaled.x, y: scaled.y, pointerType: 'touch', time: now };
            this.activeContacts.set(id, pt);
            batch.push({ type: 'move', ...pt });
        }
        if (batch.length) this._sendRaw(batch);
    }

    onTouchEnd(e) {
        e.preventDefault();
        const now = Date.now();
        const batch = [];
        for (const t of e.changedTouches) {
            const id = t.identifier;
            const scaled = this._scaleXY(t.pageX, t.pageY);
            const pt = { id, x: scaled.x, y: scaled.y, pointerType: 'touch', time: now };
            batch.push({ type: 'up', ...pt });
            this.activeContacts.delete(id);
        }
        if (batch.length) this._sendRaw(batch);
        this._maybeStopStreaming();
    }

    // Core: send raw events via socket if available, otherwise POST to /raw
    _sendRaw(eventOrArray) {
        if (this.socket && this.socket.connected) {
            try {
                if (Array.isArray(eventOrArray)) {
                    // Batch send as a single socket message for efficiency
                    this.socket.emit('raw.batch', eventOrArray);
                } else {
                    const ev = eventOrArray;
                    this.socket.emit(`raw.${ev.type}`, ev);
                }
            } catch (e) {
                // fall through to HTTP fallback
            }
            return;
        }

        // HTTP fallback: send array for efficiency
        const body = Array.isArray(eventOrArray) ? eventOrArray : [eventOrArray];
        fetch('/raw', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).catch(() => {});
    }

    // Ensure the streaming loop is running when we have one or more active contacts
    _ensureStreaming() {
        if (this.streaming) return;
        this.streaming = true;
        const tick = () => {
            if (!this.streaming) return;
            if (this.activeContacts.size === 0) {
                this.streaming = false;
                this._rafId = null;
                return;
            }
            const now = Date.now();
            const batch = [];
            for (const pt of this.activeContacts.values()) {
                // Always send latest known positions while touching
                batch.push({ type: 'move', id: pt.id, x: pt.x, y: pt.y, pointerType: pt.pointerType, time: now });
            }
            if (batch.length) this._sendRaw(batch);
            this._rafId = (window.requestAnimationFrame || function (cb) { return setTimeout(cb, 16); })(tick);
        };
        tick();
    }

    _maybeStopStreaming() {
        if (this.activeContacts.size === 0 && this.streaming) {
            this.streaming = false;
            if (this._rafId) {
                (window.cancelAnimationFrame || clearTimeout)(this._rafId);
                this._rafId = null;
            }
        }
    }

    // Simple visual touch feedback (kept for UX)
    showTouchFeedback(x, y) {
        const feedback = document.createElement('div');
        feedback.className = 'touch-feedback';
        feedback.style.left = x + 'px';
        feedback.style.top = y + 'px';
        this.trackpad.appendChild(feedback);
        setTimeout(() => { if (feedback.parentNode) feedback.parentNode.removeChild(feedback); }, 300);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    const tp = new PhoneTrackpad();
    // Expose for debugging/tweaks from console
    window.phoneTrackpad = tp;
});

