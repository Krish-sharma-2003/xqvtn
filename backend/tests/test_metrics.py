"""Tests for :mod:`metrics`."""

from datetime import date, datetime, timedelta, timezone

import math
import pytest

from app.metrics import (
    percentile,
    error_metrics,
    horizon_bucket,
    conservative_forecast,
    error_histogram,
    build_pairs_from_decision,
    group_by_horizon_bucket,
    compute_metrics_by_horizon_bucket,
    compute_decision_metrics_with_lookahead_rule,
)
from app.decision import DecisionPoint
from app.loader import ForecastRow, ActualsRow


def test_percentile_linear_interpolation() -> None:
    # Test linear interpolation (NumPy default)
    values = [1, 2, 3, 4]
    # Median of 4 elements: (2+3)/2 = 2.5
    assert percentile(values, 50) == 2.5
    assert percentile([1, 2, 3], 50) == 2.0


def test_percentile_empty_raises() -> None:
    with pytest.raises(ValueError):
        percentile([], 50)


def test_percentile_single_value() -> None:
    assert percentile([5], 50) == 5.0
    assert percentile([10], 0) == 10.0
    assert percentile([10], 100) == 10.0


def test_error_metrics_basic() -> None:
    pairs = [(110, 100), (90, 100), (130, 100)]
    metrics = error_metrics(pairs)
    assert metrics["n"] == 3
    mae = (abs(10) + abs(-10) + abs(30)) / 3  # 50/3 = 16.666...
    assert abs(metrics["mae"] - mae) < 1e-9
    assert metrics["bias"] == 10.0  # (10 + (-10) + 30)/3
    expected_rmse = math.sqrt((100 + 100 + 900) / 3)
    assert abs(metrics["rmse"] - expected_rmse) < 1e-9


def test_error_metrics_empty() -> None:
    metrics = error_metrics([])
    assert metrics["n"] == 0
    assert metrics["mae"] is None
    assert metrics["rmse"] is None
    assert metrics["bias"] is None
    assert metrics["nmae_pct"] is None
    assert metrics["p50_abs"] is None
    assert metrics["p90_abs"] is None
    assert metrics["p95_abs"] is None
    assert metrics["shortfall_p90"] is None


def test_error_metrics_more_fields() -> None:
    pairs = [(110, 100), (90, 100), (130, 100)]
    metrics = error_metrics(pairs)
    assert "nmae_pct" in metrics
    assert "p50_abs" in metrics
    assert "p90_abs" in metrics
    assert "p95_abs" in metrics
    assert "shortfall_p90" in metrics
    mae = (abs(10) + abs(-10) + abs(30)) / 3
    mean_actual = (100 + 100 + 100) / 3  # all actuals are 100
    assert abs(metrics["nmae_pct"] - (mae / mean_actual * 100)) < 1e-9


def test_horizon_bucket() -> None:
    assert horizon_bucket(0) == 0
    assert horizon_bucket(5.99) == 0
    assert horizon_bucket(6) == 6
    assert horizon_bucket(66.5) == 66  # 66.5/6 = 11.083..., floor is 11, 11*6=66


def test_horizon_bucket_negative_raises() -> None:
    with pytest.raises(ValueError):
        horizon_bucket(-1)
    with pytest.raises(ValueError):
        horizon_bucket(-0.1)


def test_conservative_forecast_never_below_0() -> None:
    # forecast - max(shortfall_p90, 0)
    cons, buf = conservative_forecast(50, 10)
    assert cons == 40
    assert buf == 10
    cons, buf = conservative_forecast(50, 100)  # shortfall_p90 larger than forecast
    assert cons == 0  # max(0, 50 - max(100,0)) = max(0, -50) = 0
    assert buf == 50
    cons, buf = conservative_forecast(50, -5)  # shortfall_p90 negative
    assert cons == 50  # max(0, 50 - max(-5,0)) = max(0, 50) = 50
    assert buf == 0


def test_error_histogram() -> None:
    errors = [-10, -5, 0, 5, 10]
    hist = error_histogram(errors, bin_width=5)
    assert isinstance(hist, list)
    assert len(hist) > 0
    # Each element should have bin_start, bin_end, count
    for item in hist:
        assert "bin_start" in item
        assert "bin_end" in item
        assert "count" in item


def test_build_pairs_from_decision() -> None:
    hour = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
    dp = DecisionPoint(startTime=hour, forecast=100.0, publishTime=hour - timedelta(hours=24), horizon_h=24.0)
    decision_points = {hour: dp}
    hourly_actuals = {hour: 90.0}
    pairs = build_pairs_from_decision(decision_points, hourly_actuals)
    assert pairs == [(100.0, 90.0)]


def test_build_pairs_skips_missing_actual() -> None:
    hour = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
    dp = DecisionPoint(startTime=hour, forecast=100.0, publishTime=hour - timedelta(hours=24), horizon_h=24.0)
    decision_points = {hour: dp}
    hourly_actuals = {}  # missing actual
    pairs = build_pairs_from_decision(decision_points, hourly_actuals)
    assert pairs == []


def test_compute_metrics_by_horizon_bucket() -> None:
    # Create forecast rows with different horizons
    forecasts = []
    actuals_rows = []
    # For hour 2026-01-15T10:00:00Z, publish at 2026-01-15T08:00:00Z gives horizon 2h
    start = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
    pub = start - timedelta(hours=2)
    forecasts.append(ForecastRow(publishTime=pub, startTime=start, generation=100.0))
    # Add actuals for that hour
    actuals_rows.append(ActualsRow(startTime=start, generation=50.0, settlementDate="2026-01-15", settlementPeriod=20, fuelType="WIND"))
    actuals_rows.append(ActualsRow(startTime=start + timedelta(minutes=30), generation=50.0, settlementDate="2026-01-15", settlementPeriod=21, fuelType="WIND"))
    
    from app.align import build_hourly_actuals
    hourly_actuals = build_hourly_actuals(actuals_rows)
    result = compute_metrics_by_horizon_bucket(forecasts, hourly_actuals)
    assert 0 in result  # bucket for horizon 2h is [0,6)
    assert result[0]["n"] == 1


def test_look_ahead_fallback() -> None:
    # Create data where fewer than 3 days available for look-ahead rule
    forecasts = []
    actuals_rows = []
    target_day = date(2026, 1, 5)  # Want to predict day 5, need days <= 3 (so day 1,2,3) - only 3 days total possible
    # Add data for day 3 only (so days <= target_day-2 = 3 means day 3 is included if it's <= 3)
    for d in [3]:  # Only 1 day
        for h in range(24):
            start = datetime(2026, 1, d, h, 0, tzinfo=timezone.utc)
            pub = datetime(2026, 1, d-1, 8, 0, tzinfo=timezone.utc)  # published before cutoff
            forecasts.append(ForecastRow(publishTime=pub, startTime=start, generation=100.0))
            actuals_rows.append(ActualsRow(startTime=start, generation=90.0, settlementDate=f"2026-01-{d:02d}", settlementPeriod=h*2+1, fuelType="WIND"))
            actuals_rows.append(ActualsRow(startTime=start + timedelta(minutes=30), generation=90.0, settlementDate=f"2026-01-{d:02d}", settlementPeriod=h*2+2, fuelType="WIND"))
    
    metrics, in_sample = compute_decision_metrics_with_lookahead_rule(forecasts, actuals_rows, target_day, "09:00")
    # Fewer than 3 days, so should fall back to all days and set in_sample=True
    assert in_sample is True
