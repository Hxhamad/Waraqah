# Waraqah API

Saudi stock analysis platform backend API.

## Features

1. **Stock Profile** - `GET /stock/{symbol}` - Price, metrics, returns, news
2. **Screener** - `GET /screener` - Filter by PE, ROE, dividend yield, sector, etc.
3. **Compare** - `GET /compare?symbols=A,B,C` - Side-by-side comparison
4. **Watchlist** - CRUD at `/watchlist`
5. **Price Alerts** - CRUD at `/alerts`, check `/alerts/due`
6. **Portfolio Analysis** - `POST /portfolio` - P/L, weights, concentration flags
7. **Dividend Calendar** - `GET /dividends/calendar` and `/dividends/project`
8. **Movers** - `GET /movers` - Top gainers/losers
9. **Macro Strip** - `GET /macro` - Brent, Gold, USD/SAR, BTC, MSCI-KSA
10. **AI Agent** - `POST /agent/chat` - Stub (501 Not Implemented)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure:

```
DATABASE_PATH=waraqah.db
SYMBOLS_PATH=symbols.csv
RATE_LIMIT_PER_MINUTE=60
```

## Running

```bash
# Start the API server
uvicorn waraqah.api.main:app --reload

# Access docs at http://localhost:8000/docs
```

## Data Refresh

```bash
# Refresh macro indicators
python -m waraqah.refresh --macro

# Refresh specific symbols
python -m waraqah.refresh --symbols 2222,4190,1120

# Refresh all symbols from symbols.csv
python -m waraqah.refresh --all
```

## Testing

```bash
python -m pytest -q
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| GET | `/stock/{symbol}` | Stock profile with metrics |
| GET | `/screener` | Screen stocks by filters |
| GET | `/compare?symbols=A,B,C` | Compare stocks |
| GET | `/watchlist` | Get watchlist |
| POST | `/watchlist/{symbol}` | Add to watchlist |
| DELETE | `/watchlist/{symbol}` | Remove from watchlist |
| GET | `/alerts` | Get all alerts |
| POST | `/alerts` | Create alert |
| DELETE | `/alerts/{id}` | Delete alert |
| GET | `/alerts/due` | Get triggered alerts |
| POST | `/portfolio` | Analyze portfolio |
| GET | `/dividends/calendar` | Dividend calendar |
| GET | `/dividends/project` | Project dividend income |
| GET | `/movers` | Top gainers/losers |
| GET | `/macro` | Macro indicators |
| POST | `/agent/chat` | AI agent (stub) |

## Scoring

Saudi-adapted composite score (0-100) based on research findings:
- Value (PE): 30%
- Quality (ROE): 20%
- Technical (SMA200 + Momentum): 20%
- Dividend: 15%
- Risk (Max Drawdown): 15%

## Architecture

```
waraqah/
├── api/           # FastAPI routers
├── core/          # Config, DB, models
├── engine/        # Data fetching and metrics
├── refresh/       # CLI refresh pipeline
└── tests/         # Pytest tests
```

## License

Private
