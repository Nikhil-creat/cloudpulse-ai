"""FinOps statistics: EWMA forecast, z-score anomaly flags, month-end projection."""
import numpy as np


def ewma_forecast(series: list[float], horizon: int = 7, alpha: float = 0.4) -> list[float]:
    if not series:
        return [0.0] * horizon
    level = series[0]
    for x in series[1:]:
        level = alpha * x + (1 - alpha) * level
    trend = (np.mean(series[-7:]) - np.mean(series[-14:-7])) / 7 if len(series) >= 14 else 0.0
    return [round(float(max(0.0, level + trend * (i + 1))), 2) for i in range(horizon)]


def zscore_anomalies(series: list[float], z: float = 3.0) -> list[int]:
    if len(series) < 8:
        return []
    a = np.asarray(series, dtype=float)
    med = np.median(a)
    mad = np.median(np.abs(a - med)) or 1e-9
    robust = 0.6745 * (a - med) / mad  # robust z-score (MAD)
    return [int(i) for i in np.where(np.abs(robust) > z)[0]]


def month_end_projection(daily: list[float], day_of_month: int, days_in_month: int = 30) -> float:
    spent = sum(daily[-day_of_month:]) if daily else 0.0
    remaining = sum(ewma_forecast(daily, max(0, days_in_month - day_of_month)))
    return round(spent + remaining, 2)
