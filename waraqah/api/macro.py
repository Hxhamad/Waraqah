"""Macro strip endpoint."""
from datetime import datetime
from fastapi import APIRouter

from waraqah.core.db import get_db
from waraqah.core.models import MacroStrip
from waraqah.engine.fetcher import fetch_macro

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("", response_model=MacroStrip)
def get_macro():
    """Get macro indicators: Brent, Gold, USD/SAR, BTC, MSCI-KSA."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT price, change_1d, updated_at FROM macro_cache WHERE symbol = 'brent'"
        ).fetchone()

        if row:
            rows = conn.execute("SELECT symbol, price, change_1d FROM macro_cache").fetchall()
            data = {r["symbol"]: {"price": r["price"], "change_1d": r["change_1d"]} for r in rows}
            return MacroStrip(
                brent=data.get("brent", {}).get("price"),
                gold=data.get("gold", {}).get("price"),
                usd_sar=data.get("usd_sar", {}).get("price"),
                btc=data.get("btc", {}).get("price"),
                msci_ksa=data.get("msci_ksa", {}).get("price"),
                updated_at=row["updated_at"],
            )

    data = fetch_macro()
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        for key, val in data.items():
            conn.execute(
                "INSERT OR REPLACE INTO macro_cache (symbol, price, change_1d, updated_at) VALUES (?, ?, ?, ?)",
                (key, val.get("price"), val.get("change_1d"), now),
            )
        conn.commit()

    return MacroStrip(
        brent=data.get("brent", {}).get("price"),
        gold=data.get("gold", {}).get("price"),
        usd_sar=data.get("usd_sar", {}).get("price"),
        btc=data.get("btc", {}).get("price"),
        msci_ksa=data.get("msci_ksa", {}).get("price"),
        updated_at=now,
    )
