"""Agent endpoint tests with mocked LLM."""
import json
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from waraqah.core.db import init_db, get_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with a temporary database and mocked LLM."""
    db_path = str(tmp_path / "test_agent.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.delenv("AGENT_LLM_API_KEY", raising=False)

    import importlib
    import waraqah.core.config
    importlib.reload(waraqah.core.config)

    init_db(db_path)

    import waraqah.api.agent
    importlib.reload(waraqah.api.agent)
    import waraqah.api.main
    importlib.reload(waraqah.api.main)
    from waraqah.api.main import app

    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """Create a seeded database with known stock data."""
    db_path = str(tmp_path / "test_agent_seeded.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.delenv("AGENT_LLM_API_KEY", raising=False)

    import importlib
    import waraqah.core.config
    importlib.reload(waraqah.core.config)

    init_db(db_path)

    test_stock_data = {
        "code": "2222",
        "name_en": "Aramco",
        "sector": "Energy",
        "price": 35.50,
        "ret_1w": 0.025,
        "ret_1m": 0.05,
        "ret_3m": 0.08,
        "ret_6m": 0.12,
        "ret_1y": 0.15,
        "sma200_flag": "above",
        "rsi14": 55.0,
        "vol_regime": "NORMAL",
        "maxdd_2y": -0.15,
        "momentum": 0.05,
        "info": {
            "pe": 12.5,
            "roe": 25.0,
            "div_yield": 6.5,
            "payout": 0.75,
            "market_cap": 7000000000000,
        },
    }

    test_stock_data_2 = {
        "code": "4190",
        "name_en": "Jarir",
        "sector": "Retail",
        "price": 150.0,
        "ret_1w": -0.015,
        "ret_1m": 0.03,
        "sma200_flag": "above",
        "rsi14": 48.0,
        "vol_regime": "NORMAL",
        "info": {
            "pe": 18.0,
            "roe": 30.0,
            "div_yield": 4.0,
        },
    }

    with get_db(db_path) as conn:
        conn.execute(
            "INSERT INTO snapshots (code, data, updated_at) VALUES (?, ?, ?)",
            ("2222", json.dumps(test_stock_data), "2024-01-01"),
        )
        conn.execute(
            "INSERT INTO snapshots (code, data, updated_at) VALUES (?, ?, ?)",
            ("4190", json.dumps(test_stock_data_2), "2024-01-01"),
        )
        conn.execute(
            "INSERT INTO macro_cache (symbol, price, change_1d, updated_at) VALUES (?, ?, ?, ?)",
            ("brent", 82.50, 0.5, "2024-01-01"),
        )
        conn.execute(
            "INSERT INTO macro_cache (symbol, price, change_1d, updated_at) VALUES (?, ?, ?, ?)",
            ("gold", 2050.0, 10.0, "2024-01-01"),
        )
        conn.commit()

    import waraqah.api.agent
    importlib.reload(waraqah.api.agent)
    import waraqah.api.main
    importlib.reload(waraqah.api.main)
    from waraqah.api.main import app

    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c, db_path


def parse_sse_events(response_text: str) -> list:
    """Parse SSE events from response text."""
    events = []
    current_event = {}
    for line in response_text.split("\n"):
        if line.startswith("event:"):
            current_event["type"] = line[6:].strip()
        elif line.startswith("data:"):
            try:
                current_event["data"] = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                current_event["data"] = line[5:].strip()
        elif line == "" and current_event:
            if current_event:
                events.append(current_event)
                current_event = {}
    return events


class TestAgentStreaming:
    """Test that agent returns streaming SSE responses."""

    def test_agent_returns_sse_stream(self, client):
        """Test that /agent/chat returns a streaming response."""
        response = client.post("/agent/chat", json={"message": "Hello"})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_agent_stream_has_events(self, client):
        """Test that SSE stream contains expected events."""
        response = client.post("/agent/chat", json={"message": "Market overview"})
        events = parse_sse_events(response.text)

        event_types = [e.get("type") for e in events]
        assert "start" in event_types
        assert "done" in event_types


class TestToolRouting:
    """Test that messages route to correct tools."""

    def test_symbol_routes_to_get_stock_profile(self, seeded_db):
        """Test that a stock symbol routes to get_stock_profile."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "Tell me about stock 2222",
            "symbol": "2222"
        })
        events = parse_sse_events(response.text)

        tool_calls = [e for e in events if e.get("type") == "tool_call"]
        assert len(tool_calls) >= 1
        assert any(tc["data"]["tool"] == "get_stock_profile" for tc in tool_calls)

    def test_portfolio_routes_to_portfolio_analysis(self, seeded_db):
        """Test that portfolio positions route to portfolio_analysis."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "Analyze my portfolio",
            "context": {
                "positions": [
                    {"symbol": "2222", "shares": 100, "avg_cost": 30.0},
                    {"symbol": "4190", "shares": 50, "avg_cost": 140.0},
                ]
            }
        })
        events = parse_sse_events(response.text)

        tool_calls = [e for e in events if e.get("type") == "tool_call"]
        assert any(tc["data"]["tool"] == "portfolio_analysis" for tc in tool_calls)

    def test_market_overview_routes_correctly(self, seeded_db):
        """Test that market overview message routes correctly."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "Give me a market overview"
        })
        events = parse_sse_events(response.text)

        tool_calls = [e for e in events if e.get("type") == "tool_call"]
        assert any(tc["data"]["tool"] == "market_overview" for tc in tool_calls)

    def test_compare_routes_to_compare_stocks(self, seeded_db):
        """Test that compare message with symbols routes to compare_stocks."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "Compare 2222 and 4190"
        })
        events = parse_sse_events(response.text)

        tool_calls = [e for e in events if e.get("type") == "tool_call"]
        assert any(tc["data"]["tool"] == "compare_stocks" for tc in tool_calls)

    def test_dividend_query_routes_correctly(self, seeded_db):
        """Test that dividend query with symbol routes to dividend_info."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "What is the dividend yield?",
            "symbol": "2222"
        })
        events = parse_sse_events(response.text)

        tool_calls = [e for e in events if e.get("type") == "tool_call"]
        assert any(tc["data"]["tool"] == "dividend_info" for tc in tool_calls)


