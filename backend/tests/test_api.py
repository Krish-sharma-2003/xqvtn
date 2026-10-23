from fastapi.testclient import TestClient
from datetime import date, datetime, timezone, timedelta

from app.main import app

client = TestClient(app)
client.__enter__()


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_decision_real():
    r = client.get("/api/decision?day=2026-01-15&cutoff=09:00")
    assert r.status_code == 200
    data = r.json()
    assert len(data["points"]) == 24
    first = data["points"][0]
    assert first["publishTime"] == "2026-01-14T07:30:00Z"


def test_422_day_out_of_range():
    r = client.get("/api/decision?day=2025-01-01&cutoff=09:00")
    assert r.status_code == 422


def test_422_bad_cutoff():
    r = client.get("/api/decision?day=2026-01-15&cutoff=99:99")
    assert r.status_code == 422


def test_accuracy_summary():
    r = client.get("/api/accuracy/summary?cutoff=09:00")
    assert r.status_code == 200
    data = r.json()
    assert data["metrics"]["n"] > 0


def test_accuracy_by_horizon():
    r = client.get("/api/accuracy/by-horizon")
    assert r.status_code == 200
    data = r.json()
    buckets = [b["bucket_start"] for b in data["buckets"]]
    assert all(0 <= b <= 66 for b in buckets)
    assert len(buckets) > 0


def test_accuracy_by_hour():
    r = client.get("/api/accuracy/by-hour?cutoff=09:00")
    assert r.status_code == 200
    data = r.json()
    assert len(data["hours"]) == 24


def test_accuracy_daily():
    r = client.get("/api/accuracy/daily?cutoff=09:00")
    assert r.status_code == 200
    data = r.json()
    assert len(data["days"]) > 0


def test_accuracy_errors():
    r = client.get("/api/accuracy/errors?cutoff=09:00")
    assert r.status_code == 200
    data = r.json()
    assert "bins" in data


def test_buffer_unchanged_when_future_actuals_modified():
    # Get baseline for 2026-01-20
    r1 = client.get("/api/decision?day=2026-01-20&cutoff=09:00")
    assert r1.status_code == 200
    data1 = r1.json()
    buffers1 = [p["buffer"] for p in data1["points"] if p["buffer"] is not None]
    summary_buffer1 = data1["summary"]["buffer_mean"]

    # Modify actuals for target days >= 2026-01-19
    hourly_actuals = app.state.hourly_actuals
    # Make a backup of keys we change
    changed = []
    # Modify all hourly actuals for days >= 2026-01-19
    for k, v in list(hourly_actuals.items()):
        if k.date() >= date(2026, 1, 19):
            changed.append((k, hourly_actuals[k]))
            hourly_actuals[k] = v * 0.5 + 1000.0  # big change

    # Clear cache for target days that might be affected
    if hasattr(app.state, "bucket_stats_by_day"):
        # Clear cache for all days to be safe
        app.state.bucket_stats_by_day = {}

    try:
        r2 = client.get("/api/decision?day=2026-01-20&cutoff=09:00")
        assert r2.status_code == 200
        data2 = r2.json()
        buffers2 = [p["buffer"] for p in data2["points"] if p["buffer"] is not None]
        summary_buffer2 = data2["summary"]["buffer_mean"]
        assert buffers1 == buffers2
        assert summary_buffer1 == summary_buffer2
    finally:
        # Restore
        for k, v in changed:
            hourly_actuals[k] = v
        if hasattr(app.state, "bucket_stats_by_day"):
            app.state.bucket_stats_by_day = {}


def test_in_sample_flags():
    r1 = client.get("/api/decision?day=2026-01-03&cutoff=09:00")
    assert r1.status_code == 200
    assert r1.json()["summary"]["in_sample"] is True

    r2 = client.get("/api/decision?day=2026-01-20&cutoff=09:00")
    assert r2.status_code == 200
    assert r2.json()["summary"]["in_sample"] is False
