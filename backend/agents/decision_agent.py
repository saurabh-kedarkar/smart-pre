"""
Decision Engine Agent — the final arbitrator that combines all analyses
into a single BUY / SELL / HOLD decision.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DecisionAgent:
    """
    Final decision engine.
    Combines outputs from all other agents into a unified decision.
    """

    def __init__(self):
        self._decisions: dict = {}

    def decide(self, symbol: str, signal: dict, risk: dict,
               prediction: dict, sentiment: dict,
               technical: dict) -> dict:
        """
        Make final trading decision.
        
        Inputs:
            signal: from SignalAgent
            risk: from RiskAgent
            prediction: from PredictionAgent
            sentiment: from SentimentAgent
            technical: from TechnicalAgent
        
        Returns:
            Final decision with full context
        """
        price = signal.get("entry_price", 0)
        signal_type = signal.get("signal", "HOLD")
        confidence = signal.get("confidence", 0.5)
        should_trade = risk.get("should_trade", False)
        pred_1m = prediction.get("prediction_1m", {})
        pred_5m = prediction.get("prediction_5m", {})
        pred_direction = prediction.get("direction", "NEUTRAL")  # FIX: was undefined
        sent_label = sentiment.get("sentiment", "NEUTRAL")
        market_structure = technical.get("market_structure", {})
        overall_ta = technical.get("overall_signal", "NEUTRAL")
        risk_level = risk.get("risk_level", "UNKNOWN")  # FIX: was undefined

        # ── Agreement check ──────────────────────────────
        # Count how many systems agree on direction
        bullish_count = 0
        bearish_count = 0

        if signal_type in ("BUY", "WEAK_BUY"):
            bullish_count += 1
        elif signal_type in ("SELL", "WEAK_SELL"):
            bearish_count += 1

        if pred_direction == "BULLISH":
            bullish_count += 1
        elif pred_direction == "BEARISH":
            bearish_count += 1

        if sent_label in ("POSITIVE", "SLIGHTLY_POSITIVE"):
            bullish_count += 1
        elif sent_label in ("NEGATIVE", "SLIGHTLY_NEGATIVE"):
            bearish_count += 1

        if overall_ta in ("BULLISH", "SLIGHTLY_BULLISH"):
            bullish_count += 1
        elif overall_ta in ("BEARISH", "SLIGHTLY_BEARISH"):
            bearish_count += 1

        agreement_count = max(bullish_count, bearish_count)
        agreement_pct = agreement_count / 4 * 100

        # ── Final decision ───────────────────────────────
        if not should_trade:
            final_action = "HOLD"
            reason = "Risk assessment recommends skipping this trade"
        elif bullish_count >= 3:
            final_action = "BUY"
            reason = "PREMIUM Signal: Strong majority (3+ systems) agree on BULLISH"
        elif bearish_count >= 3:
            final_action = "SELL"
            reason = "PREMIUM Signal: Strong majority (3+ systems) agree on BEARISH"
        elif bullish_count >= 2 and confidence >= 0.55:
            final_action = "BUY"
            reason = "Good consensus (2/4) with decent confidence"
        elif bearish_count >= 2 and confidence >= 0.55:
            final_action = "SELL"
            reason = "Good consensus (2/4) with decent confidence"
        elif agreement_count >= 2 and confidence >= 0.65:
            final_action = "BUY" if bullish_count > bearish_count else "SELL"
            reason = "High confidence outweighing minor system disagreement"
        else:
            final_action = "HOLD"
            reason = "Wait for clearer setup — optimized for safety"

        # ── Summary ──────────────────────────────────────
        decision = {
            "symbol": symbol,
            "action": final_action,
            "confidence": round(confidence, 4),
            "confidence_pct": round(confidence * 100, 1),
            "reason": reason,
            "price": price,
            "signal": {
                "type": signal_type,
                "entry": signal.get("entry_price"),
                "target_1": signal.get("target_1"),
                "target_2": signal.get("target_2"),
                "target_3": signal.get("target_3"),
                "stop_loss": signal.get("stop_loss"),
                "risk_reward": signal.get("risk_reward_ratio"),
                "breakdown": signal.get("breakdown", {}),
            },
            "risk": {
                "level": risk_level,
                "should_trade": should_trade,
                "position_value": risk.get("position_value"),
                "max_loss": risk.get("max_loss"),
                "potential_gain": risk.get("potential_gain"),
                "risk_pct": risk.get("risk_pct"),
                "warnings": risk.get("warnings", []),
                "recommendation": risk.get("recommendation", ""),
            },
            "prediction": {
                "direction": pred_direction,
                "confidence": prediction.get("confidence"),
                "next_1m": pred_1m,
                "next_5m": pred_5m,
                "breakout_probability": prediction.get("breakout_probability"),
                "models": prediction.get("models", {}),
            },
            "sentiment": {
                "label": sent_label,
                "score": sentiment.get("composite_score"),
                "fear_greed": sentiment.get("fear_greed", {}),
            },
            "technical": {
                "signal": overall_ta,
                "strength": technical.get("composite_strength"),
                "market_structure": market_structure,
                "volatility": technical.get("volatility"),
            },
            "agreement": {
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "agreement_pct": round(agreement_pct, 1),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._decisions[symbol] = decision
        logger.info(
            f"Decision for {symbol}: {final_action} | "
            f"Confidence: {confidence*100:.1f}% | "
            f"Bull: {bullish_count} Bear: {bearish_count} | "
            f"Reason: {reason}"
        )
        return decision

    def get_decision(self, symbol: str) -> dict:
        return self._decisions.get(symbol, {
            "symbol": symbol,
            "action": "HOLD",
            "confidence": 0.50,
            "confidence_pct": 50.0,
            "reason": "No analysis available",
        })

    def get_all_decisions(self) -> dict:
        return dict(self._decisions)