class TestGroundingGuard:
    """Test that answers are grounded in tool results."""

    def test_stock_profile_numbers_match_seeded_data(self, seeded_db):
        """Test that tool returns exact numbers from seeded database."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "What is the price of 2222?",
            "symbol": "2222"
        })
        events = parse_sse_events(response.text)

        tool_results = [e for e in events if e.get("type") == "tool_result"]
        assert len(tool_results) >= 1

        profile_result = next(
            (r for r in tool_results if r["data"]["tool"] == "get_stock_profile"),
            None
        )
        assert profile_result is not None

        data = profile_result["data"]["data"]
        assert data["price"] == 35.50
        assert data["metrics"]["pe"] == 12.5
        assert data["metrics"]["div_yield"] == 6.5
        assert data["metrics"]["roe"] == 25.0

    def test_answer_cites_tool(self, seeded_db):
        """Test that the answer includes tool citation."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "Tell me about 2222",
            "symbol": "2222"
        })
        events = parse_sse_events(response.text)

        answer_event = next((e for e in events if e.get("type") == "answer"), None)
        assert answer_event is not None
        assert "tools_used" in answer_event["data"]
        assert len(answer_event["data"]["tools_used"]) > 0

    def test_portfolio_analysis_numbers_match(self, seeded_db):
        """Test that portfolio analysis returns correct calculations."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "Analyze my portfolio",
            "context": {
                "positions": [
                    {"symbol": "2222", "shares": 100, "avg_cost": 30.0},
                ]
            }
        })
        events = parse_sse_events(response.text)

        tool_results = [e for e in events if e.get("type") == "tool_result"]
        portfolio_result = next(
            (r for r in tool_results if r["data"]["tool"] == "portfolio_analysis"),
            None
        )
        assert portfolio_result is not None

        data = portfolio_result["data"]["data"]
        assert data["total_value"] == 3550.0
        assert data["total_cost"] == 3000.0
        assert data["total_pnl"] == 550.0

    def test_macro_data_from_cache(self, seeded_db):
        """Test that market overview uses seeded macro data."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "Market overview"
        })
        events = parse_sse_events(response.text)

        tool_results = [e for e in events if e.get("type") == "tool_result"]
        overview_result = next(
            (r for r in tool_results if r["data"]["tool"] == "market_overview"),
            None
        )
        assert overview_result is not None

        macro = overview_result["data"]["data"]["macro"]
        assert macro["brent"] == 82.50
        assert macro["gold"] == 2050.0


