"""
LSTM Price Prediction Model
Predicts the next 15-minute price direction and magnitude.
"""
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple


class CryptoLSTM(nn.Module):
    """
    LSTM model for crypto price prediction.
    
    Input features: OHLCV + technical indicators
    Output: direction probability + predicted return
    """

    def __init__(self, input_size: int = 12, hidden_size: int = 128,
                 num_layers: int = 2, dropout: float = 0.3):
        super().__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )

        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1),
        )

        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(dropout / 2),
        )

        # Direction probability (UP/DOWN)
        self.direction_head = nn.Sequential(
            nn.Linear(32, 2),
            nn.Softmax(dim=-1),
        )

        # Predicted return magnitude
        self.magnitude_head = nn.Linear(32, 1)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            x: shape (batch, sequence_length, input_size)
        
        Returns:
            direction_probs: shape (batch, 2) — [P(DOWN), P(UP)]
            magnitude: shape (batch, 1) — predicted return
        """
        lstm_out, _ = self.lstm(x)

        # Attention mechanism
        attn_weights = self.attention(lstm_out)
        attn_weights = torch.softmax(attn_weights, dim=1)
        context = torch.sum(attn_weights * lstm_out, dim=1)

        features = self.classifier(context)
        direction_probs = self.direction_head(features)
        magnitude = self.magnitude_head(features)

        return direction_probs, magnitude


class LSTMPredictor:
    """
    Wrapper for LSTM model with preprocessing and inference.
    """

    def __init__(self, input_size: int = 12, hidden_size: int = 128,
                 num_layers: int = 2, weights_path: str = "models/weights/lstm_model.pth"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CryptoLSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
        ).to(self.device)
        self.weights_path = weights_path
        self._is_trained = False
        
        # Try loading weights if they exist
        import os
        if os.path.exists(self.weights_path):
            try:
                self.load_weights(self.weights_path)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to load LSTM weights: {e}")
        
        self.model.eval()

    def save_weights(self, path: str = None) -> bool:
        """Save model state dict."""
        path = path or self.weights_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            torch.save(self.model.state_dict(), path)
            return True
        except Exception as e:
            return False

    def load_weights(self, path: str = None) -> bool:
        """Load model state dict."""
        path = path or self.weights_path
        if not os.path.exists(path):
            return False
            
        try:
            self.model.load_state_dict(torch.load(path, map_location=self.device))
            self.model.eval()
            self._is_trained = True
            return True
        except Exception as e:
            return False

    def prepare_features(self, data: dict) -> np.ndarray:
        """
        Prepare feature matrix from OHLCV + indicators.
        
        Expected data keys:
            open, high, low, close, volume,
            rsi, macd, macd_signal, bb_upper, bb_lower,
            ema_9, vwap
        """
        feature_names = [
            "open", "high", "low", "close", "volume",
            "rsi", "macd", "macd_signal", "bb_upper", "bb_lower",
            "ema_9", "vwap",
        ]

        features = []
        for name in feature_names:
            if name in data:
                features.append(np.array(data[name], dtype=np.float32))
            else:
                features.append(np.zeros(len(data.get("close", [])), dtype=np.float32))

        feature_matrix = np.column_stack(features)

        # Normalize each feature column
        for i in range(feature_matrix.shape[1]):
            col = feature_matrix[:, i]
            col_std = col.std()
            if col_std > 0:
                feature_matrix[:, i] = (col - col.mean()) / col_std

        return feature_matrix

    def predict(self, feature_matrix: np.ndarray,
                sequence_length: int = 60) -> dict:
        """
        Run inference on the prepared features.
        
        Returns:
            dict with direction, confidence, predicted_return
        """
        if len(feature_matrix) < sequence_length:
            return {
                "direction": "NEUTRAL",
                "confidence": 0.50,
                "predicted_return": 0.0,
                "model": "LSTM",
            }

        # Take the last `sequence_length` timesteps
        seq = feature_matrix[-sequence_length:]
        tensor = torch.tensor(seq, dtype=torch.float32).unsqueeze(0).to(self.device)

        with torch.no_grad():
            direction_probs, magnitude = self.model(tensor)

        probs = direction_probs.cpu().numpy()[0]
        predicted_return = magnitude.cpu().numpy()[0][0]

        # probs[0] = P(DOWN), probs[1] = P(UP)
        if probs[1] > probs[0]:
            direction = "BULLISH"
            confidence = float(probs[1])
        else:
            direction = "BEARISH"
            confidence = float(probs[0])

        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "predicted_return": round(float(predicted_return), 6),
            "probabilities": {"up": round(float(probs[1]), 4),
                              "down": round(float(probs[0]), 4)},
            "model": "LSTM",
        }
