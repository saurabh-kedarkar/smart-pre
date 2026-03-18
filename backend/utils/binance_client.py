"""
Binance API Client — fetches OHLCV, order book, and ticker data.
"""
import asyncio
import time
import httpx
import numpy as np
import pandas as pd
from typing import Optional, Union


from config import BINANCE_BASE_URL

class BinanceClient:
    """Async Binance REST + WebSocket client."""

    def __init__(self):
        self._http = httpx.AsyncClient(
            base_url=BINANCE_BASE_URL,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )

    # ── REST helpers ────────────────────────────────────────
    async def _get(self, path: str, params: dict = None, retries: int = 3) -> Union[dict, list]:
        for attempt in range(retries):
            try:
                resp = await self._http.get(path, params=params)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(1) # Wait before retry

    # ── Public endpoints ────────────────────────────────────
    async def get_klines(self, symbol: str, interval: str = "1m",
                         limit: int = 200) -> pd.DataFrame:
        """
        Fetch OHLCV candlestick data.
        """
        raw = await self._get("/api/v3/klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        })

        df = pd.DataFrame(raw, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ])

        for col in ["open", "high", "low", "close", "volume", "quote_vol"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
        df.set_index("open_time", inplace=True)

        return df[["open", "high", "low", "close", "volume", "quote_vol", "trades"]]

    async def get_ticker_24h(self, symbol: str) -> dict:
        """Get 24hr ticker statistics."""
        return await self._get("/api/v3/ticker/24hr", {"symbol": symbol})

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        """Fetch order book depth."""
        raw = await self._get("/api/v3/depth", {
            "symbol": symbol,
            "limit": limit,
        })

        bids = [[float(p), float(q)] for p, q in raw.get("bids", [])]
        asks = [[float(p), float(q)] for p, q in raw.get("asks", [])]

        bid_total = sum(q for _, q in bids)
        ask_total = sum(q for _, q in asks)
        imbalance = (bid_total - ask_total) / (bid_total + ask_total) if (bid_total + ask_total) > 0 else 0

        return {
            "bids": bids,
            "asks": asks,
            "bid_total": bid_total,
            "ask_total": ask_total,
            "imbalance": round(imbalance, 4),
            "spread": round(asks[0][0] - bids[0][0], 8) if bids and asks else 0,
        }

    async def get_recent_trades(self, symbol: str, limit: int = 50) -> list:
        """Get recent trades."""
        return await self._get("/api/v3/trades", {
            "symbol": symbol,
            "limit": limit,
        })

    async def get_ticker_price(self, symbol: str) -> float:
        """Get current price."""
        data = await self._get("/api/v3/ticker/price", {"symbol": symbol})
        return float(data["price"])

    async def get_all_tickers(self) -> dict:
        """Get all current prices."""
        data = await self._get("/api/v3/ticker/price")
        return {item["symbol"]: float(item["price"]) for item in data}

    # ── Multi-timeframe fetch ───────────────────────────────
    async def get_multi_timeframe(self, symbol: str,
                                   timeframes: list = None,
                                   limit: int = 200) -> dict:
        """
        Fetch candle data for multiple timeframes concurrently.
        """
        if timeframes is None:
            timeframes = ["1m", "5m", "15m", "1h"]

        tasks = [self.get_klines(symbol, tf, limit) for tf in timeframes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for tf, result in zip(timeframes, results):
            if isinstance(result, Exception):
                data[tf] = None
            else:
                data[tf] = result

        return data

    async def close(self):
        await self._http.aclose()
