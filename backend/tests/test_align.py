"""Tests for :mod:`align`."""

from datetime import datetime, timezone

from app.align import build_hourly_actuals
from app.loader import ActualsRow


def _row(iso: str, generation: float) -> ActualsRow:
    return ActualsRow(
        startTime=datetime.fromisoformat(iso),
        generation=generation,
        settlementDate="2026-01-01",
        settlementPeriod=1,
        fuelType="WIND",
    )


def test_hourly_mean_of_two_half_hour_readings() -> None:
    rows = [
        _row("2026-01-01T00:00:00+00:00", 100.0),
        _row("2026-01-01T00:30:00+00:00", 140.0),
    ]
    hourly = build_hourly_actuals(rows)
    assert hourly == {datetime.fromisoformat("2026-01-01T00:00:00+00:00"): 120.0}


def test_hour_skipped_when_first_half_missing() -> None:
    rows = [
        _row("2026-01-01T00:30:00+00:00", 140.0),  # T+30 only, no T
        _row("2026-01-01T01:00:00+00:00", 200.0),
        _row("2026-01-01T01:30:00+00:00", 220.0),
    ]
    hourly = build_hourly_actuals(rows)
    # 00:00 skipped (no T reading); 01:00 = mean(200, 220) = 210
    assert hourly == {datetime.fromisoformat("2026-01-01T01:00:00+00:00"): 210.0}


def test_hour_skipped_when_second_half_missing() -> None:
    rows = [
        _row("2026-01-01T00:00:00+00:00", 100.0),  # T only, no T+30
        _row("2026-01-01T01:00:00+00:00", 200.0),
        _row("2026-01-01T01:30:00+00:00", 220.0),
    ]
    hourly = build_hourly_actuals(rows)
    assert hourly == {datetime.fromisoformat("2026-01-01T01:00:00+00:00"): 210.0}


def test_empty_input_returns_empty() -> None:
    assert build_hourly_actuals([]) == {}


def test_non_hour_start_readings_are_ignored() -> None:
    # A lone T+30 reading with no T partner must not create an hour entry.
    rows = [_row("2026-01-01T00:30:00+00:00", 140.0)]
    assert build_hourly_actuals(rows) == {}