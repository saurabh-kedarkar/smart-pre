"""
Fibonacci Retracement Levels
"""
import pandas as pd
import numpy as np

FIBONACCI_RATIOS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]


def compute_fibonacci_levels(highs: pd.Series, lows: pd.Series,
                              lookback: int = 100) -> dict:
    """
    Calculate Fibonacci retracement levels from recent swing high/low.
    """
    recent_highs = highs.tail(lookback)
    recent_lows = lows.tail(lookback)

    swing_high = recent_highs.max()
    swing_low = recent_lows.min()
    price_range = swing_high - swing_low

    levels = {}
    for ratio in FIBONACCI_RATIOS:
        # Retracement from high to low
        levels[f"fib_{ratio}"] = swing_high - (price_range * ratio)

    return {
        "levels": levels,
        "swing_high": float(swing_high),
        "swing_low": float(swing_low),
        "range": float(price_range),
    }


def fibonacci_signal(current_price: float, fib_data: dict) -> dict:
    """
    Determine where the price sits relative to Fibonacci levels.
    """
    levels = fib_data["levels"]
    sorted_levels = sorted(levels.items(), key=lambda x: x[1], reverse=True)

    nearest_support = None
    nearest_resistance = None
    nearest_support_dist = float("inf")
    nearest_resistance_dist = float("inf")

    for name, level in sorted_levels:
        diff = current_price - level
        if diff >= 0 and diff < nearest_support_dist:
            nearest_support = {"name": name, "level": level}
            nearest_support_dist = diff
        elif diff < 0 and abs(diff) < nearest_resistance_dist:
            nearest_resistance = {"name": name, "level": level}
            nearest_resistance_dist = abs(diff)

    # Signal based on position
    range_val = fib_data["range"]
    position_pct = ((current_price - fib_data["swing_low"]) / range_val) * 100 if range_val > 0 else 50

    if position_pct > 78.6:
        signal = "SELL"
        strength = -0.5
        desc = "Near swing high — potential reversal"
    elif position_pct > 61.8:
        signal = "NEUTRAL_BULLISH"
        strength = 0.2
        desc = "Between 61.8% and 78.6% — bullish zone"
    elif position_pct > 38.2:
        signal = "NEUTRAL"
        strength = 0.0
        desc = "In the middle zone (38.2%-61.8%)"
    elif position_pct > 23.6:
        signal = "NEUTRAL_BEARISH"
        strength = -0.2
        desc = "Between 23.6% and 38.2% — bearish zone"
    else:
        signal = "BUY"
        strength = 0.5
        desc = "Near swing low — potential bounce"

    return {
        "signal": signal,
        "strength": strength,
        "description": desc,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "position_pct": float(position_pct),
        "levels": {k: float(v) for k, v in levels.items()},
    }
