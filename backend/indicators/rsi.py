"""
RSI (Relative Strength Index) Indicator
"""
import numpy as np
import pandas as pd


def compute_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate RSI using the standard Wilder smoothing method.
    
    Args:
        closes: Series of closing prices
        period: RSI lookback period (default 14)
    
    Returns:
        Series of RSI values (0-100)
    """
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def rsi_signal(rsi_value: float) -> dict:
    """
    Interpret RSI value into a trading signal.
    
    Returns:
        dict with keys: signal, strength, description
    """
    if rsi_value >= 80:
        return {"signal": "STRONG_SELL", "strength": 0.9, "description": "Extremely overbought"}
    elif rsi_value >= 70:
        return {"signal": "SELL", "strength": 0.7, "description": "Overbought territory"}
    elif rsi_value >= 60:
        return {"signal": "NEUTRAL_BULLISH", "strength": 0.3, "description": "Upper neutral zone"}
    elif rsi_value >= 40:
        return {"signal": "NEUTRAL", "strength": 0.0, "description": "Neutral zone"}
    elif rsi_value >= 30:
        return {"signal": "NEUTRAL_BEARISH", "strength": -0.3, "description": "Lower neutral zone"}
    elif rsi_value >= 20:
        return {"signal": "BUY", "strength": -0.7, "description": "Oversold territory"}
    else:
        return {"signal": "STRONG_BUY", "strength": -0.9, "description": "Extremely oversold"}


def rsi_divergence(prices: pd.Series, rsi_values: pd.Series, lookback: int = 14) -> dict:
    """
    Detect RSI divergence (bullish/bearish).
    
    Bullish divergence: price makes lower low but RSI makes higher low
    Bearish divergence: price makes higher high but RSI makes lower high
    """
    if len(prices) < lookback * 2:
        return {"divergence": "NONE", "type": None}

    recent_prices = prices.tail(lookback)
    prev_prices = prices.iloc[-lookback * 2:-lookback]
    recent_rsi = rsi_values.tail(lookback)
    prev_rsi = rsi_values.iloc[-lookback * 2:-lookback]

    price_lower_low = recent_prices.min() < prev_prices.min()
    rsi_higher_low = recent_rsi.min() > prev_rsi.min()

    price_higher_high = recent_prices.max() > prev_prices.max()
    rsi_lower_high = recent_rsi.max() < prev_rsi.max()

    if price_lower_low and rsi_higher_low:
        return {"divergence": "BULLISH", "type": "hidden_bullish",
                "description": "Bullish RSI divergence detected"}
    elif price_higher_high and rsi_lower_high:
        return {"divergence": "BEARISH", "type": "hidden_bearish",
                "description": "Bearish RSI divergence detected"}

    return {"divergence": "NONE", "type": None}
