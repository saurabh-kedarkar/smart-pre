"""
Decision Engine Agent — the final arbitrator that combines all analyses
into a single BUY / SELL / HOLD decision with clear, actionable messages.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DecisionAgent:
    """
    Final decision engine.
    Combines outputs from all other agents into a unified decision
    with detailed, user-friendly reasons and proper HOLD messages.
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
            Final decision with full context and clear messages
        """
        price = signal.get("entry_price", 0)
        signal_type = signal.get("signal", "HOLD")
        confidence = signal.get("confidence", 0.5)
        should_trade = risk.get("should_trade", False)
        risk_level = risk.get("risk_level", "HIGH")
        pred_direction = prediction.get("direction", "NEUTRAL")
        pred_confidence = prediction.get("confidence", 0.5)
        pred_15m = prediction.get("prediction_15m", {})
        sent_label = sentiment.get("sentiment", "NEUTRAL")
        market_structure = technical.get("market_structure", {})
        overall_ta = technical.get("overall_signal", "NEUTRAL")
        volatility = technical.get("volatility", 0)
        structure_type = market_structure.get("type", "UNKNOWN")

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
        # More selective: only give BUY/SELL when genuinely profitable
        if not should_trade:
            final_action = "HOLD"
            reason, hold_detail = self._get_hold_reason_risk(
                risk_level, confidence, signal_type, structure_type,
                volatility, pred_direction, overall_ta
            )
        elif bullish_count >= 4 and confidence > 0.65:
            final_action = "BUY"
            reason = "🔥 PREMIUM: All 4 systems (Technical, AI, Sentiment, Signal) agree BULLISH — strong buy opportunity"
        elif bearish_count >= 4 and confidence > 0.65:
            final_action = "SELL"
            reason = "🔥 PREMIUM: All 4 systems (Technical, AI, Sentiment, Signal) agree BEARISH — strong sell signal"
        elif bullish_count >= 3 and confidence > 0.70:
            final_action = "BUY"
            reason = f"✅ Strong consensus: {bullish_count}/4 systems bullish with {confidence:.0%} confidence"
        elif bearish_count >= 3 and confidence > 0.70:
            final_action = "SELL"
            reason = f"✅ Strong consensus: {bearish_count}/4 systems bearish with {confidence:.0%} confidence"
        elif agreement_count >= 3 and confidence > 0.80:
            final_action = "BUY" if bullish_count > bearish_count else "SELL"
            direction_text = "bullish" if bullish_count > bearish_count else "bearish"
            reason = f"📊 High confidence ({confidence:.0%}) override: {agreement_count}/4 systems {direction_text}"
        elif bullish_count >= 2 and confidence > 0.60 and signal_type in ("BUY", "WEAK_BUY"):
            final_action = "WEAK_BUY"
            reason = f"📈 Moderate bullish signal: {bullish_count}/4 systems agree — consider small position"
        elif bearish_count >= 2 and confidence > 0.60 and signal_type in ("SELL", "WEAK_SELL"):
            final_action = "WEAK_SELL"
            reason = f"📉 Moderate bearish signal: {bearish_count}/4 systems agree — consider short position"
        else:
            final_action = "HOLD"
            reason, hold_detail = self._get_hold_reason_market(
                bullish_count, bearish_count, confidence,
                structure_type, volatility, pred_direction, overall_ta
            )

        # ── Build advice message ─────────────────────────
        advice = self._build_advice(
            final_action, confidence, risk_level,
            bullish_count, bearish_count, structure_type, volatility
        )

        # ── Summary ──────────────────────────────────────
        decision = {
            "symbol": symbol,
            "action": final_action,
            "confidence": round(confidence, 4),
            "confidence_pct": round(confidence * 100, 1),
            "reason": reason,
            "advice": advice,
            "price": price,
            "signal": {
                "type": signal_type,
                "entry": signal.get("entry_price"),
                "target_1": signal.get("target_1"),
                "target_2": signal.get("target_2"),
                "target_3": signal.get("target_3"),
                "stop_loss": signal.get("stop_loss"),
                "risk_reward": signal.get("risk_reward_ratio"),
            },
            "risk": {
                "level": risk_level,
                "should_trade": should_trade,
                "position_value": risk.get("position_value"),
                "max_loss": risk.get("max_loss"),
                "potential_gain": risk.get("potential_gain"),
                "warnings": risk.get("warnings", []),
                "recommendation": risk.get("recommendation", ""),
            },
            "prediction": {
                "direction": pred_direction,
                "confidence": pred_confidence,
                "next_5m": prediction.get("prediction_5m", {}),
                "next_15m": pred_15m,
                "breakout_probability": prediction.get("breakout_probability"),
            },
            "sentiment": {
                "label": sent_label,
                "score": sentiment.get("composite_score"),
                "fear_greed": sentiment.get("fear_greed", {}),
                "news": sentiment.get("news", {}),
            },
            "technical": {
                "signal": overall_ta,
                "strength": technical.get("composite_strength"),
                "market_structure": market_structure,
                "volatility": volatility,
                "indicators": technical.get("indicators", {}),
            },
            "agreement": {
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "agreement_pct": round(agreement_pct, 1),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._decisions[symbol] = decision
        return decision

    def _get_hold_reason_risk(self, risk_level, confidence, signal_type,
                               structure_type, volatility, pred_dir, ta_signal):
        """Generate detailed HOLD reason when risk assessment says don't trade."""
        reasons = []
        
        if confidence < 0.55:
            reasons.append(f"confidence too low ({confidence:.0%})")
        if risk_level in ("HIGH", "EXTREME"):
            reasons.append(f"risk level is {risk_level}")
        if volatility > 1.5:
            reasons.append(f"high volatility ({volatility:.1f}%)")
        if structure_type == "CONSOLIDATION":
            reasons.append("market is consolidating (sideways)")
        if signal_type == "HOLD":
            reasons.append("no clear directional signal")
        
        if not reasons:
            reasons.append("risk conditions unfavorable")
        
        reason = f"⏸️ WAIT — {', '.join(reasons)}. Let the market show a clearer direction before entering."
        detail = reasons
        return reason, detail

    def _get_hold_reason_market(self, bull_count, bear_count, confidence,
                                 structure_type, volatility, pred_dir, ta_signal):
        """Generate detailed HOLD reason based on market conditions."""
        reasons = []
        
        if bull_count > 0 and bear_count > 0:
            reasons.append(f"mixed signals ({bull_count} bullish vs {bear_count} bearish)")
        elif bull_count == 0 and bear_count == 0:
            reasons.append("no directional signal from any system")
        
        if confidence < 0.50:
            reasons.append(f"low confidence ({confidence:.0%})")
        elif confidence < 0.60:
            reasons.append(f"moderate confidence ({confidence:.0%}) — not strong enough")
            
        if structure_type == "CONSOLIDATION":
            reasons.append("market consolidating — breakout not confirmed")
        elif structure_type == "RANGING":
            reasons.append("market ranging without clear trend")
            
        if volatility > 1.5:
            reasons.append(f"volatile market ({volatility:.1f}%) — wait for stability")
        elif volatility < 0.1:
            reasons.append("very low volatility — no momentum")
        
        if not reasons:
            reasons.append("insufficient consensus among analysis systems")
        
        reason = f"⏸️ NO TRADE — {', '.join(reasons)}. Wait for stronger alignment before trading."
        detail = reasons
        return reason, detail

    def _build_advice(self, action, confidence, risk_level,
                      bull_count, bear_count, structure_type, volatility):
        """Build clear, actionable advice message for the user."""
        if action == "BUY":
            if confidence > 0.80:
                return "💰 High-probability BUY. Enter with recommended position size. Set stop-loss tight and let profit run."
            return "📈 Good BUY setup. Consider entering with 50-75% of normal position. Follow the Target 1 for quick profit."
        
        elif action == "SELL":
            if confidence > 0.80:
                return "💰 High-probability SELL/SHORT. Enter short with recommended position size."
            return "📉 Good SELL setup. Consider shorting with 50-75% of normal position."
        
        elif action == "WEAK_BUY":
            return "📊 Slight bullish bias detected. Enter with small position (25-50%) only. Keep tight stop-loss and book quick profit at Target 1."
        
        elif action == "WEAK_SELL":
            return "📊 Slight bearish bias detected. Consider small short position (25-50%) only with tight stop-loss."
        
        else:  # HOLD
            tips = []
            if bull_count > bear_count:
                tips.append(f"Slight bullish lean ({bull_count}/4)")
            elif bear_count > bull_count:
                tips.append(f"Slight bearish lean ({bear_count}/4)")
            
            if structure_type == "CONSOLIDATION":
                tips.append("Watch for breakout above resistance or below support")
            elif volatility > 1.0:
                tips.append("Wait for volatility to decrease")
            else:
                tips.append("Wait for 3+ systems to agree on direction")
            
            if confidence < 0.45:
                tips.append("Confidence is very low — do NOT trade right now")
            
            return "🔍 " + ". ".join(tips) + "."

    def get_decision(self, symbol: str) -> dict:
        return self._decisions.get(symbol, {
            "symbol": symbol,
            "action": "HOLD",
            "confidence": 0.50,
            "confidence_pct": 50.0,
            "reason": "⏳ Analysis starting... waiting for first data cycle.",
            "advice": "🔄 SmartPre is analyzing this pair. Results coming shortly.",
        })

    def get_all_decisions(self) -> dict:
        return dict(self._decisions)
