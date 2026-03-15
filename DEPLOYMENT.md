# 🚀 SmartPre Deployment Guide

## Quick Deploy to Render (5 Minutes)

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Production ready"
git push origin main
```

### Step 2: Deploy on Render
1. Go to [Render.com](https://render.com/) → **New** → **Web Service**
2. Connect your **GitHub repo**
3. Settings:
   - **Name**: `smartpre` (or any name)
   - **Region**: Oregon (US West)
   - **Branch**: `main`
   - **Runtime**: `Python`
   - **Build Command**: `pip install --upgrade pip && pip install --no-cache-dir -r backend/requirements.txt`
   - **Start Command**: `cd backend && python main.py`
   - **Plan**: Free
4. **Environment Variables** (click "Add Environment Variable"):
   - `PYTHON_VERSION` = `3.11.9`
   - `RENDER` = `true`
5. Click **Deploy Web Service**

### Step 3: Wait & Access
- Render will build (~3-5 minutes)
- Your site will be live at: `https://smartpre-XXXX.onrender.com`
- Everything works: Dashboard, Charts, WebSocket, Signals — all from single URL

## How It Works
- Backend (FastAPI) serves the frontend HTML/CSS/JS directly
- WebSocket auto-detects the host (`wss://your-app.onrender.com/ws`)
- No separate frontend deployment needed!
- Real-time Binance data streams via WebSocket
- AI analysis runs every 5 seconds

## Important Notes
- **Free tier**: App sleeps after 15 min of inactivity. First request takes ~30 seconds to wake up.
- **Paid tier** ($7/mo): 24/7 uptime, better performance.
- **No API keys needed**: Uses public Binance endpoints (no authentication required).

## Troubleshooting
If deploy fails:
1. Check Render logs for errors
2. Make sure `requirements.txt` doesn't include `torch` or `transformers` (too large)
3. Check `/api/health` endpoint works: `https://your-app.onrender.com/api/health`

## Local Development
```bash
cd backend
python -m venv venv_win
.\venv_win\Scripts\activate     # Windows
pip install -r requirements.txt
python main.py
```
Open http://localhost:8000
