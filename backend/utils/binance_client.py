"""
Binance API Client — fetches OHLCV, order book, and ticker data.
Uses multiple API mirrors and a proxy fallback for cloud deployment (Render etc.)
"""
import asyncio
import time
import httpx
import numpy as np
import pandas as pd
import logging
import os
from typing import Optional, Union


from config import BINANCE_BASE_URL, BINANCE_ENDPOINTS

logger = logging.getLogger(__name__)

# ── Proxy Configuration ──────────────────────────────
# If Binance is blocked on the hosting platform, route through a CORS/proxy service.
# Set BINANCE_PROXY_URL env var to use a custom proxy, or leave empty for direct.
# Popular free options:
#   - https://corsproxy.io/?
#   - https://api.allorigins.win/raw?url=
BINANCE_PROXY_URL = os.getenv("BINANCE_PROXY_URL", "")

# If true, all Binance requests go through the proxy
USE_PROXY = os.getenv("USE_BINANCE_PROXY", "false").lower() in ("true", "1", "yes")


def _proxy_url(original_url: str) -> str:
    """Wrap a URL through the configured proxy if enabled."""
    if USE_PROXY and BINANCE_PROXY_URL:
        return f"{BINANCE_PROXY_URL}{original_url}"
    return original_url


class BinanceClient:
    """Async Binance REST client with automatic endpoint failover."""

    def __init__(self):
        # List of base URLs to try in order
        self._endpoints = list(BINANCE_ENDPOINTS)
        self._current_endpoint_idx = 0
        self._http = self._create_client(self._endpoints[0])

    def _create_client(self, base_url: str) -> httpx.AsyncClient:
        """Create an HTTP client — uses proxy if configured."""
        if USE_PROXY and BINANCE_PROXY_URL:
            # When using proxy, we don't set base_url because the full URL
            # is built differently
            return httpx.AsyncClient(
                timeout=20.0,
                headers={"Accept": "application/json"},
                follow_redirects=True,
            )
        return httpx.AsyncClient(
            base_url=base_url,
            timeout=20.0,
            headers={"Accept": "application/json"},
            follow_redirects=True,
        )

    async def _rotate_endpoint(self) -> None:
        """Switch to the next available Binance API endpoint."""
        await self._http.aclose()
        self._current_endpoint_idx = (self._current_endpoint_idx + 1) % len(self._endpoints)
        new_base = self._endpoints[self._current_endpoint_idx]
        logger.info(f"Rotating to Binance endpoint: {new_base}")
        self._http = self._create_client(new_base)

    # ── REST helpers ────────────────────────────────────────
    async def _get(self, path: str, params: dict = None, retries: int = 3) -> Union[dict, list]:
        last_error = None
        # Try each endpoint
        for endpoint_attempt in range(len(self._endpoints)):
            for attempt in range(retries):
                try:
                    if USE_PROXY and BINANCE_PROXY_URL:
                        # Build full URL and proxy it
                        base = self._endpoints[self._current_endpoint_idx]
                        full_url = f"{base}{path}"
                        proxied = _proxy_url(full_url)
                        resp = await self._http.get(proxied, params=params)
                    else:
                        resp = await self._http.get(path, params=params)

                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code == 451:
                        # Geo-blocked, try next endpoint
                        logger.warning(f"Endpoint blocked (451), rotating...")
                        break
                    if e.response.status_code == 429:
                        # Rate limited, wait and retry
                        logger.warning(f"Rate limited, waiting...")
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    if attempt == retries - 1:
                        break
                    await asyncio.sleep(1)
                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                    last_error = e
                    logger.warning(f"Connection error: {e}, attempt {attempt+1}/{retries}")
                    if attempt == retries - 1:
                        break
                    await asyncio.sleep(1.5 * (attempt + 1))
                except Exception as e:
                    last_error = e
                    if attempt == retries - 1:
                        break
                    await asyncio.sleep(1)

            # Try next endpoint
            await self._rotate_endpoint()

        raise last_error or Exception("All Binance endpoints failed")

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
                logger.error(f"Failed to get {symbol} {tf}: {result}")
                data[tf] = None
            else:
                data[tf] = result

        return data

    async def close(self):
        await self._http.aclose()
