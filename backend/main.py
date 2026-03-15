"""
SmartPre — AI Crypto Trading Agent
FastAPI Backend Server
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ─── Path Resolution ────────────────────────────────
# Works both locally (from backend/) and on Render (from repo root cd backend)
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

from config import DEFAULT_SYMBOLS, SERVER_HOST, SERVER_PORT
from agents.data_agent import DataAgent
from agents.technical_agent import TechnicalAgent
from agents.sentiment_agent import SentimentAgent
from agents.prediction_agent import PredictionAgent
from agents.signal_agent import SignalAgent
from agents.risk_agent import RiskAgent
from agents.decision_agent import DecisionAgent

# ─── Logging ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("smartpre")

# ─── Agents ─────────────────────────────────────────
data_agent = DataAgent(symbols=DEFAULT_SYMBOLS)
technical_agent = TechnicalAgent()
sentiment_agent = SentimentAgent()
prediction_agent = PredictionAgent()
signal_agent = SignalAgent()
risk_agent = RiskAgent()
decision_agent = DecisionAgent()

# ─── Connected WS clients ────────────────────────────
ws_clients: set = set()
analysis_loop_task: Optional[asyncio.Task] = None


# ─── Analysis Pipeline ───────────────────────────────
async def run_analysis_pipeline(symbol: str) -> dict:
    """
    Execute the full agent pipeline for a single symbol.
    
    Step 1: Refresh market data
    Step 2: Run technical analysis
    Step 3: Analyze sentiment
    Step 4: Run ML prediction
    Step 5: Generate trading signal
    Step 6: Evaluate risk
    Step 7: Final decision
    """
    logger.info(f"Running analysis pipeline for {symbol}...")

    try:
        # Step 1: Data
        await data_agent.refresh_data(symbol)
        candles = data_agent.get_candles(symbol, "1m")
        price = data_agent.get_price(symbol)

        if candles is None or len(candles) == 0 or price <= 0:
            logger.warning(f"No data available for {symbol}")
            return {"symbol": symbol, "error": "No data available"}

        # Step 2: Technical Analysis
        try:
            ta = technical_agent.analyze(candles, symbol)
        except Exception as e:
            logger.error(f"Technical analysis failed for {symbol}: {e}")
            ta = technical_agent._empty_analysis(symbol)

        # Step 3: Sentiment
        try:
            sa = await sentiment_agent.analyze_sentiment(symbol)
        except Exception as e:
            logger.error(f"Sentiment analysis failed for {symbol}: {e}")
            sa = {"sentiment": "NEUTRAL", "composite_score": 0.0, "fear_greed": {}}

        # Step 4: ML Prediction
        try:
            indicator_data = technical_agent.get_indicator_data_for_ml(candles)
            pred = prediction_agent.predict(indicator_data, symbol)
        except Exception as e:
            logger.error(f"Prediction failed for {symbol}: {e}")
            pred = prediction_agent._empty_prediction(symbol)

        # Step 5: Trading Signal
        try:
            sig = signal_agent.generate_signal(symbol, price, ta, pred, sa)
        except Exception as e:
            logger.error(f"Signal generation failed for {symbol}: {e}")
            sig = signal_agent._empty_signal(symbol)

        # Step 6: Risk
        try:
            risk = risk_agent.evaluate_risk(sig, ta)
        except Exception as e:
            logger.error(f"Risk evaluation failed for {symbol}: {e}")
            risk = {"risk_level": "UNKNOWN", "should_trade": False, "warnings": [str(e)]}

        # Step 7: Final Decision
        try:
            decision = decision_agent.decide(symbol, sig, risk, pred, sa, ta)
        except Exception as e:
            logger.error(f"Decision engine failed for {symbol}: {e}")
            decision = {
                "symbol": symbol,
                "action": "HOLD",
                "confidence": 0.5,
                "confidence_pct": 50.0,
                "reason": f"Decision error: {str(e)}",
                "price": price,
            }

        logger.info(
            f"{symbol}: {decision.get('action', 'N/A')} | "
            f"Confidence: {decision.get('confidence_pct', 0)}% | "
            f"Price: {price}"
        )

        return decision

    except Exception as e:
        logger.error(f"Pipeline critical error for {symbol}: {e}", exc_info=True)
        return {"symbol": symbol, "error": str(e), "action": "HOLD", "confidence_pct": 50.0}


async def analysis_loop():
    """Continuous analysis loop for all symbols."""
    global ws_clients
    while True:
        try:
            results = {}
            for symbol in DEFAULT_SYMBOLS:
                try:
                    result = await run_analysis_pipeline(symbol)
                    results[symbol] = result
                except Exception as e:
                    logger.error(f"Pipeline error for {symbol}: {e}")
                    results[symbol] = {"symbol": symbol, "error": str(e)}

            # Broadcast to all WebSocket clients
            if ws_clients:
                payload = json.dumps({
                    "type": "analysis_update",
                    "data": results,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                disconnected = set()
                for ws in ws_clients:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        disconnected.add(ws)
                ws_clients.difference_update(disconnected)

            # Wait before next cycle (5 seconds)
            await asyncio.sleep(5)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Analysis loop error: {e}")
            await asyncio.sleep(10)


async def price_update_loop():
    """Fast loop for price updates (every 2 seconds)."""
    global ws_clients
    while True:
        try:
            if ws_clients:
                prices = data_agent.get_all_prices()
                payload = json.dumps({
                    "type": "price_update",
                    "data": prices,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                
                # Check if prices actually changed to avoid redundant sends
                # (Optional optimization, but let's keep it simple for now)
                
                disconnected = set()
                for ws in ws_clients:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        disconnected.add(ws)
                ws_clients.difference_update(disconnected)
            
            await asyncio.sleep(1.0)  # Update every 1 second for real-time feel
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Price update loop error: {e}")
            await asyncio.sleep(5)


# ─── App Lifecycle ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global analysis_loop_task
    logger.info("🚀 SmartPre AI Agent starting...")

    # Initialize data agent
    await data_agent.initialize()
    
    # Start data streaming
    await data_agent.start_streaming()

    # Start analysis loop
    analysis_loop_task = asyncio.create_task(analysis_loop())
    
    # Start fast price update loop
    price_update_task = asyncio.create_task(price_update_loop())
    
    logger.info("✅ Analysis pipeline and real-time streaming running")

    yield

    # Shutdown
    logger.info("Shutting down SmartPre...")
    if analysis_loop_task:
        analysis_loop_task.cancel()
    if 'price_update_task' in locals():
        price_update_task.cancel()
    await data_agent.stop()
    await sentiment_agent.close()


# ─── FastAPI App ─────────────────────────────────────
app = FastAPI(
    title="SmartPre AI Crypto Agent",
    description="AI-powered cryptocurrency trading analysis and prediction system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend (using absolute path for reliability on Render)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ─── REST Endpoints ──────────────────────────────────
@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/symbols")
async def get_symbols():
    """Get list of tracked symbols."""
    return {"symbols": DEFAULT_SYMBOLS}


@app.get("/api/prices")
async def get_all_prices():
    """Get current prices for all symbols."""
    return data_agent.get_all_prices()


@app.get("/api/klines/{symbol}")
async def get_klines(symbol: str, timeframe: str = "1m"):
    """Get candlestick data for a symbol."""
    symbol = symbol.upper()
    
    # Try to get existing candles
    df = data_agent.get_candles(symbol, timeframe)
    
    # If no cached data for this timeframe, try fetching fresh
    if df is None or (hasattr(df, 'empty') and df.empty):
        try:
            await data_agent.refresh_data(symbol)
            df = data_agent.get_candles(symbol, timeframe)
        except Exception as e:
            logger.error(f"Failed to fetch klines for {symbol}/{timeframe}: {e}")
    
    if df is None or (hasattr(df, 'empty') and df.empty):
        return []
    
    candles = []
    for ts, row in df.iterrows():
        try:
            candles.append({
                "time": int(ts.value // 10**9),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"])
            })
        except (ValueError, KeyError) as e:
            logger.warning(f"Bad candle data at {ts}: {e}")
            continue
    
    return candles


@app.get("/api/analysis/{symbol}")
async def get_analysis(symbol: str):
    """Get full analysis for a symbol."""
    symbol = symbol.upper()
    decision = decision_agent.get_decision(symbol)
    if decision.get("action"):
        return decision

    # Run fresh analysis if none cached
    result = await run_analysis_pipeline(symbol)
    return result


@app.get("/api/technical/{symbol}")
async def get_technical(symbol: str):
    """Get technical analysis for a symbol."""
    symbol = symbol.upper()
    ta = technical_agent.get_last_analysis(symbol)
    if ta.get("price", 0) > 0:
        return ta
    # Run fresh if needed
    candles = data_agent.get_candles(symbol, "1m")
    if candles is not None:
        return technical_agent.analyze(candles, symbol)
    return {"error": "No data available"}


@app.get("/api/prediction/{symbol}")
async def get_prediction(symbol: str):
    """Get ML prediction for a symbol."""
    symbol = symbol.upper()
    return prediction_agent.get_prediction(symbol)


@app.get("/api/sentiment/{symbol}")
async def get_sentiment(symbol: str):
    """Get sentiment analysis for a symbol."""
    symbol = symbol.upper()
    cached = sentiment_agent.get_cached_sentiment(symbol)
    if cached.get("composite_score", 0) != 0:
        return cached
    return await sentiment_agent.analyze_sentiment(symbol)


@app.get("/api/signal/{symbol}")
async def get_signal(symbol: str):
    """Get trading signal for a symbol."""
    symbol = symbol.upper()
    return signal_agent.get_signal(symbol)


@app.get("/api/market/{symbol}")
async def get_market_summary(symbol: str):
    """Get market data summary."""
    symbol = symbol.upper()
    return data_agent.get_market_summary(symbol)


@app.get("/api/decisions")
async def get_all_decisions():
    """Get all current decisions."""
    return decision_agent.get_all_decisions()


@app.post("/api/analyze/{symbol}")
async def trigger_analysis(symbol: str):
    """Manually trigger analysis for a symbol."""
    symbol = symbol.upper()
    result = await run_analysis_pipeline(symbol)
    return result


# ─── WebSocket ───────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    ws_clients.add(websocket)
    logger.info(f"WebSocket client connected. Total: {len(ws_clients)}")

    try:
        # Send initial data
        decisions = decision_agent.get_all_decisions()
        prices = data_agent.get_all_prices()

        await websocket.send_text(json.dumps({
            "type": "initial_data",
            "data": {
                "decisions": decisions,
                "prices": prices,
                "symbols": DEFAULT_SYMBOLS,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }))

        # Keep alive and handle messages
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif msg.get("type") == "analyze":
                symbol = msg.get("symbol", "BTCUSDT").upper()
                result = await run_analysis_pipeline(symbol)
                await websocket.send_text(json.dumps({
                    "type": "analysis_result",
                    "data": {symbol: result},
                    "timestamp": datetime.utcnow().isoformat(),
                }))

    except WebSocketDisconnect:
        ws_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(ws_clients)}")
    except Exception as e:
        ws_clients.discard(websocket)
        logger.error(f"WebSocket error: {e}")


# ─── Run ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    is_production = os.getenv("RENDER", "") != "" or os.getenv("PORT", "") != ""
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=not is_production,  # Disable reload in production
        log_level="info",
    )
