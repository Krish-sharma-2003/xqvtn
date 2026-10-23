"""Error metrics for wind forecasts (pure functions, no I/O).

All functions are deterministic and testable with hand-made inputs. Percentiles
use linear interpolation (NumPy default). Horizon buckets are 6h-wide intervals
[0,6) ... [60,72).
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Iterable

from .align import build_hourly_actuals
from .decision import DecisionPoint, compute_cutoff, select_decision_forecast
from .loader import ActualsRow, ForecastRow


def percentile(values: list[float] | list[int], q: float) -> float:
    """Compute q-th percentile using linear interpolation (NumPy default).

    Args:
        values: List of numeric values.
        q: Percentile in [0, 100].

    Returns:
        The interpolated percentile value.

    Raises:
        ValueError: If values is empty.
    """
    if not values:
        raise ValueError("percentile() arg is an empty sequence")
    if q < 0 or q > 100:
        raise ValueError("q must be between 0 and 100")

    sorted_vals = sorted(float(v) for v in values)
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]

    # NumPy's default (linear) interpolation
    k = (n - 1) * (q / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    frac = k - f
    return sorted_vals[f] * (1.0 - frac) + sorted_vals[c] * frac


def error_metrics(pairs: list[tuple[float, float]]) -> dict:
    """Compute error metrics from (forecast, actual) pairs.

    error = forecast - actual. Positive error means over-forecast (shortfall risk).

    Args:
        pairs: List of (forecast, actual) tuples.

    Returns:
        Dict with n, mae, rmse, bias, nmae_pct, p50_abs, p90_abs, p95_abs,
        shortfall_p90. Empty input returns n=0 and None for other fields.
    """
    if not pairs:
        return {
            "n": 0,
            "mae": None,
            "rmse": None,
            "bias": None,
            "nmae_pct": None,
            "p50_abs": None,
            "p90_abs": None,
            "p95_abs": None,
            "shortfall_p90": None,
        }

    n = len(pairs)
    errors = []
    abs_errors = []
    sum_error = 0.0
    sum_abs_error = 0.0
    sum_sq_error = 0.0
    sum_actual = 0.0

    for forecast, actual in pairs:
        err = forecast - actual
        errors.append(err)
        abs_err = abs(err)
        abs_errors.append(abs_err)
        sum_error += err
        sum_abs_error += abs_err
        sum_sq_error += err * err
        sum_actual += actual

    mae = sum_abs_error / n if n > 0 else 0.0
    bias = sum_error / n if n > 0 else 0.0
    rmse = math.sqrt(sum_sq_error / n) if n > 0 else 0.0
    mean_actual = sum_actual / n if n > 0 else 0.0
    if mean_actual == 0:
        nmae_pct = None
    else:
        nmae_pct = (mae / mean_actual) * 100.0

    p50_abs = percentile(abs_errors, 50)
    p90_abs = percentile(abs_errors, 90)
    p95_abs = percentile(abs_errors, 95)
    shortfall_p90 = percentile(errors, 90)  # P90 of signed error

    return {
        "n": n,
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "nmae_pct": nmae_pct,
        "p50_abs": p50_abs,
        "p90_abs": p90_abs,
        "p95_abs": p95_abs,
        "shortfall_p90": shortfall_p90,
    }


def horizon_bucket(horizon_h: float) -> float:
    """Return the bucket start for a given horizon in hours.

    Buckets are 6h wide: [0,6) ... [60,72).
    Returns the bucket start (float/int). Raises ValueError for horizon < 0.
    """
    if horizon_h < 0:
        raise ValueError("horizon_h must be >= 0")
    bucket_start = math.floor(horizon_h / 6.0) * 6.0
    return bucket_start


def conservative_forecast(forecast: float, shortfall_p90: float) -> tuple[float, float]:
    """Compute conservative forecast.

    conservative_forecast = max(0, forecast - max(shortfall_p90, 0))
    Returns (conservative_forecast, buffer) where buffer = forecast - conservative.
    """
    buffer_component = max(shortfall_p90, 0.0) if shortfall_p90 is not None else 0.0
    conservative = forecast - buffer_component
    if conservative < 0:
        conservative = 0.0
    buffer = forecast - conservative
    return conservative, buffer


def error_histogram(errors: list[float], bin_width: float) -> list[dict]:
    """Build histogram of errors.

    Returns list of {bin_start, bin_end, count}.
    """
    if not errors or bin_width <= 0:
        return []
    min_err = min(errors)
    max_err = max(errors)
    bin_start = math.floor(min_err / bin_width) * bin_width
    bins = []
    current = bin_start
    while current <= max_err + 1e-10:
        bin_end = current + bin_width
        count = sum(1 for e in errors if current <= e < bin_end)
        # If it's the last bin and there might be values at the edge
        if bin_end > max_err and abs(max_err - bin_end) >= 1e-10:  # not exact edge
            pass
        bins.append({"bin_start": current, "bin_end": bin_end, "count": count})
        current = bin_end
        if len(bins) > 10000:
            break
    # Fix last bin to include values equal to max_err if they ended up missed
    if bins:
        total_counted = sum(b["count"] for b in bins)
        if total_counted < len(errors):
            # Add remaining to last bin
            bins[-1]["count"] += (len(errors) - total_counted)
    return bins


def build_pairs_from_decision(
    decision_points: dict,
    hourly_actuals: dict,
) -> list[tuple[float, float]]:
    """Build (forecast, actual) pairs from decision-time forecasts and hourly actuals.

    Skips hours without an actual.
    """
    pairs = []
    for start_time, dp in decision_points.items():
        actual = None
        if start_time in hourly_actuals:
            actual = hourly_actuals[start_time]
        elif hasattr(dp, 'startTime') and dp.startTime in hourly_actuals:
            actual = hourly_actuals[dp.startTime]
        if actual is not None:
            if hasattr(dp, 'forecast'):
                pairs.append((dp.forecast, actual))
            else:
                # if it's just a tuple or different structure
                pass
    return pairs


def compute_metrics_by_horizon_bucket(
    forecasts: list[ForecastRow],
    hourly_actuals: dict,
) -> dict[float, dict]:
    """Group all forecast rows (horizon >= 0) by horizon bucket and compute error_metrics per bucket."""
    bucket_to_rows = {}
    for row in forecasts:
        horizon = (row.startTime - row.publishTime).total_seconds() / 3600.0
        if horizon < 0:
            continue
        b = horizon_bucket(horizon)
        if b not in bucket_to_rows:
            bucket_to_rows[b] = []
        bucket_to_rows[b].append(row)

    result = {}
    for b, rows in bucket_to_rows.items():
        pairs = []
        for row in rows:
            if row.startTime in hourly_actuals:
                pairs.append((row.generation, hourly_actuals[row.startTime]))
        result[b] = error_metrics(pairs)
    return result


def compute_decision_metrics_with_lookahead_rule(
    forecasts: list[ForecastRow],
    actuals_rows: list[ActualsRow],
    target_day: date,
    cutoff_time: str = "09:00",
) -> tuple[dict, bool]:
    """Apply no-look-ahead rule for decision day D.

    Stats for decision day D use only target days <= D-2;
    if fewer than 3 such days, fall back to all days and set in_sample=True.
    """
    hourly_actuals = build_hourly_actuals(actuals_rows)

    all_target_days = set()
    for row in forecasts:
        horizon = (row.startTime - row.publishTime).total_seconds() / 3600.0
        if horizon >= 0:
            all_target_days.add(row.startTime.date())

    allowed_days = set()
    for d in all_target_days:
        if d <= target_day - timedelta(days=2):
            allowed_days.add(d)

    in_sample = False
    if len(allowed_days) < 3:
        allowed_days = all_target_days.copy()
        in_sample = True

    all_pairs = []
    for d in allowed_days:
        decision_points = select_decision_forecast(forecasts, d, cutoff_time)
        pairs = build_pairs_from_decision(decision_points, hourly_actuals)
        all_pairs.extend(pairs)

    metrics = error_metrics(all_pairs)
    return metrics, in_sample


def group_by_horizon_bucket_forecasts(
    forecasts: list[ForecastRow],
) -> dict[float, list[ForecastRow]]:
    """Group all forecast rows (horizon >= 0) by horizon bucket."""
    bucket_to_rows = {}
    for row in forecasts:
        horizon = (row.startTime - row.publishTime).total_seconds() / 3600.0
        if horizon < 0:
            continue
        b = horizon_bucket(horizon)
        if b not in bucket_to_rows:
            bucket_to_rows[b] = []
        bucket_to_rows[b].append(row)
    return bucket_to_rows


# Keep old name for compatibility if needed
group_by_horizon_bucket = group_by_horizon_bucket_forecasts
