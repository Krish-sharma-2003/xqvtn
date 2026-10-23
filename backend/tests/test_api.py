from fastapi.testclient import TestClient

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
