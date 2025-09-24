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
            this.trackpad.addEventListener('pointerdown', (e) => { this.emitRawDownPointer(e); }, { passive: false });
            this.trackpad.addEventListener('pointermove', (e) => { this.emitRawMovePointer(e); }, { passive: false });
            this.trackpad.addEventListener('pointerup', (e) => { this.emitRawUpPointer(e); }, { passive: false });
            this.trackpad.addEventListener('pointercancel', (e) => { this.emitRawUpPointer(e); }, { passive: false });
        } else {
            this.trackpad.addEventListener('touchstart', (e) => { this.emitRawTouchStart(e); }, { passive: false });
            this.trackpad.addEventListener('touchmove', (e) => { this.emitRawTouchMove(e); }, { passive: false });
            this.trackpad.addEventListener('touchend', (e) => { this.emitRawTouchEnd(e); }, { passive: false });
            this.trackpad.addEventListener('touchcancel', (e) => { this.emitRawTouchEnd(e); }, { passive: false });
        }
    }

    // Minimal pointer-based raw emission (uses coalesced events when available)
    emitRawDownPointer(e) {
        if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
        e.preventDefault();
        const payload = { type: 'down', id: e.pointerId, x: e.pageX, y: e.pageY, pointerType: e.pointerType, time: Date.now() };
        this._sendRaw(payload);
    }

    emitRawMovePointer(e) {
        if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
        e.preventDefault();
        const events = (typeof e.getCoalescedEvents === 'function') ? e.getCoalescedEvents() : [e];
        const batch = [];
        for (const ev of events) {
            batch.push({ type: 'move', id: e.pointerId, x: ev.pageX || ev.clientX, y: ev.pageY || ev.clientY, pointerType: e.pointerType, time: Date.now() });
        }
        this._sendRaw(batch);
    }

    emitRawUpPointer(e) {
        if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
        e.preventDefault();
        const payload = { type: 'up', id: e.pointerId, x: e.pageX, y: e.pageY, pointerType: e.pointerType, time: Date.now() };
        this._sendRaw(payload);
    }

    // Touch event fallbacks
    emitRawTouchStart(e) {
        e.preventDefault();
        const batch = [];
        for (const t of e.changedTouches) batch.push({ type: 'down', id: t.identifier, x: t.pageX, y: t.pageY, pointerType: 'touch', time: Date.now() });
        this._sendRaw(batch);
    }

    emitRawTouchMove(e) {
        e.preventDefault();
        const batch = [];
        for (const t of e.changedTouches) batch.push({ type: 'move', id: t.identifier, x: t.pageX, y: t.pageY, pointerType: 'touch', time: Date.now() });
        this._sendRaw(batch);
    }

    emitRawTouchEnd(e) {
        e.preventDefault();
        const batch = [];
        for (const t of e.changedTouches) batch.push({ type: 'up', id: t.identifier, x: t.pageX, y: t.pageY, pointerType: 'touch', time: Date.now() });
        this._sendRaw(batch);
    }

    // Core: send raw events via socket if available, otherwise POST to /raw
    _sendRaw(eventOrArray) {
        if (this.socket && this.socket.connected) {
            try {
                if (Array.isArray(eventOrArray)) {
                    for (const ev of eventOrArray) this.socket.emit(`raw.${ev.type}`, ev);
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
    // Optional: warm up and indicate connectivity
    tp.checkConnection().catch(() => {});
});

