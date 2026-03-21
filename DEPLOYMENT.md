# 🚀 SmartPre — Render Deployment Guide (Binance-Compatible)

## ⚠️ Problem: Binance Blocked on Render
Render's free tier blocks outbound connections to `*.binance.com` WebSocket (`wss://stream.binance.com`).
REST API access may also be intermittent. This guide shows how to deploy with full functionality.

---

## 🛠️ How It Works (No Functionality Change)

The app uses a **3-layer fallback system**:

1. **REST API with Endpoint Rotation** — Cycles through `api1`, `api2`, `api3`, `api4`, `api.binance.com`, and `api.binance.us` automatically
2. **REST Polling for Real-Time Data** — Instead of WebSocket, polls Binance REST API every 3 seconds (configurable)
3. **Optional Proxy** — If ALL endpoints are blocked, route through a CORS proxy

**Result**: Same data, same signals, same UI — just uses REST instead of WebSocket.

---

## 📋 Step-by-Step Deployment

### Step 1: Push to GitHub

```bash
cd /path/to/smart-pre
git add .
git commit -m "Add Render deployment support"
git push origin main
```

### Step 2: Create Render Web Service

1. Go to [render.com](https://render.com) → **Dashboard** → **New +** → **Web Service**
2. Connect your GitHub repo (`smart-pre`)
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `smartpre-ai-crypto` |
| **Region** | `Oregon (US West)` or `Frankfurt (EU)` |
| **Branch** | `main` |
| **Root Directory** | *(leave empty)* |
| **Runtime** | `Python` |
| **Build Command** | `cd backend && pip install -r requirements.txt` |
| **Start Command** | `cd backend && gunicorn -w 1 -k uvicorn.workers.UvicornWorker --timeout 120 --keep-alive 30 main:app` |
| **Plan** | `Free` |

### Step 3: Set Environment Variables

Go to **Environment** tab and add these:

| Key | Value | Required |
|-----|-------|----------|
| `PYTHON_VERSION` | `3.11.0` | ✅ |
| `PORT` | `10000` | ✅ |
| `BINANCE_BASE_URL` | `https://api3.binance.com` | ✅ |
| `USE_REST_POLLING` | `true` | ✅ **Critical** |
| `REST_POLL_INTERVAL` | `3` | ✅ |
| `USE_BINANCE_PROXY` | `false` | Optional |
| `BINANCE_PROXY_URL` | *(empty)* | Optional |

### Step 4: Deploy

Click **Create Web Service** → Wait for build (5-10 minutes first time).

Your app will be live at: `https://smartpre-ai-crypto.onrender.com`

---

## 🔧 If Binance REST Is ALSO Blocked

If **direct REST API** calls to Binance also fail, enable the proxy layer:

### Option A: Use a Free CORS Proxy

Set these environment variables on Render:

```
USE_BINANCE_PROXY = true
BINANCE_PROXY_URL = https://corsproxy.io/?
```

### Option B: Deploy Your Own Proxy (Recommended for Production)

1. Create another Render Web Service with this simple Node.js proxy:

```javascript
// proxy-server.js
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
app.use('/binance', createProxyMiddleware({
    target: 'https://api3.binance.com',
    changeOrigin: true,
    pathRewrite: { '^/binance': '' },
}));

app.listen(process.env.PORT || 3000);
```

2. Set your SmartPre env vars:
```
USE_BINANCE_PROXY = true
BINANCE_PROXY_URL = https://your-proxy.onrender.com/binance
```

---

## 🧪 Testing Locally (Simulating Render)

To test the Render configuration locally:

```bash
cd backend

# Set environment variables
export USE_REST_POLLING=true
export REST_POLL_INTERVAL=3
export PORT=8000

# Run
python main.py
```

Open `http://localhost:8000` — you should see the dashboard working normally.

---

## 📊 Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_REST_POLLING` | `false` | Use REST API instead of WebSocket for real-time data |
| `REST_POLL_INTERVAL` | `3` | How often to poll (seconds). Lower = more real-time, higher = less API load |
| `USE_BINANCE_PROXY` | `false` | Route Binance REST calls through a proxy |
| `BINANCE_PROXY_URL` | *(empty)* | Proxy URL prefix (e.g., `https://corsproxy.io/?`) |
| `BINANCE_BASE_URL` | `https://api3.binance.com` | Primary Binance API endpoint |
| `PORT` | `8000` | Server port (Render sets this automatically) |

---

## ⚡ Performance Notes

- **Free Tier**: Render sleeps after 15 min of inactivity. First request takes ~30s to wake up.
- **REST Polling**: Every 3 seconds per symbol × 6 symbols = ~12 requests/3s. Binance rate limit is 1200/min, so this is well within limits.
- **CPU-Only PyTorch**: The requirements.txt installs CPU-only PyTorch (~200MB instead of ~2GB) to fit within Render's free tier memory.

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails with memory error | Ensure using CPU-only torch in requirements.txt |
| "All Binance endpoints failed" | Enable proxy: `USE_BINANCE_PROXY=true`, `BINANCE_PROXY_URL=https://corsproxy.io/?` |
| App starts but no data | Check logs for "Initial data load failed", enable REST polling |
| WebSocket errors in browser console | This is normal — browser WS connects to YOUR Render app, not Binance. Check backend logs. |
| Slow response after inactivity | Free tier limitation — app needs to wake up. Consider $7/mo Starter plan for 24/7. |
