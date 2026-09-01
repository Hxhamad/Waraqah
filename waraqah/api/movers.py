"""Movers endpoint - top gainers and losers."""
import json
from fastapi import APIRouter, Query

from waraqah.core.db import get_db
from waraqah.core.models import Mover

router = APIRouter(prefix="/movers", tags=["movers"])


@router.get("")
def get_movers(limit: int = Query(10, le=50)):
    """Get top gainers and losers."""
    stocks = []

    with get_db() as conn:
        rows = conn.execute("SELECT code, data FROM snapshots").fetchall()

    for row in rows:
        try:
            data = json.loads(row["data"])
            change = data.get("ret_1w")
            if change is not None:
                stocks.append({
                    "symbol": data.get("code"),
                    "name": data.get("name_en"),
                    "price": data.get("price"),
                    "change_pct": round(change * 100, 2),
                })
        except Exception:
            continue

    sorted_stocks = sorted(stocks, key=lambda x: x["change_pct"], reverse=True)

    gainers = sorted_stocks[:limit]
    losers = sorted_stocks[-limit:][::-1]

    return {
        "gainers": [Mover(**s) for s in gainers],
        "losers": [Mover(**s) for s in losers],
    }
