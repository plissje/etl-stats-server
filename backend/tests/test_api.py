import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Import app after conftest env is set
from app.database import init_db
from app.main import app


@pytest.fixture
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_submit_unauthorized(client):
    r = client.post("/api/submit-stats", json={})
    assert r.status_code == 401


def test_submit_sample_simple(client):
    root = Path(__file__).resolve().parents[2]
    sample = root / "refs" / "sample_simple.json"
    data = json.loads(sample.read_text())
    r = client.post(
        "/api/submit-stats",
        json=data,
        headers={"Authorization": "Bearer testtoken"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True

    lst = client.get("/api/matches").json()
    assert len(lst) == 1
    mid = lst[0]["id"]

    detail = client.get(f"/api/matches/{mid}").json()
    assert detail["match"]["match_id"] == "1774216454"
    assert len(detail["axis"]) + len(detail["allies"]) == 2

    g = detail["axis"][0]["player_guid"] if detail["axis"] else detail["allies"][0]["player_guid"]
    prof = client.get(f"/api/players/{g}").json()
    assert prof["guid"]
    assert "current_rating" in prof