class TestLanguageDetection:
    """Test Arabic/English language detection."""

    def test_english_message_detected(self, client):
        """Test that English messages are detected correctly."""
        response = client.post("/agent/chat", json={
            "message": "What is the market doing today?"
        })
        events = parse_sse_events(response.text)

        start_event = next((e for e in events if e.get("type") == "start"), None)
        assert start_event is not None
        assert start_event["data"]["language"] == "en"

    def test_arabic_message_detected(self, client):
        """Test that Arabic messages are detected correctly."""
        response = client.post("/agent/chat", json={
            "message": "ما هو سعر سهم أرامكو؟"
        })
        events = parse_sse_events(response.text)

        start_event = next((e for e in events if e.get("type") == "start"), None)
        assert start_event is not None
        assert start_event["data"]["language"] == "ar"


class TestErrorHandling:
    """Test graceful error handling."""

    def test_unknown_symbol_handled(self, client):
        """Test that unknown symbols don't crash the agent."""
        response = client.post("/agent/chat", json={
            "message": "Tell me about 9999",
            "symbol": "9999"
        })
        assert response.status_code == 200
        events = parse_sse_events(response.text)

        done_event = next((e for e in events if e.get("type") == "done"), None)
        assert done_event is not None
        assert done_event["data"]["success"] is True

    def test_empty_message_handled(self, client):
        """Test that empty-ish messages are handled."""
        response = client.post("/agent/chat", json={
            "message": "..."
        })
        assert response.status_code == 200


