"""Decision-time forecast selection.

For a chosen target day ``D`` the purchasing team may only use forecasts that
were published before the market gate closes. That moment is modelled as a
*cutoff*: the day before ``D`` at a configurable local time (default 09:00
Europe/London). Any forecast published after the cutoff is "look-ahead" and
must be ignored, even if it is the most recent one.

This module is pure: it takes parsed forecast rows and a target day and
returns, for each hour of the target day, the best available forecast at
decision time (the latest publish that is not after the cutoff and whose
horizon is non-negative). Hours with no qualifying forecast are omitted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from zoneinfo import ZoneInfo

from .loader import ForecastRow

_LONDON = ZoneInfo("Europe/London")
_CUTOFF_RE = re.compile(r"^([0-2]?\d):([0-5]\d)$")


@dataclass(frozen=True)
class DecisionPoint:
    """The selected forecast for one hour of the target day."""

    startTime: datetime  # hour start, UTC, timezone-aware
    forecast: float  # MW
    publishTime: datetime  # the publish time that was selected
    horizon_h: float  # (startTime - publishTime) in hours, >= 0


def compute_cutoff(target_day: date, cutoff_time: str = "09:00") -> datetime:
    """Return the decision cutoff as a timezone-aware UTC datetime.

    The cutoff is ``target_day - 1 day`` at ``cutoff_time`` interpreted in
    Europe/London, converted to UTC. Using ``zoneinfo`` makes the conversion
    DST-safe: a winter date resolves to GMT (UTC+0) while a summer date
    resolves to BST (UTC+1).

    Args:
        target_day: The day whose purchases are being decided.
        cutoff_time: ``"HH:MM"`` string, e.g. ``"09:00"``.

    Raises:
        ValueError: If ``cutoff_time`` is not a valid ``HH:MM`` string or the
            time is outside 00:00-23:59.
    """
    match = _CUTOFF_RE.match(cutoff_time.strip())
    if not match:
        raise ValueError(
            f"Invalid cutoff_time {cutoff_time!r}: expected 'HH:MM' (e.g. '09:00')"
        )
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23:
        raise ValueError(f"Invalid cutoff_time {cutoff_time!r}: hour must be 0-23")

    previous = target_day - timedelta(days=1)
    local = datetime.combine(previous, time(hour, minute), tzinfo=_LONDON)
    return local.astimezone(timezone.utc)


def select_decision_forecast(
    forecasts: list[ForecastRow],
    target_day: date,
    cutoff_time: str = "09:00",
) -> dict:
    """Select the decision-time forecast for each hour of ``target_day``.

    For every whole hour ``T`` of ``target_day`` (00:00..23:00 UTC) this
    considers forecast rows with ``startTime == T``, a non-negative horizon
    (``startTime - publishTime >= 0``) and ``publishTime <= cutoff``. Among
    those it picks the row with the latest ``publishTime`` -- the freshest
    forecast that respects the decision cutoff. Hours with no qualifying
    row are omitted from the result.

    Args:
        forecasts: All forecast rows (e.g. from :func:`loader.load_forecasts`).
        target_day: The day to select forecasts for.
        cutoff_time: ``"HH:MM"`` Europe/London decision cutoff.

    Returns:
        A mapping ``hour-start datetime -> :class:`DecisionPoint``.
    """
    cutoff = compute_cutoff(target_day, cutoff_time)

    # Group qualifying rows by hour start; track the max publishTime per hour.
    best: dict[datetime, ForecastRow] = {}
    for row in forecasts:
        if row.startTime.date() != target_day:
            continue
        if row.startTime.minute != 0 or row.startTime.second != 0:
            continue
        horizon = row.startTime - row.publishTime
        if horizon < timedelta(0):
            continue  # negative horizon: published after the hour, excluded
        if row.publishTime > cutoff:
            continue  # published after the decision cutoff, not usable
        previous = best.get(row.startTime)
        if previous is None or row.publishTime > previous.publishTime:
            best[row.startTime] = row

    result: dict[datetime, DecisionPoint] = {}
    for start, row in best.items():
        horizon_h = (row.startTime - row.publishTime).total_seconds() / 3600.0
        result[start] = DecisionPoint(
            startTime=start,
            forecast=row.generation,
            publishTime=row.publishTime,
            horizon_h=horizon_h,
        )
    return result