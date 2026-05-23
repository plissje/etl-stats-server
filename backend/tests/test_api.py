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


def test_balance_teams(client):
    req_body = {
        "players": [
            {"guid": "GUID_A", "name": "Player A", "team": "Axis"},
            {"guid": "GUID_B", "name": "Player B", "team": "Axis"},
            {"guid": "GUID_C", "name": "Player C", "team": "Allies"},
            {"guid": "GUID_D", "name": "Player D", "team": "Allies"},
        ],
        "variations": False
    }
    
    # Test deterministic balance
    r = client.post("/api/balancer/balance", json=req_body)
    assert r.status_code == 200, r.text
    res = r.json()
    assert "alpha" in res
    assert "beta" in res
    assert "diff" in res
    assert len(res["alpha"]) == 2
    assert len(res["beta"]) == 2
    
    # Test variations balance (reshuffle) with memory feedback
    req_body_var = {
        "players": [
            {"guid": "GUID_A", "name": "Player A", "team": "Axis"},
            {"guid": "GUID_B", "name": "Player B", "team": "Axis"},
            {"guid": "GUID_C", "name": "Player C", "team": "Allies"},
            {"guid": "GUID_D", "name": "Player D", "team": "Allies"},
        ],
        "variations": True
    }
    
    r_var = client.post("/api/balancer/balance", json=req_body_var)
    assert r_var.status_code == 200, r_var.text
    res_var = r_var.json()
    
    # Get the resulting guid sets
    alpha_guids = {p["guid"] for p in res_var["alpha"]}
    beta_guids = {p["guid"] for p in res_var["beta"]}
    
    # Check that it's NOT (A, B) and (C, D)
    is_same = (
        (alpha_guids == {"GUID_A", "GUID_B"} and beta_guids == {"GUID_C", "GUID_D"}) or
        (alpha_guids == {"GUID_C", "GUID_D"} and beta_guids == {"GUID_A", "GUID_B"})
    )
    assert not is_same, "Reshuffle should have avoided the identical partition!"

