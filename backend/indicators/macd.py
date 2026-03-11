"""
MACD (Moving Average Convergence Divergence) Indicator
"""
import pandas as pd


def compute_macd(closes: pd.Series, fast: int = 12, slow: int = 26,
                 signal_period: int = 9) -> dict:
    """
    Calculate MACD line, signal line, and histogram.
    
    Returns:
        dict with keys: macd_line, signal_line, histogram (all pd.Series)
    """
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    return {
        "macd_line": macd_line,
        "signal_line": signal_line,
        "histogram": histogram,
    }


def macd_signal(macd_data: dict) -> dict:
    """
    Interpret MACD into trading signal.
    """
    macd_line = macd_data["macd_line"]
    signal_line = macd_data["signal_line"]
    histogram = macd_data["histogram"]

    if len(macd_line) < 2:
        return {"signal": "NEUTRAL", "strength": 0.0, "description": "Insufficient data"}

    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]
    prev_macd = macd_line.iloc[-2]
    prev_signal = signal_line.iloc[-2]
    current_hist = histogram.iloc[-1]
    prev_hist = histogram.iloc[-2]

    # Crossover detection
    bullish_cross = prev_macd <= prev_signal and current_macd > current_signal
    bearish_cross = prev_macd >= prev_signal and current_macd < current_signal

    # Histogram momentum
    hist_increasing = current_hist > prev_hist
    hist_positive = current_hist > 0

    if bullish_cross:
        return {"signal": "BUY", "strength": 0.8,
                "description": "Bullish MACD crossover"}
    elif bearish_cross:
        return {"signal": "SELL", "strength": -0.8,
                "description": "Bearish MACD crossover"}
    elif hist_positive and hist_increasing:
        return {"signal": "BULLISH", "strength": 0.4,
                "description": "Bullish momentum increasing"}
    elif hist_positive and not hist_increasing:
        return {"signal": "WEAK_BULLISH", "strength": 0.2,
                "description": "Bullish momentum weakening"}
    elif not hist_positive and not hist_increasing:
        return {"signal": "BEARISH", "strength": -0.4,
                "description": "Bearish momentum increasing"}
    elif not hist_positive and hist_increasing:
        return {"signal": "WEAK_BEARISH", "strength": -0.2,
                "description": "Bearish momentum weakening"}

    return {"signal": "NEUTRAL", "strength": 0.0, "description": "No clear signal"}
