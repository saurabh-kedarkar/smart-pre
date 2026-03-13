"""
Data Agent — collects and manages market data from Binance.
"""
import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from utils.binance_client import BinanceClient
from utils.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class DataAgent:
    """
    Collects real-time and historical market data.
    Provides a unified data interface for other agents.
    """

    def __init__(self, symbols: list = None):
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
        self.client = BinanceClient()
        self.ws_manager = WebSocketManager()

        # Data stores
        self._candles: dict = {}       # symbol -> {timeframe -> DataFrame}
        self._tickers: dict = {}       # symbol -> latest ticker
        self._order_books: dict = {}   # symbol -> order book
        self._prices: dict = {}        # symbol -> current price
        self._last_update: dict = {}
        self.use_simulation = False
        self._simulation_trend: dict = {} # symbol -> float (current trend bias)

    async def initialize(self) -> None:
        """Load initial historical data for all symbols in parallel."""
        logger.info("Initializing Data Agent...")

        async def init_symbol(symbol):
            try:
                multi_tf = await self.client.get_multi_timeframe(symbol)
                self._candles[symbol] = multi_tf

                ticker = await self.client.get_ticker_24h(symbol)
                self._tickers[symbol] = ticker

                order_book = await self.client.get_order_book(symbol)
                self._order_books[symbol] = order_book

                self._prices[symbol] = float(ticker.get("lastPrice", 0))
                self._last_update[symbol] = datetime.utcnow().isoformat()

                logger.info(f"Loaded data for {symbol}")
            except Exception as e:
                logger.error(f"Failed to load {symbol}: {e}")

        # Run all initializations in parallel
        try:
            await asyncio.gather(*(init_symbol(s) for s in self.symbols))
        except Exception as e:
            if "451" in str(e):
                self.use_simulation = True
        
        # Check if any data was loaded or if explicitly blocked
        loaded_count = sum(1 for s in self.symbols if s in self._prices)
        if loaded_count == 0 or self.use_simulation:
            logger.warning("⚠️ Binance blocked or unreachable. Activating simulation mode...")
            self.use_simulation = True
            self._set_fallback_data()
        else:
            logger.info(f"✅ Data Agent initialized with {loaded_count} symbols")

    def _set_fallback_data(self) -> None:
        """Populate with realistic simulated data if Binance is unreachable."""
        base_prices = {
            "BTCUSDT": 65000.0, "ETHUSDT": 3500.0, "SOLUSDT": 145.0,
            "BNBUSDT": 580.0, "XRPUSDT": 0.62, "ADAUSDT": 0.45,
            "AVAXUSDT": 35.0, "DOTUSDT": 7.0, "LINKUSDT": 18.0
        }
        
        for symbol in self.symbols:
            price = base_prices.get(symbol, 100.0)
            # Add some randomness
            price *= (1 + (np.random.random() - 0.5) * 0.01)
            
            self._prices[symbol] = price
            self._tickers[symbol] = {
                "lastPrice": str(price),
                "highPrice": str(price * 1.02),
                "lowPrice": str(price * 0.98),
                "volume": "1000",
                "quoteVolume": str(price * 1000),
            }
            self._last_update[symbol] = datetime.utcnow().isoformat()
            
            # Create dummy candles if missing
            self._simulation_trend[symbol] = (np.random.random() - 0.5) * 0.002
            if symbol not in self._candles:
                # We generate manual DF since Binance is blocked
                # Use a moving window for simulation
                dates = pd.date_range(end=datetime.utcnow(), periods=200, freq='1min')
                df = pd.DataFrame(index=dates)
                df.index.name = "open_time"
                
                # Create a more structured random walk with momentum
                walk = np.random.randn(200).cumsum() * 0.001
                df['close'] = price * (1 + walk)
                df['open'] = df['close'].shift(1).fillna(df['close'] * 0.999)
                df['high'] = df[['open', 'close']].max(axis=1) * 1.001
                df['low'] = df[['open', 'close']].min(axis=1) * 0.999
                df['volume'] = np.random.random(200) * 10 + 5
                df['quote_vol'] = df['volume'] * df['close']
                df['trades'] = 100
                
                self._candles[symbol] = {"1m": df, "5m": df, "15m": df, "1h": df}

    async def start_streaming(self) -> None:
        """Start WebSocket streams for all symbols."""
        if self.use_simulation:
            logger.info("Skipping real-time streams (simulation mode active)")
            return

        for symbol in self.symbols:
            await self.ws_manager.subscribe_ticker(
                symbol, lambda data, s=symbol: self._on_ticker(s, data)
            )
            await self.ws_manager.subscribe_kline(
                symbol, "1m", lambda data, s=symbol: self._on_kline(s, data)
            )

        await self.ws_manager.start()

    def _on_ticker(self, symbol: str, data: dict) -> None:
        """Handle real-time ticker update."""
        self._prices[symbol] = float(data.get("c", 0))
        self._tickers[symbol] = {
            "lastPrice": data.get("c"),
            "highPrice": data.get("h"),
            "lowPrice": data.get("l"),
            "volume": data.get("v"),
            "quoteVolume": data.get("q"),
        }
        self._last_update[symbol] = datetime.utcnow().isoformat()

    def _on_kline(self, symbol: str, data: dict) -> None:
        """Handle real-time kline update."""
        k = data.get("k", {})
        if not k:
            return

        new_row = {
            "open": float(k["o"]),
            "high": float(k["h"]),
            "low": float(k["l"]),
            "close": float(k["c"]),
            "volume": float(k["v"]),
            "quote_vol": float(k["q"]),
            "trades": int(k["n"]),
        }

        if symbol in self._candles and "1m" in self._candles[symbol]:
            df = self._candles[symbol]["1m"]
            if len(df) > 0:
                ts = pd.Timestamp(k["t"], unit="ms")
                if ts in df.index:
                    for col, val in new_row.items():
                        df.at[ts, col] = val
                else:
                    new_df = pd.DataFrame([new_row], index=[ts])
                    new_df.index.name = "open_time"
                    self._candles[symbol]["1m"] = pd.concat([df, new_df]).tail(500)

        self._prices[symbol] = float(k["c"])

    async def refresh_data(self, symbol: str) -> None:
        """Refresh all data for a symbol (REST fallback)."""
        if self.use_simulation:
            self._simulate_runtime_update(symbol)
            return

        try:
            multi_tf = await self.client.get_multi_timeframe(symbol)
            if multi_tf and any(v is not None for v in multi_tf.values()):
                self._candles[symbol] = multi_tf

            ticker = await self.client.get_ticker_24h(symbol)
            if ticker and ticker.get("lastPrice"):
                self._tickers[symbol] = ticker
                self._prices[symbol] = float(ticker.get("lastPrice", 0))
                self._last_update[symbol] = datetime.utcnow().isoformat()

            order_book = await self.client.get_order_book(symbol)
            if order_book and order_book.get("bids"):
                self._order_books[symbol] = order_book
        except Exception as e:
            if "451" in str(e):
                logger.warning(f"Detection of 451 block for {symbol}. Switching to simulation.")
                self.use_simulation = True
                self._simulate_runtime_update(symbol)
            else:
                logger.error(f"Refresh failed for {symbol}: {e}")

    def _simulate_runtime_update(self, symbol: str) -> None:
        """Create a small price move for simulation."""
        current_price = self._prices.get(symbol, 65000.0 if "BTC" in symbol else 3000.0)
        
        # Every 50 calls, maybe change the trend bias
        if np.random.random() < 0.05:
            # Stronger trend bias to force technical signals (RSI/MACD crossovers)
            self._simulation_trend[symbol] = (np.random.random() - 0.5) * 0.008
            
        bias = self._simulation_trend.get(symbol, 0)
        # Random move +/- 0.05% + trend bias
        noise = (np.random.random() - 0.5) * 0.001
        new_price = current_price * (1 + noise + bias)
        
        self._prices[symbol] = new_price
        
        if symbol in self._tickers:
            self._tickers[symbol]["lastPrice"] = str(new_price)
            self._tickers[symbol]["highPrice"] = str(max(float(self._tickers[symbol]["highPrice"]), new_price))
            self._tickers[symbol]["lowPrice"] = str(min(float(self._tickers[symbol]["lowPrice"]), new_price))
        
        self._last_update[symbol] = datetime.utcnow().isoformat()

        # Update candles (and periodically add new ones to simulate time passing)
        if symbol in self._candles and "1m" in self._candles[symbol]:
            df = self._candles[symbol]["1m"]
            if df is not None and not df.empty:
                # Update current candle
                df.iloc[-1, df.columns.get_loc('close')] = new_price
                df.iloc[-1, df.columns.get_loc('high')] = max(df.iloc[-1]['high'], new_price)
                df.iloc[-1, df.columns.get_loc('low')] = min(df.iloc[-1]['low'], new_price)
                
                # Periodically (roughly every 60 "fast" updates) add a new candle
                if np.random.random() < 0.02:
                    new_idx = df.index[-1] + pd.Timedelta(minutes=1)
                    new_row = df.iloc[-1].copy()
                    new_row.name = new_idx
                    new_row['open'] = new_price
                    # Shift the series
                    self._candles[symbol]["1m"] = pd.concat([df, pd.DataFrame([new_row])]).tail(200)

    def trigger_simulation_update(self) -> None:
        """Trigger update for all symbols if in simulation mode."""
        if self.use_simulation:
            for s in self.symbols:
                self._simulate_runtime_update(s)

    # ── Accessors ──────────────────────────────────────
    def get_candles(self, symbol: str,
                    timeframe: str = "1m") -> Optional[pd.DataFrame]:
        return self._candles.get(symbol, {}).get(timeframe)

    def get_price(self, symbol: str) -> float:
        return self._prices.get(symbol, 0.0)

    def get_ticker(self, symbol: str) -> dict:
        return self._tickers.get(symbol, {})

    def get_order_book(self, symbol: str) -> dict:
        return self._order_books.get(symbol, {})

    def get_all_prices(self) -> dict:
        return dict(self._prices)

    def get_market_summary(self, symbol: str) -> dict:
        """Get a full market summary for a symbol."""
        ticker = self.get_ticker(symbol)
        price = self.get_price(symbol)
        ob = self.get_order_book(symbol)

        return {
            "symbol": symbol,
            "price": price,
            "high_24h": float(ticker.get("highPrice", 0)),
            "low_24h": float(ticker.get("lowPrice", 0)),
            "volume_24h": float(ticker.get("volume", 0)),
            "quote_volume_24h": float(ticker.get("quoteVolume", 0)),
            "order_book_imbalance": ob.get("imbalance", 0),
            "spread": ob.get("spread", 0),
            "last_update": self._last_update.get(symbol, ""),
        }

    async def stop(self) -> None:
        await self.ws_manager.stop()
        await self.client.close()
