"""
VWAP (Volume Weighted Average Price) Indicator
"""
import pandas as pd
import numpy as np


def compute_vwap(highs: pd.Series, lows: pd.Series,
                 closes: pd.Series, volumes: pd.Series) -> pd.Series:
    """
    Calculate VWAP.
    
    VWAP = cumulative(Typical Price × Volume) / cumulative(Volume)
    Typical Price = (High + Low + Close) / 3
    """
    typical_price = (highs + lows + closes) / 3.0
    cum_tp_vol = (typical_price * volumes).cumsum()
    cum_vol = volumes.cumsum()
    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    return vwap.ffill()


def compute_vwap_bands(vwap: pd.Series, closes: pd.Series,
                       std_multiplier: float = 1.0) -> dict:
    """
    Calculate VWAP standard deviation bands.
    """
    deviation = (closes - vwap).rolling(window=20).std()
    return {
        "vwap": vwap,
        "upper_1": vwap + deviation * std_multiplier,
        "lower_1": vwap - deviation * std_multiplier,
        "upper_2": vwap + deviation * std_multiplier * 2,
        "lower_2": vwap - deviation * std_multiplier * 2,
    }


def vwap_signal(current_price: float, vwap_value: float,
                vwap_bands: dict = None) -> dict:
    """
    Interpret VWAP for trading signal.
    """
    diff_pct = ((current_price - vwap_value) / vwap_value) * 100

    if diff_pct > 2.0:
        signal = "SELL"
        strength = -0.5
        desc = f"Price {diff_pct:.1f}% above VWAP — overextended"
    elif diff_pct > 0.5:
        signal = "NEUTRAL_BULLISH"
        strength = 0.2
        desc = f"Price {diff_pct:.1f}% above VWAP"
    elif diff_pct > -0.5:
        signal = "NEUTRAL"
        strength = 0.0
        desc = "Price near VWAP"
    elif diff_pct > -2.0:
        signal = "NEUTRAL_BEARISH"
        strength = -0.2
        desc = f"Price {abs(diff_pct):.1f}% below VWAP"
    else:
        signal = "BUY"
        strength = 0.5
        desc = f"Price {abs(diff_pct):.1f}% below VWAP — potential bounce"

    return {
        "signal": signal,
        "strength": strength,
        "description": desc,
        "vwap": float(vwap_value),
        "deviation_pct": float(diff_pct),
    }
