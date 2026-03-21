"""
WebSocket Manager — handles real-time price streaming from Binance.
Supports REST polling fallback when WebSocket connections are blocked (Render, Railway, etc.)
"""
import json
import asyncio
import logging
import os
from typing import Callable, Optional, Set

logger = logging.getLogger(__name__)

BINANCE_WS_BASE = "wss://stream.binance.com:9443/ws"

# ── Deployment Mode ──────────────────────────────────
# When running on platforms that block outbound WebSocket to Binance (like Render),
# enable REST polling mode which fetches data via the REST API instead.
USE_REST_POLLING = os.getenv("USE_REST_POLLING", "false").lower() in ("true", "1", "yes")
REST_POLL_INTERVAL = float(os.getenv("REST_POLL_INTERVAL", "3"))  # seconds


class WebSocketManager:
    """
    Manages Binance data streams — either via WebSocket (for local/VPS)
    or REST polling (for cloud platforms that block WS).
    """

    def __init__(self):
        self._connections: dict = {}
        self._callbacks: dict = {}
        self._running = False
        self._tasks: list = []
        self._use_rest = USE_REST_POLLING
        self._rest_subscriptions: list = []  # [(symbol, type, interval, callback)]

    async def subscribe_ticker(self, symbol: str,
                                callback: Callable) -> None:
        """Subscribe to real-time mini-ticker for a symbol."""
        if self._use_rest:
            self._rest_subscriptions.append((symbol, "ticker", None, callback))
            return

        stream = f"{symbol.lower()}@miniTicker"
        self._callbacks[stream] = callback
        if self._running:
            task = asyncio.create_task(self._listen(stream))
            self._tasks.append(task)

    async def subscribe_kline(self, symbol: str, interval: str,
                               callback: Callable) -> None:
        """Subscribe to kline/candle stream."""
        if self._use_rest:
            self._rest_subscriptions.append((symbol, "kline", interval, callback))
            return

        stream = f"{symbol.lower()}@kline_{interval}"
        self._callbacks[stream] = callback
        if self._running:
            task = asyncio.create_task(self._listen(stream))
            self._tasks.append(task)

    async def subscribe_depth(self, symbol: str,
                               callback: Callable) -> None:
        """Subscribe to order book depth stream."""
        if self._use_rest:
            self._rest_subscriptions.append((symbol, "depth", None, callback))
            return

        stream = f"{symbol.lower()}@depth20@100ms"
        self._callbacks[stream] = callback
        if self._running:
            task = asyncio.create_task(self._listen(stream))
            self._tasks.append(task)

    async def _listen(self, stream: str) -> None:
        """Connect and listen to a single Binance WebSocket stream."""
        import websockets
        url = f"{BINANCE_WS_BASE}/{stream}"
        while self._running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    self._connections[stream] = ws
                    logger.info(f"Connected to stream: {stream}")

                    async for message in ws:
                        if not self._running:
                            break
                        try:
                            data = json.loads(message)
                            callback = self._callbacks.get(stream)
                            if callback:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                        except Exception as e:
                            logger.error(f"Callback error for {stream}: {e}")

            except Exception as e:
                if not self._running:
                    break
                logger.warning(f"WebSocket error for {stream}: {e}, reconnecting...")
                await asyncio.sleep(5)

    async def _rest_poll_loop(self) -> None:
        """
        REST polling fallback — fetches ticker and kline data via REST API
        to simulate real-time streaming when WebSockets are blocked.
        """
        import httpx
        from config import BINANCE_BASE_URL, BINANCE_ENDPOINTS

        # Group subscriptions by symbol
        ticker_subs = {}
        kline_subs = {}
        for symbol, sub_type, interval, callback in self._rest_subscriptions:
            if sub_type == "ticker":
                ticker_subs[symbol] = callback
            elif sub_type == "kline":
                if symbol not in kline_subs:
                    kline_subs[symbol] = []
                kline_subs[symbol].append((interval, callback))

        endpoints = list(BINANCE_ENDPOINTS)
        current_ep = 0

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            while self._running:
                try:
                    base = endpoints[current_ep]

                    # Poll tickers
                    for symbol, callback in ticker_subs.items():
                        try:
                            resp = await client.get(
                                f"{base}/api/v3/ticker/24hr",
                                params={"symbol": symbol}
                            )
                            if resp.status_code == 451:
                                # Blocked, rotate endpoint
                                current_ep = (current_ep + 1) % len(endpoints)
                                logger.warning(f"Endpoint blocked, rotating to {endpoints[current_ep]}")
                                break
                            if resp.status_code == 200:
                                data = resp.json()
                                # Convert REST response to mini-ticker format
                                ticker_data = {
                                    "c": data.get("lastPrice", "0"),
                                    "h": data.get("highPrice", "0"),
                                    "l": data.get("lowPrice", "0"),
                                    "v": data.get("volume", "0"),
                                    "q": data.get("quoteVolume", "0"),
                                }
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(ticker_data)
                                else:
                                    callback(ticker_data)
                        except Exception as e:
                            logger.error(f"REST poll ticker {symbol}: {e}")

                    # Poll klines
                    for symbol, sub_list in kline_subs.items():
                        for interval, callback in sub_list:
                            try:
                                resp = await client.get(
                                    f"{base}/api/v3/klines",
                                    params={"symbol": symbol, "interval": interval, "limit": 2}
                                )
                                if resp.status_code == 451:
                                    current_ep = (current_ep + 1) % len(endpoints)
                                    break
                                if resp.status_code == 200:
                                    klines = resp.json()
                                    if klines:
                                        latest = klines[-1]
                                        # Convert to kline WS format
                                        kline_data = {
                                            "k": {
                                                "t": latest[0],     # open time
                                                "o": latest[1],     # open
                                                "h": latest[2],     # high
                                                "l": latest[3],     # low
                                                "c": latest[4],     # close
                                                "v": latest[5],     # volume
                                                "q": latest[7],     # quote volume
                                                "n": latest[8],     # number of trades
                                            }
                                        }
                                        if asyncio.iscoroutinefunction(callback):
                                            await callback(kline_data)
                                        else:
                                            callback(kline_data)
                            except Exception as e:
                                logger.error(f"REST poll kline {symbol}/{interval}: {e}")

                    await asyncio.sleep(REST_POLL_INTERVAL)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"REST poll loop error: {e}")
                    await asyncio.sleep(5)

    async def start(self) -> None:
        """Start all subscribed streams (WebSocket or REST polling)."""
        self._running = True

        if self._use_rest:
            logger.info(f"Starting REST polling mode ({REST_POLL_INTERVAL}s interval) "
                        f"with {len(self._rest_subscriptions)} subscriptions")
            task = asyncio.create_task(self._rest_poll_loop())
            self._tasks.append(task)
        else:
            for stream in self._callbacks:
                task = asyncio.create_task(self._listen(stream))
                self._tasks.append(task)
            logger.info(f"WebSocket manager started with {len(self._callbacks)} streams")

    async def stop(self) -> None:
        """Stop all streams."""
        self._running = False
        for ws in self._connections.values():
            try:
                await ws.close()
            except Exception:
                pass
        for task in self._tasks:
            task.cancel()
        self._connections.clear()
        self._tasks.clear()
        logger.info("WebSocket manager stopped")
