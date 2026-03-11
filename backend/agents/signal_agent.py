"""
Signal Agent — generates actionable trading signals with entry, targets, and stop loss.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SignalAgent:
    """
    Generates trading signals based on technical analysis,
    ML predictions, and sentiment data.
    """

    def __init__(self):
        self._signals: dict = {}

    def generate_signal(self, symbol: str, price: float,
                        technical: dict, prediction: dict,
                        sentiment: dict) -> dict:
        """
        Generate a trading signal from all analysis inputs.
        
        Args:
            symbol: trading pair
            price: current price
            technical: output from TechnicalAgent
            prediction: output from PredictionAgent
            sentiment: output from SentimentAgent
        
        Returns:
            Complete trading signal with entry, targets, stop loss
        """
        if price <= 0:
            return self._empty_signal(symbol)

        # ── Composite scoring ───────────────────────────
        tech_strength = technical.get("composite_strength", 0)
        pred_direction = prediction.get("direction", "NEUTRAL")
        pred_confidence = prediction.get("confidence", 0.5)
        sent_score = sentiment.get("composite_score", 0)

        # Weights: Technical 45%, ML 40%, Sentiment 15%
        tech_score = tech_strength        # ranges -1 to 1
        ml_score = (pred_confidence - 0.5) * 2 if pred_direction == "BULLISH" else -(pred_confidence - 0.5) * 2
        sent_score_norm = sent_score      # already -1 to 1

        composite = (
            tech_score * 0.45 +
            ml_score * 0.40 +
            sent_score_norm * 0.15
        )

        # ── Signal determination ─────────────────────────
        if composite > 0.45:
            signal_type = "BUY"
        elif composite > 0.20:
            signal_type = "WEAK_BUY"
        elif composite > -0.20:
            signal_type = "HOLD"
        elif composite > -0.45:
            signal_type = "WEAK_SELL"
        else:
            signal_type = "SELL"

        # ── Calculate confidence ─────────────────────────
        confidence = min(0.98, 0.50 + abs(composite) * 0.6)

        # ── Entry, targets, stop loss ────────────────────
        # Use volatility (std dev) to scale targets
        # Default volatility around 0.1 - 0.5% for 1m returns
        volatility = technical.get("volatility", 0.3)
        vol_factor = max(0.4, min(2.5, volatility / 0.3))

        if signal_type in ("BUY", "WEAK_BUY"):
            entry = price
            # Stricter Stop Loss, Wider Targets for better R:R
            stop_loss = price * (1 - 0.004 * vol_factor)
            target_1 = price * (1 + 0.006 * vol_factor)
            target_2 = price * (1 + 0.012 * vol_factor)
            target_3 = price * (1 + 0.025 * vol_factor)
        elif signal_type in ("SELL", "WEAK_SELL"):
            entry = price
            stop_loss = price * (1 + 0.004 * vol_factor)
            target_1 = price * (1 - 0.006 * vol_factor)
            target_2 = price * (1 - 0.012 * vol_factor)
            target_3 = price * (1 - 0.025 * vol_factor)
        else:
            entry = price
            stop_loss = price * (1 - 0.003 * vol_factor)
            target_1 = price * (1 + 0.005 * vol_factor)
            target_2 = price * (1 + 0.010 * vol_factor)
            target_3 = price * (1 + 0.018 * vol_factor)

        # ── Risk/Reward ratio ────────────────────────────
        risk = abs(entry - stop_loss)
        reward = abs(target_1 - entry)
        rr_ratio = reward / risk if risk > 0 else 0

        # ── Fibonacci-informed levels ────────────────────
        fib = technical.get("indicators", {}).get("fibonacci", {})
        support = fib.get("nearest_support", {})
        resistance = fib.get("nearest_resistance", {})

        result = {
            "symbol": symbol,
            "signal": signal_type,
            "entry_price": round(entry, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
            "target_3": round(target_3, 2),
            "stop_loss": round(stop_loss, 2),
            "confidence": round(confidence, 4),
            "confidence_pct": round(confidence * 100, 1),
            "risk_reward_ratio": round(rr_ratio, 2),
            "composite_score": round(composite, 4),
            "breakdown": {
                "technical_score": round(tech_score, 4),
                "ml_score": round(ml_score, 4),
                "sentiment_score": round(sent_score_norm, 4),
            },
            "levels": {
                "support": support.get("level") if support else None,
                "resistance": resistance.get("level") if resistance else None,
            },
        }

        self._signals[symbol] = result
        return result

    def _empty_signal(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "signal": "HOLD",
            "entry_price": 0,
            "target_1": 0,
            "target_2": 0,
            "stop_loss": 0,
            "confidence": 0.50,
            "confidence_pct": 50.0,
            "risk_reward_ratio": 0,
            "composite_score": 0,
        }

    def get_signal(self, symbol: str) -> dict:
        return self._signals.get(symbol, self._empty_signal(symbol))
