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

    async def initialize(self) -> None:
        """Load initial historical data for all symbols."""
        logger.info("Initializing Data Agent...")

        for symbol in self.symbols:
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

    async def start_streaming(self) -> None:
        """Start WebSocket streams for all symbols."""
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
        try:
            multi_tf = await self.client.get_multi_timeframe(symbol)
            self._candles[symbol] = multi_tf

            ticker = await self.client.get_ticker_24h(symbol)
            self._tickers[symbol] = ticker

            order_book = await self.client.get_order_book(symbol)
            self._order_books[symbol] = order_book

            self._prices[symbol] = float(ticker.get("lastPrice", 0))
            self._last_update[symbol] = datetime.utcnow().isoformat()
        except Exception as e:
            logger.error(f"Refresh failed for {symbol}: {e}")

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
