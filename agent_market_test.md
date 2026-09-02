# Waraqah AI Agent — Market Test Results

**Date:** 2026-09-02 (Riyadh) · **Endpoint:** `POST /agent/chat` (SSE) on :8123 · **LLM:** glm-5.3-flash via Z.ai · **Test driver:** `run_market_test.py`

Method: for each symbol the driver POSTs `/agent/chat` with `symbol` set, parses the SSE stream, checks (1) grounded tool_result payload exists, (2) currency matches the market, (3) numbers stated in the LLM answer trace back to the tool payload (regex extraction + tolerance match). Automated flags were manually adjudicated against raw tool payloads (notes below).

## Results

| Symbol | Market | Name | Price | Currency (exp/actual) | P/E | Div Yield | ROE | Grounded | Answer Check | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| AAPL | US | Apple Inc. | 325.13 | USD/USD | 37.33 | 0.34% | 148.75% | ✓ | clean | PASS |
| MSFT | US | Microsoft Corporation | 501.02 | USD/USD | 27.90 | 0.72% | 34.04% | ✓ | clean | PASS |
| RELIANCE.NS | India | Reliance Industries Limited | 1,309 | INR/INR | 23.71 | 0.47% | —% | ✓ | 1 flag(s) → adjudicated grounded | PASS* |
| 7203.T | Japan | Toyota Motor Corporation | 3,143 | JPY/JPY | 8.94 | 3.08% | 12.40% | ✓ | clean | PASS |
| SHEL.L | UK | Shell plc | 3,432 | GBp/GBp | 10.28 | 3.46% | 14.34% | ✓ | clean | PASS |
| SAP.DE | Germany | SAP SE | 190.90 | EUR/EUR | 27.58 | 1.31% | 18.32% | ✓ | clean | PASS |
| 2222.SR | Saudi | Saudi Arabian Oil Company | 26.06 | SAR/SAR | 15.49 | 5.21% | 23.75% | ✓ | 2 flag(s) → adjudicated grounded | PASS* |
| 1120.SR | Saudi | Al Rajhi Banking and Investme… | 67.45 | SAR/SAR | 16.11 | 3.46% | 18.52% | ✓ | clean | PASS |

\* PASS after manual adjudication of automated regex flags (details below).

## Adjudication Notes

- **RELIANCE.NS:** Checker flagged 'P/E in the low 20s' — this is a general italicized educational context note, not a data claim; the stock's stated P/E (23.71) matches the tool payload (23.7095) exactly. ROE and Market cap correctly reported as 'Not available in the data' (no invention). PASS.
- **2222.SR:** Checker flagged 'Price is above its 200-day SMA' (grounded in tool field sma200_flag='above') and 'ROE above 23' (tool ROE = 23.748). Both grounded. PASS.

## Hallucination Guard Observations

- Every answer event carried `tools_used` + `confidence` and cited the originating tool per figure (e.g. `*(get_stock_profile)*`).
- For RELIANCE.NS the model explicitly answered **"ROE: Not available in the data"** instead of inventing a value — the grounding rule held under missing data.
- SHEL.L priced in GBp (LSE pence) as specified; 7203.T in JPY; per-position currency carried in payload.
- Answer language matched prompt language (EN prompts → EN answers; Arabic detection path covered by unit tests).

## Reproduction

```bash
cd C:/Users/Hamad/waraqah-build/Waraqah
.venv/Scripts/python -m uvicorn waraqah.api.main:app --port 8123
.venv/Scripts/python run_market_test.py   # writes market_test_results.json
```
