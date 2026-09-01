# Waraqah — Backend Build Specification (Claude Code / Opus 5 Ultra)
# Target repo: https://github.com/Hxhamad/Waraqah  (empty, public)
# Date: 2026-09-01. Builder: Claude Code (Opus 5 Ultra) via `claude -p`.

## MISSION
Build the **backend** for Waraqah: a stock analysis platform (Saudi market first,
global-ready) exposing the features below as a clean REST API. Clean, simple,
organized code. Backend only — a separate step covers the frontend.

## SOURCE ASSETS (reuse, do not rewrite)
- `C:/Users/Hamad/portfolio_excel/v2/` — production Excel engine (202 Saudi symbols):
  - `fetcher.py` — defensive yfinance .SR fetcher (2015+ annual matrix, statements,
    dividend depth). N/A-tolerant by design. Units documented in its docstring.
  - `metrics.py` — N/A-tolerant metric engine: annual_return, annualized_vol,
    max_drawdown, momentum_12_1, rsi14, sma200_flag, vol_regime.
  - `symbols.py` / `symbols_full.csv` — Tadawul symbol universe (~200 / ~350).
  - `data/` — cached annual matrix (2015-2026) + statements per symbol.
- `C:/Users/Hamad/stock_analyzer/` — stock_analyzer package (fundamentals,
  technicals, risk, scorer; 0-100 composite; works with .SR tickers).
- `C:/Users/Hamad/portfolio_excel/RESEARCH_FINDINGS.md` — research-backed design:
  Saudi weights (Value 30/Quality 20/Technical 20/Dividend 15/Risk 15), risk rules
  (SMA200 halves drawdown, vol-regime gating, 10-15 positions, 20% guideline,
  oil-beta by sector), horizon playbook (near/mid/long).

## REQUIRED FEATURES (from competitive research — stockanalysis.com / Finviz /
## SimplyWallSt / TradingView)
1. **Stock Profile** — GET /stock/{symbol}: price, name, sector, 16-50 metrics
   (reuse v2 metrics + stock_analyzer scorer), 1W/1M/3M/6M/YTD/1Y returns,
   SMA200 flag, RSI, vol regime, last 3 news headlines (yfinance .news).
2. **Screener** — GET /screener?filters: market cap, P/E, div yield, ROE, RSI,
   sector, trend flag, score>=X. Runs over the cached matrix (fast, no live
   fetch per request).
3. **Compare** — GET /compare?symbols=A,B,C: side-by-side metrics table +
   normalized performance vectors for charting.
4. **Watchlist + Price Alerts** — CRUD; alert = symbol + direction (above/below)
   + target; evaluation at refresh time; expose /alerts/due.
5. **Portfolio Analysis** — POST /portfolio {positions:[{symbol, shares, avg_cost}]}
   → totals, weights, P/L, concentration flags (40% hard, 20% guideline),
   vol-regime of the whole book, horizon verdicts (near/mid/long).
6. **Dividend Calendar + Calculator** — upcoming ex-dates for watchlist/portfolio;
   income projection with reinvestment (5y compounding).
7. **Movers** — GET /movers: top gainers/losers across the universe at last refresh.
8. **Macro Strip** — GET /macro: Brent, Gold, USD/SAR, BTC, MSCI-KSA (KSA ETF)
   — cached from yfinance.
9. **Local Cache + Refresh** — SQLite DB (single file, no server) mirroring
   v2's data; refresh script pulls yfinance → updates DB → recomputes metrics.
   Scheduled/manual via CLI: `python -m waraqah.refresh`.
10. **AI Agent Endpoint (stub now, full build later)** — POST /agent/chat {message,
    context?}: accept and validate the request shape, return 501 + spec comment.
    The real agent is a later phase (GLM-5.3-flash backend, tools = the API
    endpoints above). Design the DB so the agent can read it read-only.

## ARCHITECTURE (keep it simple)
- Python 3.11+ / FastAPI / uvicorn. SQLite via sqlite3 or SQLModel (no heavy ORM).
- Package layout:
  waraqah/
    api/            # FastAPI routers: stocks, screener, portfolio, alerts, macro, agent
    core/           # config, db, models
    engine/         # reuse of v2 fetcher+metrics (import or vendored copy)
    refresh/        # CLI refresh pipeline
    tests/          # pytest: every endpoint + numeric spot-checks
  requirements.txt, README.md, .env.example, .gitignore
- All numeric outputs: {value, unit, as_of} with explicit nulls when N/A.
- No API key required for data (yfinance). Add simple rate-limit middleware.

## NUMBER VERIFICATION (mandatory before "done")
- tests/test_numbers.py must assert, against v2's cached data and 2-3 live .SR
  tickers: market value = shares × price; P/L = MV − cost; weight sums ≈ 100%;
  CAGR hand-check on a fixed series (e.g. 100→121 in 2y = 10%); max drawdown
  hand-check (100→80→90 → 20%); RSI in [0,100]; dividend yield = annual div /
  price. Zero tolerance: every assertion must pass.

## DELIVERY
- Working API: `uvicorn waraqah.api.main:app` with /docs (OpenAPI).
- pytest green. README with run instructions + endpoint list.
- Git: init in repo dir, commit in logical units, push to Hxhamad/Waraqah main.
