/**
 * SmartPre — WebSocket Manager
 * Handles real-time connection to the backend
 */
class SmartPreWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 50;
        this.reconnectDelay = 2000;
        this.listeners = {};
        this.isConnected = false;
        this.pingInterval = null;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        
        // --- DEPLOYMENT CONFIG ---
        // Change this URL to your Render backend URL (e.g., 'your-app.onrender.com')
        const productionBackend = 'smart-pre-backend.onrender.com'; 
        
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        const host = isLocal ? window.location.host : productionBackend;
        const wsUrl = `${protocol}//${host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);
            this._setupHandlers();
        } catch (e) {
            console.error('WebSocket connection failed:', e);
            this._scheduleReconnect();
        }
    }

    _setupHandlers() {
        this.ws.onopen = () => {
            console.log('✅ WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this._updateStatus('connected');
            this._startPing();
            this._emit('connected');
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this._handleMessage(msg);
            } catch (e) {
                console.error('Failed to parse WS message:', e);
            }
        };

        this.ws.onclose = () => {
            console.warn('WebSocket closed');
            this.isConnected = false;
            this._updateStatus('disconnected');
            this._stopPing();
            this._scheduleReconnect();
            this._emit('disconnected');
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this._updateStatus('error');
        };
    }

    _handleMessage(msg) {
        const type = msg.type;

        switch (type) {
            case 'initial_data':
                this._emit('initialData', msg.data);
                break;
            case 'analysis_update':
                this._emit('analysisUpdate', msg.data);
                break;
            case 'analysis_result':
                this._emit('analysisResult', msg.data);
                break;
            case 'price_update':
                this._emit('priceUpdate', msg.data);
                break;
            case 'pong':
                // Heartbeat acknowledged
                break;
            default:
                this._emit(type, msg.data);
            // console.log('Received message type:', type);
        }
    }

    send(type, data = {}) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, ...data }));
        }
    }

    requestAnalysis(symbol) {
        this.send('analyze', { symbol });
    }

    _startPing() {
        this._stopPing();
        this.pingInterval = setInterval(() => {
            this.send('ping');
        }, 25000);
    }

    _stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }
        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * this.reconnectAttempts, 30000);
        console.log(`Reconnecting in ${delay / 1000}s (attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(), delay);
    }

    _updateStatus(status) {
        const dot = document.querySelector('.status-dot');
        const text = document.querySelector('.status-text');
        if (!dot || !text) return;

        dot.className = 'status-dot';
        switch (status) {
            case 'connected':
                dot.classList.add('connected');
                text.textContent = 'Live';
                break;
            case 'disconnected':
                dot.classList.add('disconnected');
                text.textContent = 'Backend Offline';
                break;
            case 'error':
                dot.classList.add('disconnected');
                text.textContent = 'Connection Error';
                break;
        }
    }

    // Event system
    on(event, callback) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(callback);
    }

    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        }
    }

    _emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(cb => cb(data));
        }
    }
}

// Global instance
window.smartWS = new SmartPreWebSocket();
