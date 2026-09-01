"""Portfolio analysis endpoint."""
import json
from typing import List
from fastapi import APIRouter

from waraqah.core.db import get_db
from waraqah.core.models import PortfolioRequest, PortfolioAnalysis, PortfolioPosition
from waraqah.engine.fetcher import fetch_one

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _get_price(code: str):
    """Get price from DB or fetch."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT data FROM snapshots WHERE code = ?", (code,)
        ).fetchone()
        if row:
            data = json.loads(row["data"])
            return data.get("price"), data.get("vol_regime")
    data = fetch_one(code)
    if data:
        return data.get("price"), data.get("vol_regime")
    return None, None


@router.post("", response_model=PortfolioAnalysis)
def analyze_portfolio(request: PortfolioRequest):
    """Analyze a portfolio of positions."""
    positions_out = []
    total_value = 0.0
    total_cost = 0.0
    vol_regimes = []
    concentration_flags = []

    for pos in request.positions:
        code = pos.symbol.replace(".SR", "").strip()
        price, vol_regime = _get_price(code)

        cost_basis = pos.shares * pos.avg_cost
        market_value = pos.shares * price if price else None
        pnl = market_value - cost_basis if market_value else None
        pnl_pct = (pnl / cost_basis) if pnl and cost_basis else None

        positions_out.append(PortfolioPosition(
            symbol=code,
            shares=pos.shares,
            avg_cost=pos.avg_cost,
            price=price,
            market_value=market_value,
            cost_basis=cost_basis,
            pnl=round(pnl, 2) if pnl else None,
            pnl_pct=round(pnl_pct, 4) if pnl_pct else None,
            weight=None,
            vol_regime=vol_regime,
        ))

        if market_value:
            total_value += market_value
        total_cost += cost_basis
        if vol_regime:
            vol_regimes.append(vol_regime)

    for p in positions_out:
        if p.market_value and total_value > 0:
            p.weight = round(p.market_value / total_value, 4)
            if p.weight >= 0.40:
                concentration_flags.append(f"{p.symbol}: {p.weight*100:.1f}% >= 40% HARD CAP")
            elif p.weight >= 0.20:
                concentration_flags.append(f"{p.symbol}: {p.weight*100:.1f}% >= 20% guideline")

    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost if total_cost else 0

    portfolio_vol = "HIGH" if vol_regimes.count("HIGH") > len(vol_regimes) / 2 else "NORMAL"

    horizon_verdicts = {
        "near": "CAUTION" if portfolio_vol == "HIGH" else "OK",
        "mid": "OK" if len(positions_out) >= 5 else "UNDER-DIVERSIFIED",
        "long": "OK" if len(positions_out) >= 10 else "CONSIDER MORE POSITIONS",
    }

    return PortfolioAnalysis(
        positions=positions_out,
        total_value=round(total_value, 2),
        total_cost=round(total_cost, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl_pct, 4),
        concentration_flags=concentration_flags,
        vol_regime=portfolio_vol,
        horizon_verdicts=horizon_verdicts,
    )
