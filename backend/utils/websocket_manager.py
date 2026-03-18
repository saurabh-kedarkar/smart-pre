"""
WebSocket Manager — handles real-time price streaming from Binance.
"""
import json
import asyncio
import logging
from typing import Callable, Optional, Set

import websockets

logger = logging.getLogger(__name__)

# Use binance.us to bypass US cloud provider geo-blocks
BINANCE_WS_BASE = "wss://stream.binance.us:9443/ws"


class WebSocketManager:
    """
    Manages Binance WebSocket streams for real-time data.
    """

    def __init__(self):
        self._connections: dict = {}
        self._callbacks: dict = {}
        self._running = False
        self._tasks: list = []

    async def subscribe_ticker(self, symbol: str,
                                callback: Callable) -> None:
        """Subscribe to real-time mini-ticker for a symbol."""
        stream = f"{symbol.lower()}@miniTicker"
        self._callbacks[stream] = callback
        if self._running:
            task = asyncio.create_task(self._listen(stream))
            self._tasks.append(task)

    async def subscribe_kline(self, symbol: str, interval: str,
                               callback: Callable) -> None:
        """Subscribe to kline/candle stream."""
        stream = f"{symbol.lower()}@kline_{interval}"
        self._callbacks[stream] = callback
        if self._running:
            task = asyncio.create_task(self._listen(stream))
            self._tasks.append(task)

    async def subscribe_depth(self, symbol: str,
                               callback: Callable) -> None:
        """Subscribe to order book depth stream."""
        stream = f"{symbol.lower()}@depth20@100ms"
        self._callbacks[stream] = callback
        if self._running:
            task = asyncio.create_task(self._listen(stream))
            self._tasks.append(task)

    async def _listen(self, stream: str) -> None:
        """Connect and listen to a single stream."""
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

            except websockets.ConnectionClosed:
                logger.warning(f"Connection closed for {stream}, reconnecting...")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"WebSocket error for {stream}: {e}")
                await asyncio.sleep(5)

    async def start(self) -> None:
        """Start all subscribed streams."""
        self._running = True
        for stream in self._callbacks:
            task = asyncio.create_task(self._listen(stream))
            self._tasks.append(task)
        logger.info(f"WebSocket manager started with {len(self._callbacks)} streams")

    async def stop(self) -> None:
        """Stop all streams."""
        self._running = False
        for ws in self._connections.values():
            await ws.close()
        for task in self._tasks:
            task.cancel()
        self._connections.clear()
        self._tasks.clear()
        logger.info("WebSocket manager stopped")
