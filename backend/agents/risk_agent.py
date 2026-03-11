"""
Risk Management Agent — evaluates risk and provides safety recommendations.
"""
import logging
from typing import Optional

from config import (
    MAX_RISK_PER_TRADE,
    MIN_CONFIDENCE_TO_TRADE,
    DEFAULT_STOP_LOSS_PCT,
)

logger = logging.getLogger(__name__)


class RiskAgent:
    """
    Evaluates trading risk and provides safety guardrails.
    """

    def __init__(self):
        self.max_risk = MAX_RISK_PER_TRADE
        self.min_confidence = MIN_CONFIDENCE_TO_TRADE

    def evaluate_risk(self, signal: dict, technical: dict,
                      balance: float = 10000.0) -> dict:
        """
        Evaluate risk for a trading signal.
        
        Args:
            signal: output from SignalAgent
            technical: output from TechnicalAgent
            balance: account balance
        
        Returns:
            Risk assessment with position sizing and warnings
        """
        entry = signal.get("entry_price", 0)
        stop = signal.get("stop_loss", 0)
        confidence = signal.get("confidence", 0.5)
        rr_ratio = signal.get("risk_reward_ratio", 0)
        volatility = technical.get("volatility", 0.5)
        signal_type = signal.get("signal", "HOLD")

        # ── Risk calculation ─────────────────────────────
        risk_per_unit = abs(entry - stop) if entry > 0 else 0
        risk_pct = (risk_per_unit / entry) * 100 if entry > 0 else 0

        # ── Position sizing (Kelly-inspired) ─────────────
        max_position_value = balance * self.max_risk
        if risk_per_unit > 0:
            position_size = max_position_value / risk_per_unit
            position_value = position_size * entry
        else:
            position_size = 0
            position_value = 0

        # Cap position to balance
        if position_value > balance * 0.3:
            position_value = balance * 0.3
            position_size = position_value / entry if entry > 0 else 0

        max_loss = position_size * risk_per_unit
        potential_gain = position_size * abs(signal.get("target_1", entry) - entry)

        # ── Risk level classification ────────────────────
        warnings = []
        risk_level = "LOW"

        if risk_pct > 2.0:
            risk_level = "HIGH"
            warnings.append("Stop loss distance exceeds 2% — high risk")

        if volatility > 1.5:
            risk_level = "HIGH" if risk_level != "HIGH" else "EXTREME"
            warnings.append(f"High volatility ({volatility:.1f}%) detected")

        if confidence < self.min_confidence:
            warnings.append(
                f"Low confidence ({confidence:.1%}) — below {self.min_confidence:.0%} threshold"
            )

        if rr_ratio < 1.5:
            warnings.append(f"Risk/reward ratio {rr_ratio:.1f} is below recommended 1.5")

        if signal_type == "HOLD":
            warnings.append("No clear signal — consider waiting")

        market_structure = technical.get("market_structure", {})
        if market_structure.get("type") == "CONSOLIDATION":
            warnings.append("Market is consolidating — reduced signal reliability")

        if not warnings:
            risk_level = "LOW"
        elif len(warnings) <= 2:
            risk_level = max(risk_level, "MEDIUM")

        # ── Trade recommendation ─────────────────────────
        should_trade = (
            confidence >= self.min_confidence and
            risk_level != "EXTREME" and
            signal_type in ("BUY", "SELL", "WEAK_BUY", "WEAK_SELL") and
            rr_ratio >= 1.0
        )

        return {
            "symbol": signal.get("symbol", ""),
            "risk_level": risk_level,
            "should_trade": should_trade,
            "position_size": round(position_size, 6),
            "position_value": round(position_value, 2),
            "max_loss": round(max_loss, 2),
            "potential_gain": round(potential_gain, 2),
            "risk_pct": round(risk_pct, 4),
            "risk_reward": round(rr_ratio, 2),
            "warnings": warnings,
            "recommendation": (
                f"{'Execute' if should_trade else 'Skip'} {signal_type} "
                f"with {confidence:.0%} confidence"
            ),
        }
