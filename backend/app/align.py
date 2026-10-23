"""Hourly alignment of 30-minute actuals.

The raw actuals are sampled every 30 minutes. A decision is made per whole
hour, so we collapse each pair of consecutive half-hour readings into a single
hourly value: the mean of the reading at the hour start (T) and the reading
30 minutes later (T+30min). If either half-hour is missing the hour is
skipped entirely -- we never interpolate across a gap, because a missing
reading would silently bias the mean.

This module contains only pure functions; it never touches the filesystem.
"""

from __future__ import annotations

from datetime import timedelta

from .loader import ActualsRow


def _index_by_time(rows: list[ActualsRow]) -> dict:
    """Map ``startTime`` -> ``generation`` for the given actuals rows."""
    return {row.startTime: row.generation for row in rows}


def build_hourly_actuals(rows: list[ActualsRow]) -> dict:
    """Return hourly actuals keyed by the hour-start datetime.

    For each whole hour ``T`` present in the data, the hourly value is the
    mean of ``actual[T]`` and ``actual[T + 30 minutes]``. The hour is omitted
    from the result when either of those two readings is missing.

    Args:
        rows: The 30-minute actuals (e.g. from :func:`loader.load_actuals`).

    Returns:
        A mapping ``hour_start_datetime -> mean generation in MW``. The keys
        are timezone-aware datetimes on whole-hour boundaries.
    """
    by_time = _index_by_time(rows)
    half_hour = timedelta(minutes=30)

    hourly: dict = {}
    # Only a reading taken exactly on the hour can start a pair.
    for start, generation in by_time.items():
        if start.minute != 0 or start.second != 0:
            continue
        later = start + half_hour
        if later not in by_time:
            continue
        hourly[start] = (generation + by_time[later]) / 2.0
    return hourly