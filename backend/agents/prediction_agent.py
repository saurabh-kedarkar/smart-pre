"""
Prediction Agent — runs ML models to predict price direction.
Gracefully handles missing PyTorch/numpy by falling back to heuristic predictions.
"""
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

# Try importing ML models — they may fail if PyTorch isn't available
try:
    from models.lstm_model import LSTMPredictor
    from models.transformer_model import TransformerPredictor
    ML_AVAILABLE = True
    logger.info("PyTorch ML models loaded successfully")
except Exception as e:
    ML_AVAILABLE = False
    logger.warning(f"ML models not available (falling back to heuristic): {e}")


class PredictionAgent:
    """
    Manages ML models and generates ensemble predictions.
    Falls back to heuristic-based predictions if PyTorch is unavailable.
    """

    def __init__(self, sequence_length: int = 60):
        self.sequence_length = sequence_length
        self.lstm = None
        self.transformer = None
        self._predictions: dict = {}

        if ML_AVAILABLE:
            try:
                self.lstm = LSTMPredictor(input_size=12)
                self.transformer = TransformerPredictor(input_size=12)
            except Exception as e:
                logger.warning(f"Failed to initialize ML models: {e}")

    def predict(self, indicator_data: dict, symbol: str = "") -> dict:
        """
        Run prediction using ML ensemble or heuristic fallback.
        """
        if not indicator_data or "close" not in indicator_data:
            return self._empty_prediction(symbol)

        # Try ML prediction first
        if self.lstm and self.transformer:
            try:
                return self._ml_predict(indicator_data, symbol)
            except Exception as e:
                logger.debug(f"ML prediction failed, using heuristic: {e}")

        # Heuristic prediction fallback
        return self._heuristic_predict(indicator_data, symbol)

    def _ml_predict(self, indicator_data: dict, symbol: str) -> dict:
        """ML-based prediction using LSTM + Transformer ensemble."""
        lstm_features = self.lstm.prepare_features(indicator_data)
        transformer_features = self.transformer.prepare_features(indicator_data)

        lstm_pred = self.lstm.predict(lstm_features, self.sequence_length)
        transformer_pred = self.transformer.predict(transformer_features, self.sequence_length)

        lstm_weight = 0.45
        transformer_weight = 0.55

        lstm_score = lstm_pred["confidence"] if lstm_pred["direction"] == "BULLISH" else (
            1 - lstm_pred["confidence"])
        transformer_score = transformer_pred["confidence"] if transformer_pred["direction"] == "BULLISH" else (
            1 - transformer_pred["confidence"])

        ensemble_bullish = lstm_score * lstm_weight + transformer_score * transformer_weight

        if ensemble_bullish > 0.5:
            direction = "BULLISH"
            confidence = ensemble_bullish
        else:
            direction = "BEARISH"
            confidence = 1 - ensemble_bullish

        avg_return = (
            lstm_pred.get("predicted_return", 0) * lstm_weight +
            transformer_pred.get("predicted_return", 0) * transformer_weight
        )

        pred_5m = self._extrapolate_timeframe(direction, confidence, factor=0.33)
        pred_15m = {
            "direction": direction,
            "confidence": round(confidence, 4),
            "probability": round(confidence * 100, 1),
        }

        volatility = transformer_pred.get("predicted_volatility", 0)
        breakout_prob = min(0.95, abs(avg_return) * 50 + volatility * 10 + 0.1)

        result = {
            "symbol": symbol,
            "direction": direction,
            "confidence": round(confidence, 4),
            "predicted_return": round(float(avg_return), 6),
            "prediction_5m": pred_5m,
            "prediction_15m": pred_15m,
            "breakout_probability": round(float(breakout_prob), 4),
            "models": {
                "lstm": lstm_pred,
                "transformer": transformer_pred,
            },
            "ensemble_weights": {"lstm": lstm_weight, "transformer": transformer_weight},
            "model_type": "ML_ENSEMBLE",
        }

        self._predictions[symbol] = result
        return result

    def _heuristic_predict(self, indicator_data: dict, symbol: str) -> dict:
        """
        Heuristic prediction based on technical indicator momentum.
        Used as fallback when PyTorch is unavailable.
        """
        closes = indicator_data.get("close", [])
        rsi_vals = indicator_data.get("rsi", [])
        macd_vals = indicator_data.get("macd", [])
        volumes = indicator_data.get("volume", [])

        if len(closes) < 20:
            return self._empty_prediction(symbol)

        # Price momentum (short-term slope)
        recent = closes[-20:]
        price_change = (recent[-1] - recent[0]) / recent[0] if recent[0] > 0 else 0

        # RSI signal
        rsi_score = 0.0
        if rsi_vals and len(rsi_vals) > 0:
            last_rsi = rsi_vals[-1]
            if last_rsi > 70:
                rsi_score = -0.3
            elif last_rsi > 60:
                rsi_score = 0.1
            elif last_rsi < 30:
                rsi_score = 0.3
            elif last_rsi < 40:
                rsi_score = -0.1

        # MACD signal
        macd_score = 0.0
        if macd_vals and len(macd_vals) >= 2:
            if macd_vals[-1] > macd_vals[-2] and macd_vals[-1] > 0:
                macd_score = 0.25 # Stronger bullish if above zero
            elif macd_vals[-1] > macd_vals[-2]:
                macd_score = 0.15
            elif macd_vals[-1] < macd_vals[-2] and macd_vals[-1] < 0:
                macd_score = -0.25
            else:
                macd_score = -0.15

        # VWAP Signal
        vwap_vals = indicator_data.get("vwap", [])
        vwap_score = 0.0
        if vwap_vals and len(vwap_vals) > 0:
            if closes[-1] > vwap_vals[-1]:
                vwap_score = 0.1
            else:
                vwap_score = -0.1

        # Volume trend
        vol_score = 0.0
        if volumes and len(volumes) >= 10:
            recent_vol = np.mean(volumes[-5:])
            prev_vol = np.mean(volumes[-20:-5])
            if recent_vol > prev_vol * 1.3:
                vol_score = 0.2 if price_change > 0 else -0.2

        # Composite
        composite = price_change * 60 + rsi_score + macd_score + vwap_score + vol_score
        composite = max(-1.0, min(1.0, composite))

        # Count how many sub-signals agree
        sub_signals = [rsi_score, macd_score, vwap_score, vol_score]
        bullish_subs = sum(1 for s in sub_signals if s > 0.05)
        bearish_subs = sum(1 for s in sub_signals if s < -0.05)
        neutral_subs = len(sub_signals) - bullish_subs - bearish_subs
        agreement = max(bullish_subs, bearish_subs)

        if composite > 0.15:
            direction = "BULLISH"
            # Confidence based on composite strength + agreement
            confidence = 0.50 + abs(composite) * 0.35 + (agreement / len(sub_signals)) * 0.10
        elif composite < -0.15:
            direction = "BEARISH"
            confidence = 0.50 + abs(composite) * 0.35 + (agreement / len(sub_signals)) * 0.10
        else:
            direction = "NEUTRAL"
            # Low confidence for weak/mixed signals — CAN go below 50%
            confidence = 0.35 + abs(composite) * 0.25

        # Penalize conflicting signals (both bull and bear subs present)
        if bullish_subs > 0 and bearish_subs > 0:
            conflict_penalty = min(bullish_subs, bearish_subs) * 0.06
            confidence -= conflict_penalty

        confidence = min(0.92, max(0.25, confidence))

        pred_5m = self._extrapolate_timeframe(direction, confidence, factor=0.33)
        pred_15m = {
            "direction": direction,
            "confidence": round(confidence, 4),
            "probability": round(confidence * 100, 1),
        }

        breakout_prob = min(0.6, abs(composite) * 0.4 + 0.05) if abs(composite) > 0.2 else 0.05

        result = {
            "symbol": symbol,
            "direction": direction,
            "confidence": round(confidence, 4),
            "predicted_return": round(float(price_change * 0.3), 6),
            "prediction_5m": pred_5m,
            "prediction_15m": pred_15m,
            "breakout_probability": round(float(breakout_prob), 4),
            "models": {
                "lstm": {"direction": direction, "confidence": round(confidence * 0.95, 4), "model": "heuristic"},
                "transformer": {"direction": direction, "confidence": round(confidence * 1.02, 4), "model": "heuristic"},
            },
            "ensemble_weights": {"lstm": 0.45, "transformer": 0.55},
            "model_type": "HEURISTIC",
        }

        self._predictions[symbol] = result
        return result

    def _extrapolate_timeframe(self, direction: str, confidence: float,
                                factor: float) -> dict:
        scaled_conf = 0.5 + (confidence - 0.5) * factor
        return {
            "direction": direction,
            "confidence": round(scaled_conf, 4),
            "probability": round(scaled_conf * 100, 1),
        }

    def _empty_prediction(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "direction": "NEUTRAL",
            "confidence": 0.50,
            "predicted_return": 0.0,
            "prediction_5m": {"direction": "NEUTRAL", "confidence": 0.50, "probability": 50.0},
            "prediction_15m": {"direction": "NEUTRAL", "confidence": 0.50, "probability": 50.0},
            "breakout_probability": 0.10,
            "models": {},
        }

    def get_prediction(self, symbol: str) -> dict:
        return self._predictions.get(symbol, self._empty_prediction(symbol))
