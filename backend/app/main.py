"""FastAPI application for the wind forecast decision support app.

Loads data once at startup into app.state. Handlers do no file I/O. CORS is
enabled for the Vite dev server origin http://localhost:5173.
"""

from __future__ import annotations

import math
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .align import build_hourly_actuals
from .decision import compute_cutoff, select_decision_forecast
from .loader import load_actuals, load_forecasts
from .metrics import (
    build_pairs_from_decision,
    compute_decision_metrics_with_lookahead_rule,
    compute_metrics_by_horizon_bucket,
    conservative_forecast,
    error_histogram,
    error_metrics,
)
from .schemas import (
    AccuracyByHourResponse,
    AccuracyByHorizonResponse,
    AccuracyDailyResponse,
    AccuracyErrorsResponse,
    AccuracyMetrics,
    AccuracySummaryResponse,
    CutoffSensitivityPoint,
    CutoffSensitivityResponse,
    DailyAccuracyRow,
    DecisionResponse,
    DecisionSummary,
    ErrorHistogramBin,
    HealthResponse,
    HorizonBucketMetrics,
    HourOfDayMetrics,
    HourlyPoint,
    MetaResponse,
)

TARGET_DAYS_START = date(2026, 1, 2)
TARGET_DAYS_END = date(2026, 2, 1)
DEFAULT_CUTOFF = "09:00"


def _parse_day(day: str) -> date:
    try:
        d = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=422, detail="day must be YYYY-MM-DD")
    if d < TARGET_DAYS_START or d > TARGET_DAYS_END:
        raise HTTPException(
            status_code=422,
            detail=f"day must be between {TARGET_DAYS_START} and {TARGET_DAYS_END}",
        )
    return d


def _validate_cutoff(cutoff: str) -> str:
    parts = cutoff.split(":")
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="cutoff must be HH:MM")
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        raise HTTPException(status_code=422, detail="cutoff must be HH:MM")
    if h > 23 or m > 59 or len(parts[0]) != 2 or len(parts[1]) != 2:
        raise HTTPException(status_code=422, detail="cutoff must be HH:MM")
    return cutoff


@asynccontextmanager
async def lifespan(app: FastAPI):
    actuals = load_actuals()
    forecasts = load_forecasts()
    app.state.actuals = actuals
    app.state.forecasts = forecasts
    app.state.hourly_actuals = build_hourly_actuals(actuals)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.get("/api/meta", response_model=MetaResponse)
def meta(request: Request):
    forecasts = request.app.state.forecasts
    actuals = request.app.state.actuals
    target_days = sorted(
        {r.startTime.date().isoformat() for r in forecasts
         if (r.startTime - r.publishTime).total_seconds() >= 0}
    )
    tds = [d for d in target_days if TARGET_DAYS_START.isoformat() <= d <= TARGET_DAYS_END.isoformat()]
    sample_day = date(2026, 1, 14)
    pts = sorted({r.publishTime for r in forecasts if r.publishTime.date() == sample_day})
    publish_times_per_day = [p.isoformat().replace("+00:00", "Z") for p in pts]
    data_ranges = {
        "actuals_start": min(a.startTime for a in actuals).isoformat().replace("+00:00", "Z"),
        "actuals_end": max(a.startTime for a in actuals).isoformat().replace("+00:00", "Z"),
        "forecasts_start": min(f.startTime for f in forecasts).isoformat().replace("+00:00", "Z"),
        "forecasts_end": max(f.startTime for f in forecasts).isoformat().replace("+00:00", "Z"),
    }
    return MetaResponse(
        target_days=tds,
        default_cutoff=DEFAULT_CUTOFF,
        publish_times_per_day=publish_times_per_day,
        data_ranges=data_ranges,
    )


@app.get("/api/decision", response_model=DecisionResponse)
def decision(
    request: Request,
    day: str = Query(...),
    cutoff: str = Query(DEFAULT_CUTOFF),
):
    d = _parse_day(day)
    c = _validate_cutoff(cutoff)
    forecasts = request.app.state.forecasts
    actuals_rows = request.app.state.actuals
    hourly_actuals = request.app.state.hourly_actuals

    points_map = select_decision_forecast(forecasts, d, c)
    bucket_metrics = compute_metrics_by_horizon_bucket(forecasts, hourly_actuals)

    points = []
    forecasts_list = []
    buffers = []
    for h in range(24):
        start = datetime(d.year, d.month, d.day, h, 0, tzinfo=timezone.utc)
        dp = points_map.get(start)
        actual = hourly_actuals.get(start)
        if dp is not None:
            forecast = dp.forecast
            publish_time = dp.publishTime
            horizon_h = dp.horizon_h
            bstart = math.floor(horizon_h / 6.0) * 6.0
            bm = bucket_metrics.get(bstart)
            sp90 = bm["shortfall_p90"] if (bm and bm.get("shortfall_p90") is not None) else 0.0
            cons, buf = conservative_forecast(forecast, sp90)
            forecasts_list.append(forecast)
            buffers.append(buf)
        else:
            forecast = None
            publish_time = None
            horizon_h = None
            cons = None
            buf = None
        points.append(HourlyPoint(
            startTime=start,
            forecast=forecast,
            publishTime=publish_time,
            horizon_h=horizon_h,
            actual=actual,
            conservative=cons,
            buffer=buf,
        ))

    _, in_sample = compute_decision_metrics_with_lookahead_rule(forecasts, actuals_rows, d, c)

    fmean = sum(forecasts_list) / len(forecasts_list) if forecasts_list else 0.0
    fmin = min(forecasts_list) if forecasts_list else 0.0
    fmax = max(forecasts_list) if forecasts_list else 0.0
    bmean = sum(buffers) / len(buffers) if buffers else 0.0
    cutoff_utc = compute_cutoff(d, c)

    return DecisionResponse(
        day=d.isoformat(),
        cutoff=c,
        points=points,
        summary=DecisionSummary(
            forecast_mean=fmean,
            forecast_min=fmin,
            forecast_max=fmax,
            buffer_mean=bmean,
            in_sample=in_sample,
            cutoff_utc=cutoff_utc,
        ),
    )


