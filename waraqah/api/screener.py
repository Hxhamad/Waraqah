"""Screener endpoint - filter stocks by metrics."""
import json
from typing import Optional
from fastapi import APIRouter, Query

from waraqah.core.db import get_db
from waraqah.engine.metrics import composite_score, rating

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("")
def screener(
    sector: Optional[str] = Query(None),
    pe_min: Optional[float] = Query(None),
    pe_max: Optional[float] = Query(None),
    div_yield_min: Optional[float] = Query(None),
    roe_min: Optional[float] = Query(None),
    rsi_min: Optional[float] = Query(None),
    rsi_max: Optional[float] = Query(None),
    trend: Optional[str] = Query(None, description="above or below SMA200"),
    score_min: Optional[float] = Query(None),
    limit: int = Query(50, le=200),
):
    """Screen stocks by various filters."""
    results = []

    with get_db() as conn:
        rows = conn.execute("SELECT code, data FROM snapshots").fetchall()

    for row in rows:
        try:
            data = json.loads(row["data"])
        except Exception:
            continue

        info = data.get("info") or {}
        pe = info.get("pe")
        roe = info.get("roe")
        div_yield = info.get("div_yield") or info.get("div5y")
        rsi = data.get("rsi14")
        sma_flag = data.get("sma200_flag")
        stock_sector = data.get("sector")

        tech_pair = (sma_flag, data.get("momentum"))
        maxdd = data.get("maxdd_2y")
        score = composite_score(pe, roe, div_yield, tech_pair, maxdd)

        if sector and stock_sector and sector.lower() not in stock_sector.lower():
            continue
        if pe_min is not None and (pe is None or pe < pe_min):
            continue
        if pe_max is not None and (pe is None or pe > pe_max):
            continue
        if div_yield_min is not None and (div_yield is None or div_yield < div_yield_min):
            continue
        if roe_min is not None and (roe is None or roe < roe_min):
            continue
        if rsi_min is not None and (rsi is None or rsi < rsi_min):
            continue
        if rsi_max is not None and (rsi is None or rsi > rsi_max):
            continue
        if trend and sma_flag != trend:
            continue
        if score_min is not None and score < score_min:
            continue

        results.append({
            "code": data.get("code"),
            "name": data.get("name_en"),
            "sector": stock_sector,
            "price": data.get("price"),
            "pe": pe,
            "roe": roe,
            "div_yield": div_yield,
            "rsi14": rsi,
            "sma200_flag": sma_flag,
            "score": score,
            "rating": rating(score),
        })

    results.sort(key=lambda x: x.get("score") or 0, reverse=True)
    return {"count": len(results), "results": results[:limit]}
