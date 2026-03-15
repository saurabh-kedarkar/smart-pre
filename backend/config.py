"""
SmartPre Configuration
"""
import os

# ─── Binance API ───
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BINANCE_BASE_URL = "https://api.binance.com"
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"

# ─── Trading Pairs ───
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h"]

# ─── ML Model ───
SEQUENCE_LENGTH = 60          # lookback window
PREDICTION_HORIZON = 15       # minutes ahead
MODEL_CONFIDENCE_THRESHOLD = 0.55
LSTM_HIDDEN_SIZE = 128
LSTM_NUM_LAYERS = 2
TRANSFORMER_D_MODEL = 64
TRANSFORMER_NHEAD = 4
TRANSFORMER_NUM_LAYERS = 2

# ─── Technical Analysis ───
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2
EMA_PERIODS = [9, 21, 50, 200]
SMA_PERIODS = [20, 50, 100, 200]
VWAP_PERIOD = 14

# ─── Sentiment ───
SENTIMENT_WEIGHT = 0.15
TECHNICAL_WEIGHT = 0.45
ML_PREDICTION_WEIGHT = 0.40

# ─── Risk Management ───
MAX_RISK_PER_TRADE = 0.02     # 2% risk
DEFAULT_STOP_LOSS_PCT = 0.005  # 0.5%
DEFAULT_TAKE_PROFIT_PCT = 0.01 # 1.0%
MIN_CONFIDENCE_TO_TRADE = 0.50

# ─── Server ───
SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", "8000"))  # Render sets $PORT automatically
WS_HEARTBEAT_INTERVAL = 30

# ─── News / Sentiment APIs (placeholders) ───
CRYPTO_NEWS_API_KEY = os.getenv("CRYPTO_NEWS_API_KEY", "")
CRYPTO_NEWS_API_URL = "https://cryptopanic.com/api/v1/posts/"
