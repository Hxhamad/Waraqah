"""CLI entry point: python -m waraqah.refresh"""
import argparse
import json
import os
from datetime import datetime

from waraqah.core.db import init_db, get_db
from waraqah.core.config import SYMBOLS_PATH
from waraqah.engine.fetcher import fetch_one, fetch_macro
from waraqah.engine.symbols import load_codes
from waraqah.api.alerts import evaluate_alerts


def refresh_symbols(codes: list, force: bool = False):
    """Refresh snapshot data for given symbols."""
    init_db()

    for code in codes:
        print(f"Fetching {code}...", end=" ")
        try:
            data = fetch_one(code)
            if data is None:
                print("FAILED (no data)")
                continue

            snapshot_data = {k: v for k, v in data.items()
                           if k not in ("annual_rows", "statement_rows")}

            with get_db() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO snapshots (code, data, updated_at) VALUES (?, ?, ?)",
                    (code, json.dumps(snapshot_data), datetime.utcnow().isoformat()),
                )
                conn.commit()
            print("OK")
        except Exception as e:
            print(f"FAILED ({e})")


def refresh_macro():
    """Refresh macro indicators."""
    print("Fetching macro indicators...", end=" ")
    try:
        data = fetch_macro()
        now = datetime.utcnow().isoformat()

        with get_db() as conn:
            for key, val in data.items():
                conn.execute(
                    "INSERT OR REPLACE INTO macro_cache (symbol, price, change_1d, updated_at) VALUES (?, ?, ?, ?)",
                    (key, val.get("price"), val.get("change_1d"), now),
                )
            conn.commit()
        print("OK")
    except Exception as e:
        print(f"FAILED ({e})")


def main():
    parser = argparse.ArgumentParser(description="Waraqah data refresh")
    parser.add_argument("--symbols", "-s", help="Comma-separated symbols to refresh")
    parser.add_argument("--all", "-a", action="store_true", help="Refresh all symbols from symbols.csv")
    parser.add_argument("--macro", "-m", action="store_true", help="Refresh macro indicators")
    parser.add_argument("--force", "-f", action="store_true", help="Force refresh even if cached")
    args = parser.parse_args()

    if args.macro or not (args.symbols or args.all):
        refresh_macro()

    if args.symbols:
        codes = [s.strip().replace(".SR", "") for s in args.symbols.split(",")]
        refresh_symbols(codes, args.force)
    elif args.all:
        if os.path.exists(SYMBOLS_PATH):
            codes = load_codes(SYMBOLS_PATH)
            refresh_symbols(codes, args.force)
        else:
            print(f"Symbols file not found: {SYMBOLS_PATH}")

    print("Evaluating alerts...")
    evaluate_alerts()
    print("Done.")


if __name__ == "__main__":
    main()
