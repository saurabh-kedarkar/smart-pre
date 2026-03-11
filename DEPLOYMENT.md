# 🚀 Deployment Guide: SmartPre AI Trading Agent

Follow these steps to deploy your trading agent for **FREE**.

## 1. Push to GitHub
Run these commands in your terminal to upload the code:
```bash
git push -u origin main
```

## 2. Backend Deployment (Render)
1. Go to [Render.com](https://render.com/).
2. Click **New +** > **Web Service**.
3. Connect your `smart-pre` GitHub repo.
4. Settings:
   - **Name**: `smart-pre-backend`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Click **Deploy**.
6. **Note your URL:** It will be something like `https://smart-pre-backend.onrender.com`.

## 3. Frontend Deployment (Vercel)
1. Go to [Vercel.com](https://vercel.com/).
2. Import your `smart-pre` GitHub repo.
3. Settings:
   - **Framework Preset**: `Other`
   - **Root Directory**: `frontend`
4. Click **Deploy**.

## 4. Connect Frontend to Backend
Once your Render backend is live:
1. Open `frontend/js/app.js`.
2. Update the `API_BASE_URL` with your Render URL:
   ```javascript
   const API_BASE_URL = isLocal ? '' : 'https://your-backend-name.onrender.com';
   ```
3. Open `frontend/js/websocket.js`.
4. Update the `productionBackend` with your Render host (without https://):
   ```javascript
   const productionBackend = 'your-backend-name.onrender.com';
   ```
5. Commit and push the changes:
   ```bash
   git add .
   git commit -m "Update production URLs"
   git push
   ```

---
**Tip:** Render's free tier sleeps after 15 mins. Use a service like **Cron-job.org** to ping your `/api/health` endpoint every 10 mins to keep it awake!
