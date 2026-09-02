# AI Agent Data Strategy

## Decision: Hybrid (DB-first with live fallback)

### Strategy
The agent uses **Option (a) + (b) hybrid**: read-only access to the Waraqah SQLite database as the primary source, with live yfinance fallback for missing symbols.

### Rationale

1. **Consistency with existing API**: All routers (stocks, screener, portfolio, movers, dividends) already implement this pattern - DB snapshot first, then live fetch if needed. Reusing the same code paths ensures numbers from the agent match numbers from direct API calls.

2. **Verified data**: The SQLite data (snapshots, annual_metrics, statements) has been validated through 67 passing tests. Using it directly avoids introducing new data quality risks.

3. **Performance**: DB reads are fast and avoid rate limiting from external APIs. For most queries about Saudi stocks already in the system, responses are instant.

4. **Freshness when needed**: For symbols not in the DB or when live prices are requested, the existing `fetch_one()` and `fetch_macro()` functions provide yfinance data - the same fallback mechanism the REST API uses.

5. **No persistence of user data**: Portfolio analysis accepts positions from the request and processes them in-memory. User portfolio data is never stored unless explicitly flagged.

### Data Sources by Tool

| Tool | Primary Source | Fallback |
|------|---------------|----------|
| `get_stock_profile` | `snapshots` table | yfinance via `fetch_one()` |
| `screener_query` | `snapshots` table | None (DB only) |
| `compare_stocks` | `snapshots` table | yfinance via `fetch_one()` |
| `portfolio_analysis` | `snapshots` + request positions | yfinance via `fetch_one()` |
| `market_overview` | `macro_cache` + `snapshots` | yfinance via `fetch_macro()` |
| `dividend_info` | `snapshots` (info.div_yield) | yfinance via `fetch_one()` |

### Caveats

- Screener only searches stocks already cached in the DB
- Prices may be up to 24h stale depending on refresh cadence
- For real-time trading decisions, users should verify with live sources
