# Wind Forecast Decision Support (UK day-ahead)

## What this is

UK day-ahead wind forecast decision support for a utility's purchasing team. It uses Elexon data only: FUELHH fuelType=WIND actuals and WINDFOR forecasts, for decisions made in January 2026 (decision day D-1 in January, target days 2 Jan to 1 Feb 2026). It shows the latest national wind forecast available at decision time for a chosen target day and quantifies forecast error so the error can be factored into the purchase decision.

## Live app

Live app: https://xqvtn.vercel.app. Interactive API docs are served by FastAPI at `/docs` in local development; on Vercel the function is mounted under `/api`, so `/docs` is not exposed there.

## AI tools used

Built with Nemotron 3 Ultra via OpenCode, Kilo Code in VS Code, and Claude for planning and code review. All code was reviewed and tested by the author; the backend ships with 42+ pytest tests.

## Architecture

```
Browser
   |
   v
React (Vite SPA)  -- HTTP /api/* -->  FastAPI (app.state)  -- in-memory -->  data/*.json
```

- `backend/app/loader.py`: the only module that reads files; resolves `DATA_DIR` (default `data/` relative to the repo) and parses JSON into typed UTC datetimes.
- `backend/app/align.py`: collapses 30-minute actuals into hourly means (T and T+30min), skipping any hour with a missing half.
- `backend/app/decision.py`: applies the cutoff (latest `publishTime` <= cutoff, non-negative horizon) to pick one forecast per target hour.
- `backend/app/metrics.py`: error metrics, linear-interpolation percentiles, 6-hour horizon buckets, conservative forecast, allowed stat days, histogram.
- `backend/app/main.py`: FastAPI app; loads data once at startup, exposes `/api/*` routes, validates inputs.
- `backend/app/schemas.py`: Pydantic response models that define the `/docs` contract.

## Key definitions and assumptions

- Hourly actual for hour T = mean of the two 30-minute values at T and T+30min; missing half => hour skipped.
- Decision cutoff for target day D = (D-1) at a configurable local time, default 09:00 Europe/London. This default is an assumption to verify against the real market gate closure; the cutoff is configurable and a cutoff-sensitivity view is provided.
- Decision forecast for hour T = among rows with `startTime = T`, horizon >= 0 and `publishTime <= cutoff`, the one with max `publishTime`.
- Rows with negative horizon are excluded everywhere (3721 of 18104).
- `error = forecast - actual` (MW); positive error = over-forecast = shortfall risk.
- Metrics: MAE, RMSE, bias (mean error), nMAE (MAE / mean actual, %), P50/P90/P95 of `|error|`, and `shortfall_p90` = P90 of the signed error. Percentiles use linear interpolation.
- Horizon buckets are 6 hours wide: [0,6), [6,12), ... [60,72).
- Conservative forecast = `max(0, forecast - shortfall_p90)` of its horizon bucket; buffer = forecast - conservative.
- No look-ahead: error stats for day D use only target days <= D-2. If fewer than 3 such days, fall back to all-January stats and set `in_sample = true` (warning chip in the UI).
- All timestamps are UTC (January is GMT, so UTC equals UK local time; cutoffs are still converted with zoneinfo Europe/London).

## API

| Endpoint | Query params | Purpose |
|---|---|---|
| `GET /api/health` | none | Service health check. |
| `GET /api/meta` | none | Target days, default cutoff, publish times per day, data ranges. |
| `GET /api/decision` | `day` (req), `cutoff` (def 09:00) | 24 hourly points + summary for a target day. |
| `GET /api/decision/cutoff-sensitivity` | `day` (req) | Per cutoff 06:00-12:00: selected publish time and mean forecast. |
| `GET /api/accuracy/summary` | `cutoff` (def 09:00) | Metrics of decision-time forecasts over all January target days. |
| `GET /api/accuracy/by-horizon` | none | Metrics per 6-hour horizon bucket (all publishes). |
| `GET /api/accuracy/by-hour` | `cutoff` (def 09:00) | Metrics per hour of day (decision-time forecasts). |
| `GET /api/accuracy/daily` | `cutoff` (def 09:00) | Per target day MAE, bias, nMAE. |
| `GET /api/accuracy/errors` | `cutoff` (def 09:00) | Histogram bins of signed error (decision-time forecasts). |

Inputs are validated (day range, cutoff format); invalid input returns 422 with a clear message.

## Files and directories

```
.
├── AGENTS.md
├── SPEC.md
├── README.md
├── DEPLOY.md
├── docker-compose.yml
├── vercel.json
├── pyproject.toml
├── .dockerignore
├── .gitignore
├── api/
│   └── index.py
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── conftest.py
│   ├── requirements.txt
│   ├── requirements-prod.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── align.py
│   │   ├── decision.py
│   │   ├── loader.py
│   │   ├── main.py
│   │   ├── metrics.py
│   │   └── schemas.py
│   └── tests/
│       ├── test_align.py
│       ├── test_api.py
│       ├── test_decision.py
│       └── test_metrics.py
├── data/
│   ├── actuals.json
│   └── forecasts.json
├── frontend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .gitignore
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── .oxlintrc.json
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── App.css
│       ├── index.css
│       ├── styles.css
│       ├── api.ts
│       ├── types.ts
│       ├── components/
│       │   ├── CardHeader.tsx
│       │   ├── ChartCard.tsx
│       │   ├── Chip.tsx
│       │   ├── ErrorState.tsx
│       │   ├── KpiCard.tsx
│       │   ├── Loading.tsx
│       │   ├── chartAxis.ts
│       │   └── chartTheme.ts
│       └── pages/
│           ├── Accuracy.tsx
│           └── Decision.tsx
└── scripts/
    ├── check_data.py
    ├── fetch_data.py
    └── m0_decision_probe.py
```

## How to start

Docker:

```bash
docker compose up --build
```

Then open http://localhost:8080.

Local dev, backend (from repo root):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --port 8000
```

Local dev, frontend:

```bash
cd frontend
npm ci
npm run dev
```

Then open http://localhost:5173.

Tests:

```bash
cd backend && python -m pytest -q
```

Refreshing data (no API key needed, run from repo root):

```bash
python scripts/fetch_data.py
```

## Deployment

- Vercel is configured by `vercel.json`: build `cd frontend && npm ci && npm run build`, output `frontend/dist`.
- `api/index.py` adds `backend/` to `sys.path` and re-exports the FastAPI `app`.
- `functions.api/index.py.includeFiles` bundles `data/**` and `backend/**` into the function.
- Rewrites send `/api/(.*)` to `/api/index` and `/(.*)` to `/index.html`.
- Framework Preset is Other, root directory is `.`; no environment variables are required.

## Limitations and next steps

Limitations: wind only, national level, one month of decisions (January 2026), no demand data, and in-sample error stats for the first target days (Jan 2-5). Next steps: add demand input to show residual volume to buy, apply a bias-adjusted forecast, and use a rolling error window instead of fixed January stats.
