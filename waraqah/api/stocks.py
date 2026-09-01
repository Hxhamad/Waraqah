"""Stock profile and compare endpoints."""
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Query

from waraqah.core.db import get_db
from waraqah.core.models import StockProfile
from waraqah.engine.metrics import composite_score, rating
from waraqah.engine.fetcher import fetch_one

router = APIRouter(prefix="/stock", tags=["stocks"])


def _get_snapshot(code: str):
    """Get snapshot from DB or fetch live."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT data FROM snapshots WHERE code = ?", (code,)
        ).fetchone()
        if row:
            return json.loads(row["data"])
    return None


def _build_profile(data: dict) -> StockProfile:
    info = data.get("info") or {}
    pe = info.get("pe")
    roe = info.get("roe")
    div_yield = info.get("div_yield") or info.get("div5y")
    tech_pair = (data.get("sma200_flag"), data.get("momentum"))
    maxdd = data.get("maxdd_2y")
    score = composite_score(pe, roe, div_yield, tech_pair, maxdd)

    return StockProfile(
        code=data.get("code"),
        name=data.get("name_en"),
        sector=data.get("sector"),
        price=data.get("price"),
        returns={
            "1W": data.get("ret_1w"),
            "1M": data.get("ret_1m"),
            "3M": data.get("ret_3m"),
            "6M": data.get("ret_6m"),
            "1Y": data.get("ret_1y"),
        },
        metrics={
            "pe": pe,
            "roe": roe,
            "div_yield": div_yield,
            "payout": info.get("payout"),
            "market_cap": info.get("market_cap"),
            "maxdd_2y": maxdd,
        },
        sma200_flag=data.get("sma200_flag"),
        rsi14=data.get("rsi14"),
        vol_regime=data.get("vol_regime"),
        news=data.get("news", []),
        score=score,
        rating=rating(score),
    )


@router.get("/{symbol}", response_model=StockProfile)
def get_stock(symbol: str):
    """Get stock profile with metrics and returns."""
    code = symbol.replace(".SR", "").strip()
    data = _get_snapshot(code)
    if not data:
        data = fetch_one(code)
        if not data:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO snapshots (code, data, updated_at) VALUES (?, ?, ?)",
                (code, json.dumps(data), datetime.utcnow().isoformat()),
            )
            conn.commit()
    return _build_profile(data)


compare_router = APIRouter(prefix="/compare", tags=["compare"])


@compare_router.get("")
def compare_stocks(symbols: str = Query(..., description="Comma-separated symbols")):
    """Compare multiple stocks side-by-side."""
    codes = [s.replace(".SR", "").strip() for s in symbols.split(",")]
    if len(codes) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 symbols")
    if len(codes) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 symbols")

    profiles = []
    for code in codes:
        data = _get_snapshot(code)
        if not data:
            data = fetch_one(code)
        if data:
            profiles.append(_build_profile(data))

    if len(profiles) < 2:
        raise HTTPException(status_code=404, detail="Not enough valid symbols found")

    return {
        "symbols": [p.code for p in profiles],
        "profiles": profiles,
        "comparison_matrix": {
            "price": {p.code: p.price for p in profiles},
            "pe": {p.code: p.metrics.get("pe") for p in profiles},
            "roe": {p.code: p.metrics.get("roe") for p in profiles},
            "div_yield": {p.code: p.metrics.get("div_yield") for p in profiles},
            "score": {p.code: p.score for p in profiles},
            "ret_1m": {p.code: p.returns.get("1M") for p in profiles},
            "ret_1y": {p.code: p.returns.get("1Y") for p in profiles},
        },
    }
