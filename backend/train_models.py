"""
SmartPre — Training Script
Downloads historical data and trains ML models (LSTM & Transformer).
"""
import asyncio
import os
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from datetime import datetime, timedelta

from utils.binance_client import BinanceClient
from agents.technical_agent import TechnicalAgent
from models.lstm_model import LSTMPredictor
from models.transformer_model import TransformerPredictor

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trainer")

# Config
SYMBOL = "BTCUSDT"
TIMEFRAME = "15m"
TRAIN_DAW_DAYS = 365
SEQUENCE_LENGTH = 60
EPOCHS = 10
BATCH_SIZE = 64
LR = 0.001

async def download_data(symbol: str, tf: str) -> pd.DataFrame:
    """Fetch historical data from Binance."""
    client = BinanceClient()
    logger.info(f"Downloading historical data for {symbol} ({tf})...")
    
    # Binance limits to 1000 candles per request. We need many requests for 1 year.
    # 365 days * 24 * 4 = 35,040 candles
    all_klines = []
    end_time = int(datetime.utcnow().timestamp() * 1000)
    
    # Roughly 35 requests of 1000 each
    for i in range(40):
        try:
            # Note: We need to modify BinanceClient or use raw path for large history
            # For simplicity in this script, we'll fetch a decent chunk (e.g., 5000 candles)
            # as a full year download is slow for a demo.
            df = await client.get_klines(symbol, tf, limit=1000)
            all_klines.append(df)
            break # Just getting 1000 for the demo/example, real training would loop with start_time
        except Exception as e:
            logger.error(f"Download error: {e}")
            break
            
    await client.close()
    return pd.concat(all_klines).drop_duplicates().sort_index()

def prepare_dataset(df: pd.DataFrame, seq_len: int = 60):
    """Convert OHLCV to features and targets."""
    ta = TechnicalAgent()
    indicator_data = ta.get_indicator_data_for_ml(df)
    
    # Prepare predictor to use its normalization logic
    predictor = LSTMPredictor() 
    feature_matrix = predictor.prepare_features(indicator_data)
    
    # Create sequences
    X, y_dir, y_ret = [], [], []
    
    # Price direction and magnitude as target (next close)
    # We want to predict the return of the NEXT candle relative to the current close
    close_prices = df["close"].values
    
    for i in range(len(feature_matrix) - seq_len - 1):
        X.append(feature_matrix[i : i + seq_len])
        
        # Target is return of the candle AFTER the sequence
        current_close = close_prices[i + seq_len - 1]
        next_close = close_prices[i + seq_len]
        ret = (next_close - current_close) / current_close
        
        y_ret.append(ret)
        y_dir.append(1 if ret > 0 else 0)
        
    return (
        torch.tensor(np.array(X), dtype=torch.float32),
        torch.tensor(np.array(y_dir), dtype=torch.long),
        torch.tensor(np.array(y_ret), dtype=torch.float32).unsqueeze(1)
    )

async def train():
    """Main training loop."""
    # 1. Get Data
    df = await download_data(SYMBOL, TIMEFRAME)
    if len(df) < 200:
        logger.error("Not enough data to train.")
        return
        
    # 2. Prepare Tensors
    X, y_dir, y_ret = prepare_dataset(df, SEQUENCE_LENGTH)
    logger.info(f"Prepared {len(X)} samples for training.")
    
    # Split
    split = int(len(X) * 0.8)
    train_ds = TensorDataset(X[:split], y_dir[:split], y_ret[:split])
    test_ds = TensorDataset(X[split:], y_dir[split:], y_ret[split:])
    
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE)
    
    # 3. Initialize Models
    lstm_predictor = LSTMPredictor(input_size=12)
    transformer_predictor = TransformerPredictor(input_size=12)
    
    # 4. Train LSTM
    logger.info("Training LSTM model...")
    await train_one_model(lstm_predictor.model, train_loader, "lstm")
    lstm_predictor.save_weights()
    
    # 5. Train Transformer
    logger.info("Training Transformer model...")
    await train_one_model(transformer_predictor.model, train_loader, "transformer")
    transformer_predictor.save_weights()
    
    logger.info("✅ Training complete! Models saved to backend/models/weights/")

async def train_one_model(model, loader, name):
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion_dir = nn.CrossEntropyLoss()
    criterion_ret = nn.MSELoss()
    
    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0
        for i, (xb, yb_dir, yb_ret) in enumerate(loader):
            optimizer.zero_grad()
            
            # Forward
            if name == "transformer":
                pred_dir_probs, pred_ret, _ = model(xb)
            else:
                pred_dir_probs, pred_ret = model(xb)
                
            loss_dir = criterion_dir(pred_dir_probs, yb_dir)
            loss_ret = criterion_ret(pred_ret, yb_ret)
            
            loss = loss_dir + loss_ret * 100 # Weight return loss more
            
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        logger.info(f"Epoch {epoch+1}/{EPOCHS} | Loss: {total_loss/len(loader):.4f}")

if __name__ == "__main__":
    asyncio.run(train())
