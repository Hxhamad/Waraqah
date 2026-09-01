"""Watchlist and alerts endpoints."""
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException

from waraqah.core.db import get_db
from waraqah.core.models import WatchlistItem, AlertCreate, Alert

router = APIRouter(tags=["watchlist"])


@router.get("/watchlist", response_model=List[WatchlistItem])
def get_watchlist():
    """Get all watchlist items."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, symbol, added_at FROM watchlist ORDER BY added_at DESC"
        ).fetchall()
    return [WatchlistItem(id=r["id"], symbol=r["symbol"], added_at=r["added_at"]) for r in rows]


@router.post("/watchlist/{symbol}")
def add_to_watchlist(symbol: str):
    """Add a symbol to watchlist."""
    code = symbol.replace(".SR", "").strip()
    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO watchlist (symbol, added_at) VALUES (?, ?)",
                (code, datetime.utcnow().isoformat()),
            )
            conn.commit()
        except Exception:
            raise HTTPException(status_code=400, detail="Symbol already in watchlist")
    return {"status": "added", "symbol": code}


@router.delete("/watchlist/{symbol}")
def remove_from_watchlist(symbol: str):
    """Remove a symbol from watchlist."""
    code = symbol.replace(".SR", "").strip()
    with get_db() as conn:
        conn.execute("DELETE FROM watchlist WHERE symbol = ?", (code,))
        conn.commit()
    return {"status": "removed", "symbol": code}


@router.get("/alerts", response_model=List[Alert])
def get_alerts():
    """Get all alerts."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, symbol, direction, target, triggered, created_at FROM alerts ORDER BY created_at DESC"
        ).fetchall()
    return [
        Alert(
            id=r["id"],
            symbol=r["symbol"],
            direction=r["direction"],
            target=r["target"],
            triggered=bool(r["triggered"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/alerts", response_model=Alert)
def create_alert(alert: AlertCreate):
    """Create a new price alert."""
    code = alert.symbol.replace(".SR", "").strip()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO alerts (symbol, direction, target, created_at) VALUES (?, ?, ?, ?)",
            (code, alert.direction, alert.target, datetime.utcnow().isoformat()),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, symbol, direction, target, triggered, created_at FROM alerts WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return Alert(
        id=row["id"],
        symbol=row["symbol"],
        direction=row["direction"],
        target=row["target"],
        triggered=bool(row["triggered"]),
        created_at=row["created_at"],
    )


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int):
    """Delete an alert."""
    with get_db() as conn:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
    return {"status": "deleted", "id": alert_id}


@router.get("/alerts/due", response_model=List[Alert])
def get_due_alerts():
    """Get alerts that have been triggered."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, symbol, direction, target, triggered, created_at FROM alerts WHERE triggered = 1"
        ).fetchall()
    return [
        Alert(
            id=r["id"],
            symbol=r["symbol"],
            direction=r["direction"],
            target=r["target"],
            triggered=True,
            created_at=r["created_at"],
        )
        for r in rows
    ]


def evaluate_alerts():
    """Evaluate all alerts against current prices."""
    with get_db() as conn:
        alerts = conn.execute(
            "SELECT id, symbol, direction, target FROM alerts WHERE triggered = 0"
        ).fetchall()

        for alert in alerts:
            row = conn.execute(
                "SELECT data FROM snapshots WHERE code = ?", (alert["symbol"],)
            ).fetchone()
            if not row:
                continue
            try:
                data = json.loads(row["data"])
                price = data.get("price")
            except Exception:
                continue

            if price is None:
                continue

            triggered = False
            if alert["direction"] == "above" and price >= alert["target"]:
                triggered = True
            elif alert["direction"] == "below" and price <= alert["target"]:
                triggered = True

            if triggered:
                conn.execute("UPDATE alerts SET triggered = 1 WHERE id = ?", (alert["id"],))

        conn.commit()
