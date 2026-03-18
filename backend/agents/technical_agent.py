"""
Technical Analysis Agent — runs all indicators and produces composite signals.
"""
import logging
import pandas as pd
import numpy as np
from typing import Optional

from indicators.rsi import compute_rsi, rsi_signal, rsi_divergence
from indicators.macd import compute_macd, macd_signal
from indicators.bollinger import compute_bollinger_bands, bollinger_signal
from indicators.moving_averages import compute_all_moving_averages, ma_signal
from indicators.vwap import compute_vwap, vwap_signal
from indicators.fibonacci import compute_fibonacci_levels, fibonacci_signal
from indicators.volume_profile import compute_volume_profile, volume_signal

logger = logging.getLogger(__name__)


class TechnicalAgent:
    """
    Runs all technical indicators on OHLCV data and produces
    a composite technical analysis report.
    """

    def __init__(self):
        self._last_analysis: dict = {}

    def analyze(self, df: pd.DataFrame, symbol: str = "") -> dict:
        """
        Run full technical analysis on an OHLCV DataFrame.
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
            symbol: symbol name for logging
        
        Returns:
            Comprehensive analysis dict with all indicator results
        """
        if df is None or len(df) < 30:
            return self._empty_analysis(symbol)

        closes = df["close"]
        highs = df["high"]
        lows = df["low"]
        opens = df["open"]
        volumes = df["volume"]
        current_price = closes.iloc[-1]

        # ── RSI ─────────────────────────────────────────
        rsi_values = compute_rsi(closes)
        rsi_curr = rsi_values.iloc[-1]
        rsi_sig = rsi_signal(rsi_curr)
        rsi_div = rsi_divergence(closes, rsi_values)

        # ── MACD ────────────────────────────────────────
        macd_data = compute_macd(closes)
        macd_sig = macd_signal(macd_data)

        # ── Bollinger Bands ─────────────────────────────
        bb_data = compute_bollinger_bands(closes)
        bb_sig = bollinger_signal(bb_data, current_price)

        # ── Moving Averages ─────────────────────────────
        ma_data = compute_all_moving_averages(closes)
        ma_sig = ma_signal(closes, ma_data)

        # ── VWAP ────────────────────────────────────────
        vwap_values = compute_vwap(highs, lows, closes, volumes)
        vwap_curr = vwap_values.iloc[-1]
        vwap_sig = vwap_signal(current_price, vwap_curr)

        # ── Fibonacci ───────────────────────────────────
        fib_data = compute_fibonacci_levels(highs, lows)
        fib_sig = fibonacci_signal(current_price, fib_data)

        # ── Volume Profile ──────────────────────────────
        vol_profile = compute_volume_profile(closes, volumes)
        avg_vol = volumes.tail(20).mean()
        vol_sig = volume_signal(current_price, vol_profile, volumes.iloc[-1], avg_vol)

        # ── Composite Score ─────────────────────────────
        signals = [rsi_sig, macd_sig, bb_sig, ma_sig, vwap_sig, fib_sig, vol_sig]
        weights = [0.20, 0.20, 0.15, 0.15, 0.10, 0.10, 0.10]

        composite_strength = sum(
            s.get("strength", 0) * w for s, w in zip(signals, weights)
        )

        if composite_strength > 0.3:
            overall = "BULLISH"
        elif composite_strength > 0.1:
            overall = "SLIGHTLY_BULLISH"
        elif composite_strength > -0.1:
            overall = "NEUTRAL"
        elif composite_strength > -0.3:
            overall = "SLIGHTLY_BEARISH"
        else:
            overall = "BEARISH"

        # ── Market Structure ────────────────────────────
        structure = self._detect_market_structure(closes, highs, lows)

        # ── Volatility ──────────────────────────────────
        returns = closes.pct_change().dropna()
        volatility = float(returns.tail(20).std() * 100)

        analysis = {
            "symbol": symbol,
            "price": float(current_price),
            "overall_signal": overall,
            "composite_strength": round(float(composite_strength), 4),
            "volatility": round(volatility, 4),
            "market_structure": structure,
            "indicators": {
                "rsi": {
                    "value": round(float(rsi_curr), 2),
                    **rsi_sig,
                    "divergence": rsi_div,
                },
                "macd": {
                    "macd_line": round(float(macd_data["macd_line"].iloc[-1]), 6),
                    "signal_line": round(float(macd_data["signal_line"].iloc[-1]), 6),
                    "histogram": round(float(macd_data["histogram"].iloc[-1]), 6),
                    **macd_sig,
                },
                "bollinger_bands": {
                    "upper": round(float(bb_data["upper"].iloc[-1]), 2),
                    "middle": round(float(bb_data["middle"].iloc[-1]), 2),
                    "lower": round(float(bb_data["lower"].iloc[-1]), 2),
                    **bb_sig,
                },
                "moving_averages": ma_sig,
                "vwap": vwap_sig,
                "fibonacci": fib_sig,
                "volume": vol_sig,
            },
        }

        self._last_analysis[symbol] = analysis
        return analysis

    def _detect_market_structure(self, closes: pd.Series,
                                  highs: pd.Series,
                                  lows: pd.Series) -> dict:
        """Detect market structure (trend, consolidation, breakout)."""
        if len(closes) < 20:
            return {"trend": "UNKNOWN", "type": "UNKNOWN"}

        # Simple trend detection using recent highs and lows
        recent = closes.tail(20)
        mid = closes.tail(40).head(20) if len(closes) >= 40 else recent

        recent_high = highs.tail(20).max()
        recent_low = lows.tail(20).min()
        range_pct = ((recent_high - recent_low) / recent_low) * 100

        slope = np.polyfit(range(len(recent)), recent.values, 1)[0]
        norm_slope = slope / recent.mean() * 100

        if range_pct < 1.0:
            structure_type = "CONSOLIDATION"
        elif abs(norm_slope) > 0.05:
            structure_type = "TRENDING"
        else:
            structure_type = "RANGING"

        # Breakout detection
        is_breakout = False
        if len(closes) >= 50:
            prev_high = highs.iloc[-50:-20].max()
            prev_low = lows.iloc[-50:-20].min()
            if closes.iloc[-1] > prev_high:
                is_breakout = True
                structure_type = "BREAKOUT_UP"
            elif closes.iloc[-1] < prev_low:
                is_breakout = True
                structure_type = "BREAKOUT_DOWN"

        trend = "UP" if norm_slope > 0 else "DOWN" if norm_slope < 0 else "FLAT"

        return {
            "trend": trend,
            "type": structure_type,
            "slope": round(float(norm_slope), 4),
            "range_pct": round(float(range_pct), 2),
            "is_breakout": is_breakout,
        }

    def _empty_analysis(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "price": 0,
            "overall_signal": "NEUTRAL",
            "composite_strength": 0.0,
            "volatility": 0.0,
            "market_structure": {"trend": "UNKNOWN", "type": "UNKNOWN"},
            "indicators": {},
        }

    def get_last_analysis(self, symbol: str) -> dict:
        return self._last_analysis.get(symbol, self._empty_analysis(symbol))

    def get_indicator_data_for_ml(self, df: pd.DataFrame) -> dict:
        """
        Extract indicator values as arrays for ML model input.
        """
        if df is None or len(df) < 30:
            return {}

        closes = df["close"]
        highs = df["high"]
        lows = df["low"]
        volumes = df["volume"]

        rsi_values = compute_rsi(closes)
        macd_data = compute_macd(closes)
        bb_data = compute_bollinger_bands(closes)
        from indicators.moving_averages import compute_ema
        ema_9 = compute_ema(closes, 9)
        vwap_values = compute_vwap(highs, lows, closes, volumes)

        return {
            "open": df["open"].values.tolist(),
            "high": highs.values.tolist(),
            "low": lows.values.tolist(),
            "close": closes.values.tolist(),
            "volume": volumes.values.tolist(),
            "rsi": rsi_values.values.tolist(),
            "macd": macd_data["macd_line"].values.tolist(),
            "macd_signal": macd_data["signal_line"].values.tolist(),
            "bb_upper": bb_data["upper"].values.tolist(),
            "bb_lower": bb_data["lower"].values.tolist(),
            "ema_9": ema_9.values.tolist(),
            "vwap": vwap_values.values.tolist(),
        }
