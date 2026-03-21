# 🤖 SmartPre — AI Crypto Trading Agent

**AI-powered cryptocurrency trading analysis system with ML predictions, technical indicators, and sentiment analysis.**

---

## 🏗️ Architecture

```
smart-pre/
├── backend/                    # Python FastAPI Backend
│   ├── main.py                 # Server + API orchestrator
│   ├── config.py               # Configuration
│   ├── requirements.txt
│   ├── agents/                 # AI Agent Modules
│   │   ├── data_agent.py       # Market data collection (Binance)
│   │   ├── technical_agent.py  # Technical analysis engine
│   │   ├── sentiment_agent.py  # NLP sentiment analysis
│   │   ├── prediction_agent.py # ML ensemble predictor
│   │   ├── signal_agent.py     # Trading signal generator
│   │   ├── risk_agent.py       # Risk management
│   │   └── decision_agent.py   # Final decision engine
│   ├── models/                 # ML Models
│   │   ├── lstm_model.py       # LSTM with attention
│   │   └── transformer_model.py # Transformer encoder
│   ├── indicators/             # Technical Indicators
│   │   ├── rsi.py              # Relative Strength Index
│   │   ├── macd.py             # MACD
│   │   ├── bollinger.py        # Bollinger Bands
│   │   ├── moving_averages.py  # EMA / SMA
│   │   ├── vwap.py             # VWAP
│   │   ├── fibonacci.py        # Fibonacci levels
│   │   └── volume_profile.py   # Volume profile
│   └── utils/
│       ├── binance_client.py   # Binance REST client
│       └── websocket_manager.py # WebSocket stream handler
├── frontend/                   # Dashboard UI
│   ├── index.html
│   ├── css/styles.css
│   └── js/
│       ├── app.js              # Main controller
│       ├── chart.js            # TradingView charts
│       ├── signals.js          # Signal display
│       ├── sentiment.js        # Sentiment display
│       └── websocket.js        # WebSocket client
└── README.md
```

## ⚡ Quick Start

### 1. Create virtual environment

```bash
cd smart-pre/backend
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set environment variables (optional)

```bash
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
```

### 4. Run the server

```bash
python main.py
```

### 5. Open the dashboard

Navigate to **http://localhost:8000**

---

## 🚀 Deployment (Render)

This project is optimized for **Render** (and other cloud providers) with specific bypasses for Binance API blocks.

### Option 1: One-Click Deployment (Blueprint)
Click on **"New Blueprint Service"** in Render and connect your GitHub repository. It will automatically use the `render.yaml` file to configure everything.

### Option 2: Manual Web Service Setup
If you prefer manual setup, use these settings:

- **Build Command**: `cd backend && pip install -r requirements.txt`
- **Start Command**: `cd backend && gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT`
- **Environment Variables**:
  | Variable | Value | Description |
  |----------|-------|-------------|
  | `PYTHON_VERSION` | `3.9.6` | Recommended Python version |
  | `BINANCE_BASE_URL` | `https://api3.binance.com` | Bypasses standard API blocks |
  | `PORT` | `10000` | Port for the web service |

---

## 🧠 Agent Workflow

```
Step 1: Data Agent     → Fetch real-time OHLCV from Binance
Step 2: Technical Agent → Run RSI, MACD, BB, MA, VWAP, Fibonacci, Volume
Step 3: Sentiment Agent → Analyze crypto news & Fear/Greed index
Step 4: Prediction Agent → LSTM + Transformer ensemble prediction
Step 5: Signal Agent    → Generate BUY/SELL/HOLD with entry, targets, stop loss
Step 6: Risk Agent      → Evaluate risk, position sizing, warnings
Step 7: Decision Agent  → Final consensus vote across all systems
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/health` | GET | Health check |
| `/api/symbols` | GET | Tracked symbols |
| `/api/prices` | GET | All current prices |
| `/api/analysis/{symbol}` | GET | Full analysis |
| `/api/technical/{symbol}` | GET | Technical analysis |
| `/api/prediction/{symbol}` | GET | ML prediction |
| `/api/sentiment/{symbol}` | GET | Sentiment analysis |
| `/api/signal/{symbol}` | GET | Trading signal |
| `/api/market/{symbol}` | GET | Market summary |
| `/api/decisions` | GET | All decisions |
| `/api/analyze/{symbol}` | POST | Trigger analysis |
| `/ws` | WebSocket | Real-time updates |

## 🤖 ML Models

### LSTM with Attention
- Input: OHLCV + 7 technical indicators
- Architecture: 2-layer LSTM → Attention → FC → Direction + Magnitude
- Output: direction probability + predicted return

### Transformer Encoder
- Positional encoding for time series
- Multi-head self-attention (4 heads)
- 3-head output: direction, magnitude, volatility

### Ensemble
- LSTM weight: 45%
- Transformer weight: 55%
- Outputs 5-minute and 15-minute forecasts

## 📈 Technical Indicators

- **RSI** — with divergence detection
- **MACD** — crossover and momentum
- **Bollinger Bands** — squeeze detection
- **EMA/SMA** — golden/death cross
- **VWAP** — deviation bands
- **Fibonacci** — retracement levels
- **Volume Profile** — POC and Value Area

## ⚠️ Disclaimer

This is an **educational/research project**. It does NOT execute real trades.
Cryptocurrency trading carries significant risk. Never trade with money you cannot afford to lose.
Past performance does not guarantee future results. Always do your own research.

---

Built with ❤️ by SmartPre AI


USE_REST_POLLING = true ← SABSE IMPORTANT
REST_POLL_INTERVAL = 3
BINANCE_BASE_URL = https://api3.binance.com
PORT = 10000
PYTHON_VERSION = 3.11.

--------------------
USE_BINANCE_PROXY = true
BINANCE_PROXY_URL = https://corsproxy.io/?