class TestConfidenceBadge:
    """Test confidence field in answers."""

    def test_answer_has_confidence(self, seeded_db):
        """Test that answers include a confidence badge."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "Tell me about 2222",
            "symbol": "2222"
        })
        events = parse_sse_events(response.text)

        answer_event = next((e for e in events if e.get("type") == "answer"), None)
        assert answer_event is not None
        assert "confidence" in answer_event["data"]
        assert answer_event["data"]["confidence"] in ["low", "medium", "high"]


class TestGlobalSymbolDetection:
    """Test global vs Tadawul symbol detection."""

    def test_aapl_is_global(self):
        """Test that AAPL is detected as global."""
        from waraqah.api.agent import is_global_symbol
        assert is_global_symbol("AAPL") is True

    def test_reliance_ns_is_global(self):
        """Test that RELIANCE.NS is detected as global."""
        from waraqah.api.agent import is_global_symbol
        assert is_global_symbol("RELIANCE.NS") is True

    def test_7203_t_is_global(self):
        """Test that 7203.T (Toyota Japan) is detected as global."""
        from waraqah.api.agent import is_global_symbol
        assert is_global_symbol("7203.T") is True

    def test_shel_l_is_global(self):
        """Test that SHEL.L (Shell UK) is detected as global."""
        from waraqah.api.agent import is_global_symbol
        assert is_global_symbol("SHEL.L") is True

    def test_sap_de_is_global(self):
        """Test that SAP.DE (SAP Germany) is detected as global."""
        from waraqah.api.agent import is_global_symbol
        assert is_global_symbol("SAP.DE") is True

    def test_2222_is_tadawul(self):
        """Test that 2222 is detected as Tadawul."""
        from waraqah.api.agent import is_global_symbol
        assert is_global_symbol("2222") is False

    def test_2222_sr_is_tadawul(self):
        """Test that 2222.SR is detected as Tadawul."""
        from waraqah.api.agent import is_global_symbol
        assert is_global_symbol("2222.SR") is False

    def test_1120_is_tadawul(self):
        """Test that 1120 is detected as Tadawul."""
        from waraqah.api.agent import is_global_symbol
        assert is_global_symbol("1120") is False


class TestFetchGlobal:
    """Test fetch_global function with mocked yfinance."""

    def test_fetch_global_returns_snapshot_with_currency(self):
        """Test that fetch_global returns snapshot dict with price and currency."""
        import pandas as pd
        import numpy as np
        from unittest.mock import patch, MagicMock
        from datetime import datetime

        dates = pd.date_range(end=datetime.now(), periods=300, freq="D")
        closes = pd.Series(np.linspace(100, 150, 300), index=dates)
        hist_df = pd.DataFrame({"Close": closes})

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist_df
        mock_ticker.info = {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "currency": "USD",
            "trailingPE": 25.5,
            "returnOnEquity": 0.85,
            "dividendYield": 0.005,
        }

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            from waraqah.engine.fetcher import fetch_global
            result = fetch_global("AAPL")

        assert result is not None
        assert result["code"] == "AAPL"
        assert result["name_en"] == "Apple Inc."
        assert result["price"] is not None
        assert result["info"]["currency"] == "USD"

    def test_fetch_global_returns_none_on_failure(self):
        """Test that fetch_global returns None when ticker not found."""
        from unittest.mock import patch, MagicMock
        import pandas as pd

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()

        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            from waraqah.engine.fetcher import fetch_global
            result = fetch_global("INVALID_TICKER_XYZ")

        assert result is None


class TestCurrencyInference:
    """Test currency inference from symbol suffix."""

    def test_infer_currency_from_suffix_sr(self):
        """Test SAR currency for .SR suffix."""
        from waraqah.api.agent import infer_currency
        assert infer_currency("2222.SR") == "SAR"

    def test_infer_currency_from_suffix_ns(self):
        """Test INR currency for .NS suffix."""
        from waraqah.api.agent import infer_currency
        assert infer_currency("RELIANCE.NS") == "INR"

    def test_infer_currency_from_suffix_t(self):
        """Test JPY currency for .T suffix."""
        from waraqah.api.agent import infer_currency
        assert infer_currency("7203.T") == "JPY"

    def test_infer_currency_from_suffix_l(self):
        """Test GBp currency for .L suffix."""
        from waraqah.api.agent import infer_currency
        assert infer_currency("SHEL.L") == "GBp"

    def test_infer_currency_from_suffix_de(self):
        """Test EUR currency for .DE suffix."""
        from waraqah.api.agent import infer_currency
        assert infer_currency("SAP.DE") == "EUR"

    def test_infer_currency_default_usd(self):
        """Test USD default for US symbols."""
        from waraqah.api.agent import infer_currency
        assert infer_currency("AAPL") == "USD"

    def test_infer_currency_4digit_sar(self):
        """Test SAR for 4-digit Tadawul codes."""
        from waraqah.api.agent import infer_currency
        assert infer_currency("2222") == "SAR"

    def test_infer_currency_from_info(self):
        """Test that info.currency takes precedence."""
        from waraqah.api.agent import infer_currency
        assert infer_currency("AAPL", "EUR") == "EUR"


class TestBuildProfileDictCurrency:
    """Test build_profile_dict includes currency."""

    def test_build_profile_dict_tadawul_sar(self):
        """Test that Tadawul stock gets SAR currency."""
        from waraqah.api.agent import build_profile_dict
        data = {
            "code": "2222",
            "name_en": "Aramco",
            "price": 35.5,
            "info": {"pe": 12.5},
        }
        profile = build_profile_dict(data, is_global=False)
        assert profile["currency"] == "SAR"

    def test_build_profile_dict_global_usd(self):
        """Test that US stock gets USD currency."""
        from waraqah.api.agent import build_profile_dict
        data = {
            "code": "AAPL",
            "name_en": "Apple Inc.",
            "price": 150.0,
            "info": {"pe": 25.0, "currency": "USD"},
        }
        profile = build_profile_dict(data, is_global=True)
        assert profile["currency"] == "USD"

    def test_build_profile_dict_global_infers_from_suffix(self):
        """Test that global stock infers currency from suffix when not in info."""
        from waraqah.api.agent import build_profile_dict
        data = {
            "code": "RELIANCE.NS",
            "name_en": "Reliance Industries",
            "price": 2500.0,
            "info": {"pe": 20.0},
        }
        profile = build_profile_dict(data, is_global=True)
        assert profile["currency"] == "INR"


class TestDividendInfoCurrency:
    """Test tool_dividend_info includes currency."""

    def test_dividend_info_tadawul_has_currency(self, seeded_db):
        """Test that dividend info for Tadawul stock includes SAR currency."""
        client, _ = seeded_db
        response = client.post("/agent/chat", json={
            "message": "What is the dividend yield?",
            "symbol": "2222"
        })
        events = parse_sse_events(response.text)

        tool_results = [e for e in events if e.get("type") == "tool_result"]
        div_result = next(
            (r for r in tool_results if r["data"]["tool"] == "dividend_info"),
            None
        )
        assert div_result is not None
        assert div_result["data"]["data"]["currency"] == "SAR"
