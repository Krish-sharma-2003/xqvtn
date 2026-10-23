# Wind Forecast Decision Support (UK day-ahead)

## Goal
A web app for a UK utility's day-ahead purchasing team. It must:
1. Show the latest national wind forecast available at decision time for a chosen target day.
2. Quantify forecast accuracy so the error can be factored into the purchase decision.
Scope: Elexon only (FUELHH fuelType=WIND actuals, WINDFOR forecasts). Decisions made in January 2026,
i.e. decision day D-1 in January, target days 2 Jan to 1 Feb 2026. No other data.

## Data (already in data/, produced by scripts/fetch_data.py)
- data/actuals.json: 1632 rows, 30-min. Fields: startTime, generation (MW), settlementDate, settlementPeriod, fuelType.
  Range 2025-12-31T00:00Z to 2026-02-02T23:30Z.
- data/forecasts.json: 18104 rows, hourly startTime. Fields: publishTime, startTime, generation (MW).
  248 publishes (8 per day), 2026-01-01T02:30Z to 2026-01-31T22:30Z.
- horizon = startTime - publishTime. Range -25.5h to 66.5h. Rows with horizon < 0 (3721) are excluded everywhere.
- All timestamps are UTC. January is GMT so UTC equals UK local time, but convert cutoffs with zoneinfo Europe/London.

## Definitions (single source of truth, implement exactly)
- Hourly actual for hour T = mean(actual[T], actual[T+30min]). If either is missing, hour is skipped.
- Cutoff for target day D = (D-1) at cutoff_time, default 09:00 Europe/London, configurable via query param.
  README must say the real market gate-closure time should be verified; the default is an assumption.
- Decision forecast for hour T = among rows with startTime=T, horizon>=0, publishTime<=cutoff, the one with max publishTime.
- error = forecast - actual (MW). Positive error = over-forecast = shortfall risk (less wind than planned).
- Metrics: MAE, RMSE, bias (mean error), nMAE (MAE / mean actual, in %), P50/P90/P95 of |error|,
  shortfall_p90 = P90 of the signed error (positive side of the distribution).
  Percentiles use linear interpolation. Document in README.
- Horizon buckets: 6h wide, [0,6) ... [60,72).
- Conservative forecast = max(0, forecast - shortfall_p90 of its horizon bucket). Buffer = forecast - conservative.
  (We have no demand data, so the app reports reliable wind volume; optional stretch: user enters demand MW and the app shows residual to buy.)
- No look-ahead: for decision page of day D, error stats use only target days <= D-2 (all forecast rows with horizon>=0, grouped by bucket).
  If fewer than 3 such days, fall back to all-January stats and return in_sample=true (UI shows a warning chip).

## API (FastAPI, all routes under /api, data loaded once at startup)
- GET /api/meta: target days available, default cutoff, publish times per day, data ranges.
- GET /api/decision?day=YYYY-MM-DD&cutoff=HH:MM: 24 hourly points {startTime, forecast, publishTime, horizon_h, actual|null, conservative, buffer}
  plus summary {forecast_mean, forecast_min, forecast_max, buffer_mean, in_sample, cutoff_utc}.
- GET /api/decision/cutoff-sensitivity?day=YYYY-MM-DD: for cutoffs 06:00 to 12:00 (hourly), returns per cutoff the selected publishTime and the mean forecast, so the user sees how the cutoff choice changes the decision.
- GET /api/accuracy/summary?cutoff=HH:MM: metrics of decision-time forecasts over all January target days.
- GET /api/accuracy/by-horizon: metrics per 6h bucket (all publishes, horizon>=0).
- GET /api/accuracy/by-hour: metrics per hour of day (decision-time forecasts).
- GET /api/accuracy/daily: per target day MAE, bias, nMAE (for worst-days table).
- GET /api/accuracy/errors: histogram bins of signed error (decision-time forecasts).
Validate inputs (day range, cutoff format) and return 422 with clear messages.

## Frontend (React + TypeScript + Vite + Recharts)
- Page 1 Decision: date picker (2 Jan to 1 Feb), cutoff input, chart (forecast line, conservative line, actual overlay behind a "show hindsight actuals" toggle),
  KPI cards (publish time used, mean forecast, mean buffer), table of the 24 hours, in_sample warning chip.
- Page 2 Accuracy: metric cards (MAE, RMSE, bias, nMAE), error-vs-horizon bar chart, hour-of-day chart, error histogram, worst-days table.
- Loading and error states everywhere. Responsive. Plain readable design, units (MW) on every axis.

## Repo layout
scripts/ (fetch_data.py, check_data.py), data/, backend/app/{main,loader,align,decision,metrics,schemas}.py, backend/tests/,
backend/requirements.txt, backend/Dockerfile, frontend/ (Vite app, Dockerfile), docker-compose.yml, api/index.py (Vercel entry), vercel.json, README.md.
Logic modules are pure functions (no I/O) so they are unit-testable. Only loader.py reads files. No pandas.

## Milestones (one commit each, do only the one requested)
- M0: print the 8 publish times of 2026-01-14 and the decision forecast horizon range for cutoff 09:00 (script only). 
- M1: loader.py, align.py, decision.py + pytest (cutoff picks latest publish <= cutoff, never a later one; hourly alignment; negative horizon excluded; missing handled).
- M2: metrics.py + pytest with hand-computed expected values.
- M3: main.py endpoints + API tests (FastAPI TestClient).
- M4: frontend scaffold + Decision page.
- M5: Accuracy page.
- M6: Dockerfiles + docker-compose (docker compose up works) + Vercel deploy (one project: static frontend + FastAPI under /api; make sure data/ is bundled; follow current Vercel docs).
- M7: README (files, how to start, deployed link, AI-tools disclosure, assumptions, metric definitions) + polish.