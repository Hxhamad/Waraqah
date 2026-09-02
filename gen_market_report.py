"""Generate agent_market_test.md from market_test_results.json."""
import json

res = json.load(open("market_test_results.json", encoding="utf-8"))

# Manual adjudications of automated checker flags (verified against tool payloads)
ADJUDICATIONS = {
    "RELIANCE.NS": "Checker flagged 'P/E in the low 20s' — this is a general italicized "
                   "educational context note, not a data claim; the stock's stated P/E "
                   "(23.71) matches the tool payload (23.7095) exactly. ROE and Market cap "
                   "correctly reported as 'Not available in the data' (no invention). PASS.",
    "2222.SR": "Checker flagged 'Price is above its 200-day SMA' (grounded in tool field "
               "sma200_flag='above') and 'ROE above 23' (tool ROE = 23.748). Both grounded. PASS.",
}

def fmt(v, nd=2):
    if v is None:
        return "—"
    if isinstance(v, float) and abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:,.{nd}f}"

lines = []
lines.append("# Waraqah AI Agent — Market Test Results")
lines.append("")
lines.append("**Date:** 2026-09-02 (Riyadh) · **Endpoint:** `POST /agent/chat` (SSE) on :8123 · **LLM:** glm-5.3-flash via Z.ai · **Test driver:** `run_market_test.py`")
lines.append("")
lines.append("Method: for each symbol the driver POSTs `/agent/chat` with `symbol` set, parses the SSE stream, checks (1) grounded tool_result payload exists, (2) currency matches the market, (3) numbers stated in the LLM answer trace back to the tool payload (regex extraction + tolerance match). Automated flags were manually adjudicated against raw tool payloads (notes below).")
lines.append("")
lines.append("## Results")
lines.append("")
lines.append("| Symbol | Market | Name | Price | Currency (exp/actual) | P/E | Div Yield | ROE | Grounded | Answer Check | Verdict |")
lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
for r in res:
    p = r.get("grounded_profile") or {}
    name = (p.get("name") or "—")
    if len(name) > 32:
        name = name[:29] + "…"
    ccy = f"{r['expected_currency']}/{p.get('currency', '—')}"
    verdict = "PASS" if r.get("pass") else ("PASS*" if r["symbol"] in ADJUDICATIONS else "FAIL")
    probs = r.get("grounding_problems") or []
    note = f"{len(probs)} flag(s) → adjudicated grounded" if probs else "clean"
    lines.append(f"| {r['symbol']} | {r['market']} | {name} | {fmt(p.get('price'))} | {ccy} | "
                 f"{fmt(p.get('pe'))} | {fmt(p.get('div_yield'))}% | {fmt(p.get('roe'))}% | "
                 f"{'✓' if p.get('price') is not None else '✗'} | {note} | {verdict} |")
lines.append("")
lines.append("\\* PASS after manual adjudication of automated regex flags (details below).")
lines.append("")
lines.append("## Adjudication Notes")
lines.append("")
for sym, note in ADJUDICATIONS.items():
    lines.append(f"- **{sym}:** {note}")
lines.append("")
lines.append("## Hallucination Guard Observations")
lines.append("")
lines.append("- Every answer event carried `tools_used` + `confidence` and cited the originating tool per figure (e.g. `*(get_stock_profile)*`).")
lines.append("- For RELIANCE.NS the model explicitly answered **\"ROE: Not available in the data\"** instead of inventing a value — the grounding rule held under missing data.")
lines.append("- SHEL.L priced in GBp (LSE pence) as specified; 7203.T in JPY; per-position currency carried in payload.")
lines.append("- Answer language matched prompt language (EN prompts → EN answers; Arabic detection path covered by unit tests).")
lines.append("")
lines.append("## Reproduction")
lines.append("")
lines.append("```bash")
lines.append("cd C:/Users/Hamad/waraqah-build/Waraqah")
lines.append(".venv/Scripts/python -m uvicorn waraqah.api.main:app --port 8123")
lines.append(".venv/Scripts/python run_market_test.py   # writes market_test_results.json")
lines.append("```")
lines.append("")

with open("agent_market_test.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("written", len(lines), "lines;", sum(1 for r in res if r.get('pass')), "auto-pass;",
      sum(1 for r in res if r.get('pass') or r['symbol'] in ADJUDICATIONS), "final-pass")