@app.get("/api/decision/cutoff-sensitivity", response_model=CutoffSensitivityResponse)
def cutoff_sensitivity(
    request: Request,
    day: str = Query(...),
):
    d = _parse_day(day)
    forecasts = request.app.state.forecasts
    cutoffs = []
    for h in range(6, 13):
        c = f"{h:02d}:00"
        pts_map = select_decision_forecast(forecasts, d, c)
        first = pts_map.get(datetime(d.year, d.month, d.day, 0, 0, tzinfo=timezone.utc))
        pt = first.publishTime if first else None
        vals = [p.forecast for p in pts_map.values()]
        mean_fc = (sum(vals) / len(vals)) if vals else None
        cutoffs.append(CutoffSensitivityPoint(cutoff=c, publishTime=pt, mean_forecast=mean_fc))
    return CutoffSensitivityResponse(day=d.isoformat(), cutoffs=cutoffs)


@app.get("/api/accuracy/summary", response_model=AccuracySummaryResponse)
def accuracy_summary(request: Request, cutoff: str = Query(DEFAULT_CUTOFF)):
    c = _validate_cutoff(cutoff)
    forecasts = request.app.state.forecasts
    hourly_actuals = request.app.state.hourly_actuals
    all_pairs = []
    for d in _target_days():
        pts = select_decision_forecast(forecasts, d, c)
        all_pairs.extend(build_pairs_from_decision(pts, hourly_actuals))
    m = error_metrics(all_pairs)
    return AccuracySummaryResponse(
        cutoff=c,
        in_sample=False,
        metrics=AccuracyMetrics(**m),
    )


@app.get("/api/accuracy/by-horizon", response_model=AccuracyByHorizonResponse)
def accuracy_by_horizon(request: Request):
    forecasts = request.app.state.forecasts
    hourly_actuals = request.app.state.hourly_actuals
    bm = compute_metrics_by_horizon_bucket(forecasts, hourly_actuals)
    buckets = []
    for b in sorted(bm.keys()):
        buckets.append(HorizonBucketMetrics(
            bucket_start=b,
            bucket_end=b + 6.0,
            metrics=AccuracyMetrics(**bm[b]),
        ))
    return AccuracyByHorizonResponse(buckets=buckets)


@app.get("/api/accuracy/by-hour", response_model=AccuracyByHourResponse)
def accuracy_by_hour(request: Request, cutoff: str = Query(DEFAULT_CUTOFF)):
    c = _validate_cutoff(cutoff)
    forecasts = request.app.state.forecasts
    hourly_actuals = request.app.state.hourly_actuals
    hour_pairs = {h: [] for h in range(24)}
    for d in _target_days():
        pts = select_decision_forecast(forecasts, d, c)
        for start, dp in pts.items():
            actual = hourly_actuals.get(start)
            if actual is not None:
                hour_pairs[start.hour].append((dp.forecast, actual))
    hours = []
    for h in range(24):
        m = error_metrics(hour_pairs[h])
        hours.append(HourOfDayMetrics(hour=h, metrics=AccuracyMetrics(**m)))
    return AccuracyByHourResponse(hours=hours)


@app.get("/api/accuracy/daily", response_model=AccuracyDailyResponse)
def accuracy_daily(request: Request, cutoff: str = Query(DEFAULT_CUTOFF)):
    c = _validate_cutoff(cutoff)
    forecasts = request.app.state.forecasts
    hourly_actuals = request.app.state.hourly_actuals
    days = []
    for d in _target_days():
        pts = select_decision_forecast(forecasts, d, c)
        pairs = build_pairs_from_decision(pts, hourly_actuals)
        m = error_metrics(pairs)
        days.append(DailyAccuracyRow(
            day=d.isoformat(),
            n=m["n"],
            mae=m["mae"],
            bias=m["bias"],
            nmae_pct=m["nmae_pct"],
        ))
    return AccuracyDailyResponse(days=days)


@app.get("/api/accuracy/errors", response_model=AccuracyErrorsResponse)
def accuracy_errors(request: Request, cutoff: str = Query(DEFAULT_CUTOFF)):
    c = _validate_cutoff(cutoff)
    forecasts = request.app.state.forecasts
    hourly_actuals = request.app.state.hourly_actuals
    errors = []
    for d in _target_days():
        pts = select_decision_forecast(forecasts, d, c)
        for start, dp in pts.items():
            actual = hourly_actuals.get(start)
            if actual is not None:
                errors.append(dp.forecast - actual)
    bin_width = 500.0
    bins_raw = error_histogram(errors, bin_width)
    bins = [ErrorHistogramBin(**b) for b in bins_raw]
    return AccuracyErrorsResponse(bin_width=bin_width, bins=bins)


def _target_days():
    d = TARGET_DAYS_START
    while d <= TARGET_DAYS_END:
        yield d
        d = d + timedelta(days=1)
