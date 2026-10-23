"""Tests for :mod:`decision`."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.decision import compute_cutoff, select_decision_forecast
from app.loader import ForecastRow


def _row(start_iso: str, publish_iso: str, generation: float) -> ForecastRow:
    return ForecastRow(
        publishTime=datetime.fromisoformat(publish_iso),
        startTime=datetime.fromisoformat(start_iso),
        generation=generation,
    )


DAY = date(2026, 1, 15)  # a Thursday in January


def test_cutoff_winter_date_is_utc() -> None:
    # 2026-01-14 is winter: Europe/London is GMT (UTC+0), so 09:00 local = 09:00 UTC
    cutoff = compute_cutoff(DAY, "09:00")
    assert cutoff == datetime(2026, 1, 14, 9, 0, tzinfo=timezone.utc)


def test_cutoff_summer_date_is_bst() -> None:
    # 2026-07-15 is summer: Europe/London is BST (UTC+1), so 09:00 local = 08:00 UTC
    summer = date(2026, 7, 15)
    cutoff = compute_cutoff(summer, "09:00")
    assert cutoff == datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc)


def test_invalid_cutoff_string_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compute_cutoff(DAY, "not-a-time")
    with pytest.raises(ValueError):
        compute_cutoff(DAY, "25:00")
    with pytest.raises(ValueError):
        compute_cutoff(DAY, "9:0")  # wrong format


def test_picks_latest_publish_at_or_before_cutoff() -> None:
    hour = "2026-01-15T10:00:00+00:00"
    rows = [
        _row(hour, "2026-01-14T08:00:00+00:00", 100.0),  # older
        _row(hour, "2026-01-14T08:30:00+00:00", 110.0),  # latest <= cutoff
        _row(hour, "2026-01-14T09:30:00+00:00", 120.0),  # after cutoff -> excluded
    ]
    result = select_decision_forecast(rows, DAY, "09:00")
    assert set(result.keys()) == {datetime.fromisoformat(hour)}
    point = result[datetime.fromisoformat(hour)]
    assert point.forecast == 110.0
    assert point.publishTime == datetime.fromisoformat("2026-01-14T08:30:00+00:00")


def test_publish_exactly_equal_to_cutoff_is_included() -> None:
    hour = "2026-01-15T10:00:00+00:00"
    rows = [
        _row(hour, "2026-01-14T09:00:00+00:00", 150.0),  # exactly at cutoff
    ]
    result = select_decision_forecast(rows, DAY, "09:00")
    assert len(result) == 1
    assert result[datetime.fromisoformat(hour)].forecast == 150.0


def test_negative_horizon_rows_are_excluded() -> None:
    # publishTime after startTime -> negative horizon -> must be ignored
    hour = "2026-01-15T10:00:00+00:00"
    rows = [
        _row(hour, "2026-01-15T11:00:00+00:00", 999.0),  # published after the hour
    ]
    result = select_decision_forecast(rows, DAY, "09:00")
    assert result == {}


def test_hours_with_no_valid_forecast_are_omitted() -> None:
    rows = [
        _row("2026-01-15T10:00:00+00:00", "2026-01-14T08:00:00+00:00", 100.0),
        _row("2026-01-15T11:00:00+00:00", "2026-01-15T12:00:00+00:00", 999.0),  # neg horizon
    ]
    result = select_decision_forecast(rows, DAY, "09:00")
    assert set(result.keys()) == {datetime.fromisoformat("2026-01-15T10:00:00+00:00")}


def test_horizon_hours_are_reported() -> None:
    hour = "2026-01-15T14:00:00+00:00"
    rows = [_row(hour, "2026-01-14T08:00:00+00:00", 50.0)]  # 30h ahead
    result = select_decision_forecast(rows, DAY, "09:00")
    point = result[datetime.fromisoformat(hour)]
    assert point.horizon_h == 30.0


def test_rows_outside_target_day_are_ignored() -> None:
    rows = [
        _row("2026-01-16T10:00:00+00:00", "2026-01-14T08:00:00+00:00", 100.0),
    ]
    assert select_decision_forecast(rows, DAY, "09:00") == {}