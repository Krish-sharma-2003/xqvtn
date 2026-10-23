"""Pydantic response models for the wind forecast decision API.

These models describe the JSON shape of every endpoint so the OpenAPI docs
(/docs) are accurate and the client can rely on a stable contract. All
timestamps are timezone-aware UTC datetimes; FastAPI serialises them as
ISO-8601 with a trailing ``Z``.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# Shared model config: timezone-aware datetimes, no arbitrary types.
_MODEL_CONFIG = ConfigDict(
    from_attributes=True,
    populate_by_name=True,
    json_schema_extra={"example": None},
)


class HourlyPoint(BaseModel):
    """One hourly decision point returned by ``/api/decision``.

    All forecast-side fields are nullable: an hour with no qualifying
    forecast (none published before the cutoff with a non-negative horizon)
    carries ``null`` for forecast/publishTime/horizon_h, while the actual is
    still reported when the hourly mean is available.
    """

    model_config = _MODEL_CONFIG

    startTime: datetime = Field(description="Hour start, UTC, timezone-aware.")
    forecast: float | None = Field(
        default=None, description="Decision-time forecast in MW, or null."
    )
    publishTime: datetime | None = Field(
        default=None, description="Publish time selected for this hour, UTC, or null."
    )
    horizon_h: float | None = Field(
        default=None, description="Horizon = startTime - publishTime in hours (>= 0), or null."
    )
    actual: float | None = Field(
        default=None, description="Hourly actual in MW, or null when unavailable."
    )
    conservative: float | None = Field(
        default=None, description="Conservative forecast = max(0, forecast - shortfall_p90) in MW."
    )
    buffer: float | None = Field(
        default=None, description="forecast - conservative in MW."
    )


class DecisionSummary(BaseModel):
    """Summary block returned alongside the 24 hourly points."""

    model_config = _MODEL_CONFIG

    forecast_mean: float = Field(description="Mean of the 24 hourly forecasts (MW).")
    forecast_min: float = Field(description="Minimum hourly forecast (MW).")
    forecast_max: float = Field(description="Maximum hourly forecast (MW).")
    buffer_mean: float = Field(description="Mean of the 24 hourly buffers (MW).")
    in_sample: bool = Field(
        description="True when error stats fall back to all-January data (fewer than 3 usable target days)."
    )
    cutoff_utc: datetime = Field(description="Decision cutoff as a UTC datetime.")


class DecisionResponse(BaseModel):
    """Response body for ``/api/decision``."""

    model_config = _MODEL_CONFIG

    day: str = Field(description="Target day, ISO-8601 date (YYYY-MM-DD).")
    cutoff: str = Field(description="Cutoff time as HH:MM (Europe/London).")
    points: list[HourlyPoint] = Field(description="24 hourly decision points.")
    summary: DecisionSummary


class CutoffSensitivityPoint(BaseModel):
    """One cutoff row returned by ``/api/decision/cutoff-sensitivity``."""

    model_config = _MODEL_CONFIG

    cutoff: str = Field(description="Cutoff time as HH:MM (Europe/London).")
    publishTime: datetime | None = Field(
        default=None, description="Publish time selected for this cutoff, or null if none."
    )
    mean_forecast: float | None = Field(
        default=None, description="Mean forecast across the 24 hours for this cutoff."
    )


class CutoffSensitivityResponse(BaseModel):
    """Response body for ``/api/decision/cutoff-sensitivity``."""

    model_config = _MODEL_CONFIG

    day: str = Field(description="Target day, ISO-8601 date (YYYY-MM-DD).")
    cutoffs: list[CutoffSensitivityPoint]


class AccuracyMetrics(BaseModel):
    """Error-metrics block (shared by several accuracy endpoints)."""

    model_config = _MODEL_CONFIG

    n: int = Field(description="Number of (forecast, actual) pairs.")
    mae: float | None = Field(default=None, description="Mean absolute error (MW).")
    rmse: float | None = Field(default=None, description="Root mean squared error (MW).")
    bias: float | None = Field(default=None, description="Mean signed error (MW).")
    nmae_pct: float | None = Field(default=None, description="MAE / mean actual, in percent.")
    p50_abs: float | None = Field(default=None, description="P50 of |error| (MW).")
    p90_abs: float | None = Field(default=None, description="P90 of |error| (MW).")
    p95_abs: float | None = Field(default=None, description="P95 of |error| (MW).")
    shortfall_p90: float | None = Field(
        default=None, description="P90 of the signed error (MW)."
    )


class AccuracySummaryResponse(BaseModel):
    """Response body for ``/api/accuracy/summary``."""

    model_config = _MODEL_CONFIG

    cutoff: str = Field(description="Cutoff time as HH:MM (Europe/London).")
    in_sample: bool = Field(description="Whether the stats use the all-January fallback.")
    metrics: AccuracyMetrics


class HorizonBucketMetrics(BaseModel):
    """Per-horizon-bucket metrics row."""

    model_config = _MODEL_CONFIG

    bucket_start: float = Field(description="Start of the 6h horizon bucket, e.g. 0.0 for [0,6).")
    bucket_end: float = Field(description="End of the 6h horizon bucket, e.g. 6.0.")
    metrics: AccuracyMetrics


class AccuracyByHorizonResponse(BaseModel):
    """Response body for ``/api/accuracy/by-horizon``."""

    model_config = _MODEL_CONFIG

    buckets: list[HorizonBucketMetrics]


class HourOfDayMetrics(BaseModel):
    """Per-hour-of-day metrics row."""

    model_config = _MODEL_CONFIG

    hour: int = Field(description="Hour of day, 0..23 (UTC).")
    metrics: AccuracyMetrics


class AccuracyByHourResponse(BaseModel):
    """Response body for ``/api/accuracy/by-hour``."""

    model_config = _MODEL_CONFIG

    hours: list[HourOfDayMetrics]


class DailyAccuracyRow(BaseModel):
    """One row of the daily accuracy table."""

    model_config = _MODEL_CONFIG

    day: str = Field(description="Target day, ISO-8601 date (YYYY-MM-DD).")
    n: int = Field(description="Number of hourly points with a matching actual.")
    mae: float | None = Field(default=None, description="Mean absolute error (MW).")
    bias: float | None = Field(default=None, description="Mean signed error (MW).")
    nmae_pct: float | None = Field(default=None, description="MAE / mean actual, in percent.")


class AccuracyDailyResponse(BaseModel):
    """Response body for ``/api/accuracy/daily``."""

    model_config = _MODEL_CONFIG

    days: list[DailyAccuracyRow]


class ErrorHistogramBin(BaseModel):
    """One histogram bin."""

    model_config = _MODEL_CONFIG

    bin_start: float = Field(description="Bin lower edge (MW).")
    bin_end: float = Field(description="Bin upper edge (MW).")
    count: int = Field(description="Number of errors in [bin_start, bin_end).")


class AccuracyErrorsResponse(BaseModel):
    """Response body for ``/api/accuracy/errors``."""

    model_config = _MODEL_CONFIG

    bin_width: float = Field(description="Width of each histogram bin (MW).")
    bins: list[ErrorHistogramBin]


class MetaResponse(BaseModel):
    """Response body for ``/api/meta``."""

    model_config = _MODEL_CONFIG

    target_days: list[str] = Field(description="Target days available, ISO-8601 dates.")
    default_cutoff: str = Field(description="Default decision cutoff, HH:MM Europe/London.")
    publish_times_per_day: list[str] = Field(
        description="Distinct publish times (UTC) seen on a single day."
    )
    data_ranges: dict[str, str] = Field(
        description="First/last startTime for actuals and forecasts."
    )


class HealthResponse(BaseModel):
    """Response body for ``/api/health``."""

    model_config = _MODEL_CONFIG

    status: str = Field(description="Service status, e.g. 'ok'.")