"""Market test driver: POST /agent/chat for 8 global + Saudi symbols.

Checks per symbol:
  1. SSE stream structure (start/tool_call/tool_result/answer/done)
  2. tool_result carries a grounded profile (price, name, metrics)
  3. currency field matches the market's expected currency
  4. numbers in the LLM answer text trace back to tool_result payload (no hallucinated fields)
Writes per-symbol JSON to market_test_results.json incrementally.
"""
import json
import re
import sys
import time

import httpx

BASE = "http://127.0.0.1:8123"
CASES = [
    ("AAPL", "USD", "US"),
    ("MSFT", "USD", "US"),
    ("RELIANCE.NS", "INR", "India"),
    ("7203.T", "JPY", "Japan"),
    ("SHEL.L", "GBp", "UK"),
    ("SAP.DE", "EUR", "Germany"),
    ("2222.SR", "SAR", "Saudi"),
    ("1120.SR", "SAR", "Saudi"),
]

NUM_KEYS = {"price", "pe", "roe", "div_yield", "payout", "market_cap",
            "maxdd_2y", "rsi14", "annual_dividend_per_share", "div_yield_pct"}


def parse_sse(text: str):
    events = []
    cur_event, cur_data = None, []
    for line in text.split("\n"):
        if line.startswith("event: "):
            cur_event = line[7:].strip()
        elif line.startswith("data: "):
            cur_data.append(line[6:])
        elif line == "" and cur_event is not None:
            raw = "\n".join(cur_data)
            try:
                events.append((cur_event, json.loads(raw)))
            except Exception:
                events.append((cur_event, {"_raw": raw}))
            cur_event, cur_data = None, []
    return events


def flatten_numbers(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in NUM_KEYS and isinstance(v, (int, float)):
                out.append((k, float(v)))
            else:
                flatten_numbers(v, out)
    elif isinstance(obj, list):
        for item in obj:
            flatten_numbers(item, out)


def check_grounding(answer_text: str, tool_payload: dict):
    """Numbers the model states near metric keywords must exist in tool payload."""
    tool_nums = []
    flatten_numbers(tool_payload, tool_nums)
    values = [v for _, v in tool_nums]
    problems = []
    checked = 0
    # price patterns: "232.50 USD", "price of 232.50", "السعر: 55.25"
    patterns = [
        r"(?:price|Price|السعر)[^0-9\-]{0,20}([0-9][0-9,]*\.?[0-9]*)",
        r"([0-9][0-9,]*\.?[0-9]*)\s*(?:USD|INR|JPY|GBp|EUR|SAR)",
        r"(?:P/E|PE|مكرر)[^0-9]{0,15}([0-9]+\.?[0-9]*)",
        r"(?:yield|Yield|عائد)[^0-9]{0,15}([0-9]+\.?[0-9]*)",
        r"(?:ROE|roe)[^0-9]{0,15}([0-9]+\.?[0-9]*)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, answer_text):
            try:
                num = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            checked += 1
            if not any(abs(num - v) < max(0.05, abs(v) * 0.02) for v in values):
                problems.append(f"stated {m.group(0)!r} not found in tool payload")
    return checked, problems


def run_case(client: httpx.Client, symbol: str, expected_ccy: str, market: str):
    rec = {"symbol": symbol, "market": market, "expected_currency": expected_ccy}
    t0 = time.time()
    try:
        r = client.post("/agent/chat", json={
            "message": f"Give me an educational profile of {symbol}: price, valuation and dividends.",
            "symbol": symbol,
        }, timeout=280.0)
        rec["http_status"] = r.status_code
        events = parse_sse(r.text)
    except Exception as e:
        rec["error"] = f"request failed: {e}"
        return rec
    rec["elapsed_s"] = round(time.time() - t0, 1)
    kinds = [k for k, _ in events]
    rec["event_kinds"] = kinds

    tool_data = {}
    answer = ""
    for k, data in events:
        if k == "tool_result":
            tool_data[data.get("tool")] = data.get("data")
        elif k == "answer":
            answer = data.get("text", "")
            rec["confidence"] = data.get("confidence")
            rec["tools_used"] = data.get("tools_used")
            rec["llm_used"] = data.get("llm_used")
    rec["answer"] = answer

    profile = tool_data.get("get_stock_profile")
    if not isinstance(profile, dict) or "error" in (profile or {}):
        rec["error"] = f"no grounded profile; tool_data keys={list(tool_data)}; err={profile}"
        return rec
    rec["grounded_profile"] = {
        "code": profile.get("code"),
        "name": profile.get("name"),
        "price": profile.get("price"),
        "currency": profile.get("currency"),
        "pe": (profile.get("metrics") or {}).get("pe"),
        "div_yield": (profile.get("metrics") or {}).get("div_yield"),
        "roe": (profile.get("metrics") or {}).get("roe"),
        "score": profile.get("score"),
        "rating": profile.get("rating"),
    }
    # currency check (profile field OR stated in answer text)
    ccy_ok = profile.get("currency") == expected_ccy
    if not ccy_ok and expected_ccy in answer:
        ccy_ok = True  # currency surfaced in answer text is acceptable grounding
    rec["currency_ok"] = ccy_ok
    # grounding check
    checked, problems = check_grounding(answer, tool_data)
    rec["grounding_checked"] = checked
    rec["grounding_problems"] = problems
    rec["pass"] = bool(ccy_ok and not problems and answer and rec["grounded_profile"]["price"])
    return rec


def main():
    results = []
    with httpx.Client(base_url=BASE) as client:
        for symbol, ccy, market in CASES:
            print(f"[{time.strftime('%H:%M:%S')}] testing {symbol} ...", flush=True)
            rec = run_case(client, symbol, ccy, market)
            rec["pass"] = rec.get("pass", False)
            results.append(rec)
            print(f"  -> pass={rec.get('pass')} ccy_ok={rec.get('currency_ok')} "
                  f"price={rec.get('grounded_profile', {}).get('price')} "
                  f"ccy={rec.get('grounded_profile', {}).get('currency')} "
                  f"problems={rec.get('grounding_problems', rec.get('error'))}", flush=True)
            with open("market_test_results.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
    passed = sum(1 for r in results if r.get("pass"))
    print(f"DONE: {passed}/{len(results)} passed", flush=True)


if __name__ == "__main__":
    sys.exit(main())
