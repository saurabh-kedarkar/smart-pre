"""
Bollinger Bands Indicator
"""
import pandas as pd
import numpy as np


def compute_bollinger_bands(closes: pd.Series, period: int = 20,
                            std_dev: float = 2.0) -> dict:
    """
    Calculate Bollinger Bands.
    
    Returns:
        dict with: upper, middle, lower (all pd.Series), bandwidth, percent_b
    """
    middle = closes.rolling(window=period).mean()
    rolling_std = closes.rolling(window=period).std()

    upper = middle + (rolling_std * std_dev)
    lower = middle - (rolling_std * std_dev)

    bandwidth = ((upper - lower) / middle) * 100
    percent_b = ((closes - lower) / (upper - lower)) * 100

    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "bandwidth": bandwidth,
        "percent_b": percent_b,
    }


def bollinger_signal(bb_data: dict, current_price: float) -> dict:
    """
    Interpret Bollinger Bands for trading signals.
    """
    upper = bb_data["upper"].iloc[-1]
    lower = bb_data["lower"].iloc[-1]
    middle = bb_data["middle"].iloc[-1]
    bandwidth = bb_data["bandwidth"].iloc[-1]
    pct_b = bb_data["percent_b"].iloc[-1]

    # Squeeze detection (low bandwidth → potential breakout)
    avg_bandwidth = bb_data["bandwidth"].tail(50).mean()
    is_squeeze = bandwidth < avg_bandwidth * 0.5

    if current_price >= upper:
        signal = "SELL"
        strength = -0.6
        desc = "Price at upper band — potential reversal"
    elif current_price <= lower:
        signal = "BUY"
        strength = 0.6
        desc = "Price at lower band — potential bounce"
    elif current_price > middle:
        signal = "NEUTRAL_BULLISH"
        strength = 0.2
        desc = "Price above middle band"
    elif current_price < middle:
        signal = "NEUTRAL_BEARISH"
        strength = -0.2
        desc = "Price below middle band"
    else:
        signal = "NEUTRAL"
        strength = 0.0
        desc = "Price at middle band"

    return {
        "signal": signal,
        "strength": strength,
        "description": desc,
        "is_squeeze": is_squeeze,
        "bandwidth": float(bandwidth),
        "percent_b": float(pct_b),
    }
