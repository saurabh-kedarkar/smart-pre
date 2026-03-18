"""
Transformer-based Price Prediction Model
Uses self-attention for capturing long-range dependencies in time series.
"""
import math
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple


class PositionalEncoding(nn.Module):
    """Positional encoding for transformer input."""

    def __init__(self, d_model: int, max_len: int = 500):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * -(math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]


class CryptoTransformer(nn.Module):
    """
    Transformer encoder model for price prediction.
    """

    def __init__(self, input_size: int = 12, d_model: int = 64,
                 nhead: int = 4, num_layers: int = 2,
                 dim_feedforward: int = 128, dropout: float = 0.2):
        super().__init__()

        self.input_projection = nn.Linear(input_size, d_model)
        self.pos_encoder = PositionalEncoding(d_model)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers
        )

        self.global_pool = nn.AdaptiveAvgPool1d(1)

        self.classifier = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        self.direction_head = nn.Sequential(
            nn.Linear(32, 2),
            nn.Softmax(dim=-1),
        )

        self.magnitude_head = nn.Linear(32, 1)
        self.volatility_head = nn.Linear(32, 1)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, ...]:
        """
        Args:
            x: shape (batch, seq_len, input_size)
        
        Returns:
            direction_probs, magnitude, volatility
        """
        x = self.input_projection(x)
        x = self.pos_encoder(x)

        # Transformer encoding
        x = self.transformer_encoder(x)

        # Global average pooling
        x = x.permute(0, 2, 1)
        x = self.global_pool(x).squeeze(-1)

        features = self.classifier(x)
        direction_probs = self.direction_head(features)
        magnitude = self.magnitude_head(features)
        volatility = torch.abs(self.volatility_head(features))

        return direction_probs, magnitude, volatility


class TransformerPredictor:
    """
    Wrapper for the Transformer prediction model.
    """

    def __init__(self, input_size: int = 12, d_model: int = 64,
                 nhead: int = 4, num_layers: int = 2, weights_path: str = "models/weights/transformer_model.pth"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CryptoTransformer(
            input_size=input_size,
            d_model=d_model,
            nhead=nhead,
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
                logging.getLogger(__name__).warning(f"Failed to load Transformer weights: {e}")
                
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
        Same feature preparation as LSTM for compatibility.
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

        fm = np.column_stack(features)

        for i in range(fm.shape[1]):
            col = fm[:, i]
            col_std = col.std()
            if col_std > 0:
                fm[:, i] = (col - col.mean()) / col_std

        return fm

    def predict(self, feature_matrix: np.ndarray,
                sequence_length: int = 60) -> dict:
        """
        Run inference.
        
        Returns:
            dict with direction, confidence, predicted_return, volatility
        """
        if len(feature_matrix) < sequence_length:
            return {
                "direction": "NEUTRAL",
                "confidence": 0.50,
                "predicted_return": 0.0,
                "predicted_volatility": 0.0,
                "model": "Transformer",
            }

        seq = feature_matrix[-sequence_length:]
        tensor = torch.tensor(seq, dtype=torch.float32).unsqueeze(0).to(self.device)

        with torch.no_grad():
            direction_probs, magnitude, volatility = self.model(tensor)

        probs = direction_probs.cpu().numpy()[0]
        pred_return = magnitude.cpu().numpy()[0][0]
        pred_vol = volatility.cpu().numpy()[0][0]

        if probs[1] > probs[0]:
            direction = "BULLISH"
            confidence = float(probs[1])
        else:
            direction = "BEARISH"
            confidence = float(probs[0])

        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "predicted_return": round(float(pred_return), 6),
            "predicted_volatility": round(float(pred_vol), 6),
            "probabilities": {"up": round(float(probs[1]), 4),
                              "down": round(float(probs[0]), 4)},
            "model": "Transformer",
        }
