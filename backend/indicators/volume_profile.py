"""
Volume Profile Analysis
"""
import pandas as pd
import numpy as np


def compute_volume_profile(closes: pd.Series, volumes: pd.Series,
                            num_bins: int = 24) -> dict:
    """
    Calculate volume profile (price vs. volume histogram).
    
    Returns:
        dict with price levels and their corresponding volumes
    """
    price_min = closes.min()
    price_max = closes.max()

    if price_min == price_max:
        return {"bins": [], "poc": float(price_min), "value_area_high": float(price_max),
                "value_area_low": float(price_min)}

    bins = np.linspace(price_min, price_max, num_bins + 1)
    bin_volumes = np.zeros(num_bins)

    for i in range(len(closes)):
        price = closes.iloc[i]
        vol = volumes.iloc[i]
        bin_idx = int((price - price_min) / (price_max - price_min) * (num_bins - 1))
        bin_idx = min(bin_idx, num_bins - 1)
        bin_volumes[bin_idx] += vol

    # Point of Control (POC) — price level with highest volume
    poc_idx = np.argmax(bin_volumes)
    poc_price = (bins[poc_idx] + bins[poc_idx + 1]) / 2

    # Value Area (70% of total volume around POC)
    total_vol = bin_volumes.sum()
    target_vol = total_vol * 0.70
    accumulated = bin_volumes[poc_idx]
    low_idx = poc_idx
    high_idx = poc_idx

    while accumulated < target_vol:
        expand_low = low_idx > 0
        expand_high = high_idx < num_bins - 1

        if expand_low and expand_high:
            if bin_volumes[low_idx - 1] >= bin_volumes[high_idx + 1]:
                low_idx -= 1
                accumulated += bin_volumes[low_idx]
            else:
                high_idx += 1
                accumulated += bin_volumes[high_idx]
        elif expand_low:
            low_idx -= 1
            accumulated += bin_volumes[low_idx]
        elif expand_high:
            high_idx += 1
            accumulated += bin_volumes[high_idx]
        else:
            break

    value_area_high = (bins[high_idx] + bins[high_idx + 1]) / 2
    value_area_low = (bins[low_idx] + bins[low_idx + 1]) / 2

    profile_bins = []
    for i in range(num_bins):
        profile_bins.append({
            "price_low": float(bins[i]),
            "price_high": float(bins[i + 1]),
            "price_mid": float((bins[i] + bins[i + 1]) / 2),
            "volume": float(bin_volumes[i]),
        })

    return {
        "bins": profile_bins,
        "poc": float(poc_price),
        "value_area_high": float(value_area_high),
        "value_area_low": float(value_area_low),
        "total_volume": float(total_vol),
    }


def volume_signal(current_price: float, volume_profile: dict,
                  current_volume: float, avg_volume: float) -> dict:
    """
    Generate volume-based signals.
    """
    poc = volume_profile["poc"]
    vah = volume_profile["value_area_high"]
    val = volume_profile["value_area_low"]

    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    is_volume_spike = volume_ratio > 2.0
    is_high_volume = volume_ratio > 1.5

    if current_price > vah:
        base_signal = "BULLISH"
        strength = 0.4
        desc = "Price above Value Area High"
    elif current_price < val:
        base_signal = "BEARISH"
        strength = -0.4
        desc = "Price below Value Area Low"
    elif abs(current_price - poc) / poc < 0.001:
        base_signal = "NEUTRAL"
        strength = 0.0
        desc = "Price at Point of Control"
    else:
        base_signal = "NEUTRAL"
        strength = 0.1 if current_price > poc else -0.1
        desc = "Price within Value Area"

    if is_volume_spike:
        strength *= 1.5
        desc += " | Volume SPIKE detected"

    return {
        "signal": base_signal,
        "strength": max(-1.0, min(1.0, strength)),
        "description": desc,
        "volume_ratio": float(volume_ratio),
        "is_spike": is_volume_spike,
        "poc": poc,
        "value_area_high": vah,
        "value_area_low": val,
    }
