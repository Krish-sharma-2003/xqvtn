# Deployment

## Docker (local)

```bash
docker-compose up --build
```

Then:

```bash
curl http://localhost:8080/api/health
curl "http://localhost:8080/api/decision?day=2026-01-15&cutoff=09:00"
```

Open http://localhost:8080.

## Vercel (one project, same domain)

1. Push this repository to GitHub.
2. In Vercel, **Add New Project** and import the GitHub repo.
3. Set **Framework Preset** to **Other**.
4. Set **Root Directory** to `.` (repository root).
5. Leave build settings as defined in `vercel.json` (`cd frontend && npm ci && npm run build`, output `frontend/dist`).
6. Add no environment variables.
7. Deploy.

Test the deployed URL:

```bash
URL=https://<your-deployment>.vercel.app
curl "$URL/api/health"
curl "$URL/api/decision?day=2026-01-15&cutoff=09:00"
```

Open `$URL` in a browser.

Notes:
- `api/index.py` exposes the FastAPI `app`; `/api/...` requests are rewritten to it.
- `data/` and `backend/` are bundled into the function via `includeFiles`.
- Python defaults to 3.12 on Vercel (`pyproject.toml`).
- Docs note: current Vercel docs prefer the FastAPI framework preset / Services for new apps. This project intentionally uses the `/api` file-based function approach with Framework Preset **Other** to match the repo layout in SPEC.md and keep the frontend build in `vercel.json`.
