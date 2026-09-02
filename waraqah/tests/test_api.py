"""API endpoint tests."""
import json
import os
import pytest
from fastapi.testclient import TestClient

from waraqah.core.db import init_db, get_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with a temporary database."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)

    import importlib
    import waraqah.core.config
    importlib.reload(waraqah.core.config)

    init_db(db_path)

    import waraqah.api.main
    importlib.reload(waraqah.api.main)
    from waraqah.api.main import app

    with TestClient(app) as c:
        yield c


class TestRootEndpoints:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Waraqah" in response.json()["name"]

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestScreener:
    def test_screener_empty(self, client):
        response = client.get("/screener")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "results" in data

    def test_screener_with_filters(self, client):
        response = client.get("/screener?pe_min=5&pe_max=25")
        assert response.status_code == 200


class TestWatchlist:
    def test_get_empty_watchlist(self, client):
        response = client.get("/watchlist")
        assert response.status_code == 200
        assert response.json() == []

    def test_add_to_watchlist(self, client):
        response = client.post("/watchlist/2222")
        assert response.status_code == 200
        assert response.json()["symbol"] == "2222"

    def test_remove_from_watchlist(self, client):
        client.post("/watchlist/2222")
        response = client.delete("/watchlist/2222")
        assert response.status_code == 200


class TestAlerts:
    def test_get_empty_alerts(self, client):
        response = client.get("/alerts")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_alert(self, client):
        response = client.post("/alerts", json={
            "symbol": "2222",
            "direction": "above",
            "target": 35.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "2222"
        assert data["direction"] == "above"
        assert data["target"] == 35.0

    def test_delete_alert(self, client):
        create_resp = client.post("/alerts", json={
            "symbol": "2222",
            "direction": "below",
            "target": 30.0
        })
        alert_id = create_resp.json()["id"]
        response = client.delete(f"/alerts/{alert_id}")
        assert response.status_code == 200

    def test_get_due_alerts(self, client):
        response = client.get("/alerts/due")
        assert response.status_code == 200


class TestPortfolio:
    def test_portfolio_analysis(self, client, tmp_path):
        db_path = str(tmp_path / "test.db")
        with get_db(db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO snapshots (code, data, updated_at) VALUES (?, ?, ?)",
                ("2222", json.dumps({"code": "2222", "price": 35.0, "vol_regime": "NORMAL"}), "2024-01-01"),
            )
            conn.execute(
                "INSERT OR REPLACE INTO snapshots (code, data, updated_at) VALUES (?, ?, ?)",
                ("4190", json.dumps({"code": "4190", "price": 150.0, "vol_regime": "NORMAL"}), "2024-01-01"),
            )
            conn.commit()

        response = client.post("/portfolio", json={
            "positions": [
                {"symbol": "2222", "shares": 100, "avg_cost": 30.0},
                {"symbol": "4190", "shares": 50, "avg_cost": 140.0},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "total_pnl" in data
        assert "positions" in data


class TestMovers:
    def test_get_movers(self, client):
        response = client.get("/movers")
        assert response.status_code == 200
        data = response.json()
        assert "gainers" in data
        assert "losers" in data


class TestDividends:
    def test_dividend_calendar(self, client):
        response = client.get("/dividends/calendar")
        assert response.status_code == 200

    def test_dividend_projection(self, client):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO snapshots (code, data, updated_at) VALUES (?, ?, ?)",
                ("2222", json.dumps({
                    "code": "2222",
                    "price": 35.0,
                    "info": {"div_yield": 5.0}
                }), "2024-01-01"),
            )
            conn.commit()

        response = client.get("/dividends/project?symbols=2222&shares=100")
        assert response.status_code == 200


class TestCompare:
    def test_compare_requires_two_symbols(self, client):
        response = client.get("/compare?symbols=2222")
        assert response.status_code == 400


class TestAgent:
    def test_agent_returns_streaming_response(self, client):
        response = client.post("/agent/chat", json={
            "message": "Hello"
        })
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
