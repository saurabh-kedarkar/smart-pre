# SmartPre AI Trading Agent 🚀

SmartPre is a real-time cryptocurrency trading analysis system powered by ML (LSTM & Transformers) and technical indicators.

## Features
- **Real-time Data:** Live streaming from Binance WebSocket.
- **ML Predictions:** Ensemble model using PyTorch (LSTM + Transformer).
- **Technical Analysis:** RSI, MACD, Bollinger Bands, VWAP, and more.
- **Automated Signals:** BUY/SELL/HOLD signals based on multi-agent consensus.
- **Modern Dashboard:** Glassmorphic UI with dynamic charts.

## Local Setup
1. **Clone the repo:** `git clone https://github.com/saurabh-kedarkar/smart-pre.git`
2. **Backend Setup:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Or .\venv\Scripts\activate on Windows
   pip install -r requirements.txt
   python main.py
   ```
3. **Open Dashboard:** Visit `http://localhost:8000`

## Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for instructions on hosting for free on Render and Vercel.
