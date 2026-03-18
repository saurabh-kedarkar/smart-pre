"""
Moving Averages — EMA & SMA
"""
import pandas as pd


def compute_ema(closes: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return closes.ewm(span=period, adjust=False).mean()


def compute_sma(closes: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return closes.rolling(window=period).mean()


def compute_all_moving_averages(closes: pd.Series,
                                 ema_periods: list = None,
                                 sma_periods: list = None) -> dict:
    """
    Compute all configured moving averages.
    """
    if ema_periods is None:
        ema_periods = [9, 21, 50, 200]
    if sma_periods is None:
        sma_periods = [20, 50, 100, 200]

    result = {"ema": {}, "sma": {}}

    for p in ema_periods:
        result["ema"][p] = compute_ema(closes, p)

    for p in sma_periods:
        result["sma"][p] = compute_sma(closes, p)

    return result


def ma_signal(closes: pd.Series, ma_data: dict) -> dict:
    """
    Generate moving average signals.
    
    Checks for:
    - Golden cross (short EMA above long EMA)
    - Death cross (short EMA below long EMA)
    - Price position relative to key MAs
    """
    current_price = closes.iloc[-1]
    signals = []
    total_strength = 0.0

    # EMA cross signals
    ema_keys = sorted(ma_data["ema"].keys())
    if len(ema_keys) >= 2:
        short_ema = ma_data["ema"][ema_keys[0]]
        long_ema = ma_data["ema"][ema_keys[-1]]

        if len(short_ema) >= 2 and len(long_ema) >= 2:
            curr_short = short_ema.iloc[-1]
            prev_short = short_ema.iloc[-2]
            curr_long = long_ema.iloc[-1]
            prev_long = long_ema.iloc[-2]

            if prev_short <= prev_long and curr_short > curr_long:
                signals.append("Golden Cross (Bullish)")
                total_strength += 0.8
            elif prev_short >= prev_long and curr_short < curr_long:
                signals.append("Death Cross (Bearish)")
                total_strength -= 0.8

    # Price relative to EMA 200
    if 200 in ma_data["ema"]:
        ema200 = ma_data["ema"][200].iloc[-1]
        if current_price > ema200:
            signals.append("Above EMA200 — bullish trend")
            total_strength += 0.3
        else:
            signals.append("Below EMA200 — bearish trend")
            total_strength -= 0.3

    # Price relative to SMA 50
    if 50 in ma_data["sma"]:
        sma50 = ma_data["sma"][50].iloc[-1]
        if current_price > sma50:
            total_strength += 0.2
        else:
            total_strength -= 0.2

    # Clamp strength
    total_strength = max(-1.0, min(1.0, total_strength))

    if total_strength > 0.3:
        signal = "BULLISH"
    elif total_strength < -0.3:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    return {
        "signal": signal,
        "strength": total_strength,
        "details": signals,
        "description": " | ".join(signals) if signals else "No MA signals",
    }
