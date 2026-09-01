"""Dividend calendar and calculator endpoints."""
import json
from typing import List, Optional
from fastapi import APIRouter, Query

from waraqah.core.db import get_db
from waraqah.core.models import DividendEvent, DividendProjection

router = APIRouter(prefix="/dividends", tags=["dividends"])


@router.get("/calendar", response_model=List[DividendEvent])
def dividend_calendar(symbols: Optional[str] = Query(None)):
    """Get upcoming dividend events for watchlist/portfolio symbols."""
    events = []

    with get_db() as conn:
        if symbols:
            codes = [s.replace(".SR", "").strip() for s in symbols.split(",")]
        else:
            watchlist = conn.execute("SELECT symbol FROM watchlist").fetchall()
            codes = [r["symbol"] for r in watchlist]

        for code in codes:
            row = conn.execute(
                "SELECT data FROM snapshots WHERE code = ?", (code,)
            ).fetchone()
            if not row:
                continue
            try:
                data = json.loads(row["data"])
                info = data.get("info") or {}
                div_yield = info.get("div_yield") or info.get("div5y")
                if div_yield and div_yield > 0:
                    events.append(DividendEvent(
                        symbol=code,
                        ex_date=None,
                        amount=div_yield,
                    ))
            except Exception:
                continue

    return events


@router.get("/project", response_model=List[DividendProjection])
def project_dividends(
    symbols: str = Query(..., description="Comma-separated symbols"),
    shares: str = Query(..., description="Comma-separated share counts"),
    reinvest: bool = Query(True),
):
    """Project dividend income over 5 years with optional reinvestment."""
    codes = [s.replace(".SR", "").strip() for s in symbols.split(",")]
    share_counts = [float(s) for s in shares.split(",")]

    if len(codes) != len(share_counts):
        return []

    projections = []

    with get_db() as conn:
        for code, shares_count in zip(codes, share_counts):
            row = conn.execute(
                "SELECT data FROM snapshots WHERE code = ?", (code,)
            ).fetchone()
            if not row:
                continue
            try:
                data = json.loads(row["data"])
                info = data.get("info") or {}
                price = data.get("price") or 0
                div_yield_pct = info.get("div_yield") or info.get("div5y") or 0

                if price <= 0 or div_yield_pct <= 0:
                    continue

                annual_div_per_share = price * (div_yield_pct / 100)
                income_y1 = annual_div_per_share * shares_count

                income_y5_cumulative = income_y1 * 5

                if reinvest:
                    total_shares = shares_count
                    cumulative_with_reinvest = 0
                    for _ in range(5):
                        div_income = annual_div_per_share * total_shares
                        cumulative_with_reinvest += div_income
                        new_shares = div_income / price
                        total_shares += new_shares
                    income_y5_with_reinvest = cumulative_with_reinvest
                else:
                    income_y5_with_reinvest = income_y5_cumulative

                projections.append(DividendProjection(
                    symbol=code,
                    annual_dividend=round(annual_div_per_share, 4),
                    shares=shares_count,
                    income_year1=round(income_y1, 2),
                    income_year5_cumulative=round(income_y5_cumulative, 2),
                    income_year5_with_reinvestment=round(income_y5_with_reinvest, 2),
                ))
            except Exception:
                continue

    return projections
