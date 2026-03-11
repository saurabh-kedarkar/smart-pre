# 🚀 Deployment Guide: SmartPre AI Trading Agent

Follow these steps to deploy your trading agent for **FREE** using modern cloud platforms.

## 1. Prepare your Codebase
Ensure your project structure looks like this:
```
/smart-pre
  /backend
    main.py
    requirements.txt
    ...
  /frontend
    index.html
    static/
    ...
```

## 2. Backend Deployment (FastAPI/Python)
We recommend **Render** or **Koyeb** for the backend.

### Option A: Render (Easiest)
1. Push your code to a **GitHub** repository.
2. Go to [Render.com](https://render.com/) and create a new **Web Service**.
3. Connect your GitHub repo.
4. Settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add **Environment Variables**:
   - `BINANCE_API_KEY`: Your key
   - `BINANCE_API_SECRET`: Your secret
6. Click **Deploy**. Render will give you a URL like `https://smart-pre-backend.onrender.com`.

## 3. Frontend Deployment (Static HTML/JS)
You can use **Vercel** or **Netlify**.

### Option A: Vercel
1. Go to [Vercel.com](https://vercel.com/) and create a new project.
2. Connect your GitHub repo.
3. Settings:
   - **Framework Preset**: `Other`
   - **Root Directory**: `frontend`
4. Click **Deploy**. Vercel will give you a URL like `https://smart-pre.vercel.app`.

## 4. Connect Frontend to Backend
Once you have your backend URL from Render, update your frontend configuration:
1. Open `frontend/js/websocket.js`.
2. Find the WebSocket connection logic and update the URL:
   ```javascript
   // Replace localhost with your Render URL (use wss:// for production)
   const backendUrl = 'smart-pre-backend.onrender.com'; 
   this.socket = new WebSocket(`wss://${backendUrl}/ws`);
   ```
3. Re-deploy the frontend.

## 5. Free Database (Optional)
If you add a database later for trade history:
- Use [Neon.tech](https://neon.tech/) for free **PostgreSQL**.
- Use [Upstash](https://upstash.com/) for free **Redis** (caching).

---
**Note:** Render's free tier "sleeps" after 15 minutes of inactivity. For 24/7 trading, you might eventually need a $7/mo plan or a VPS (like a $5 DigitalOcean droplet).
