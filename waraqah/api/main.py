"""Waraqah API - Main FastAPI application."""
import time
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from waraqah.core.config import RATE_LIMIT_PER_MINUTE
from waraqah.core.db import init_db
from waraqah.api.stocks import router as stocks_router, compare_router
from waraqah.api.screener import router as screener_router
from waraqah.api.portfolio import router as portfolio_router
from waraqah.api.alerts import router as alerts_router
from waraqah.api.dividends import router as dividends_router
from waraqah.api.movers import router as movers_router
from waraqah.api.macro import router as macro_router
from waraqah.api.agent import router as agent_router

app = FastAPI(
    title="Waraqah API",
    description="Saudi stock analysis platform API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limit_store = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    now = time.time()

    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] if now - t < 60
    ]

    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    rate_limit_store[client_ip].append(now)
    return await call_next(request)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {
        "name": "Waraqah API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


app.include_router(stocks_router)
app.include_router(compare_router)
app.include_router(screener_router)
app.include_router(portfolio_router)
app.include_router(alerts_router)
app.include_router(dividends_router)
app.include_router(movers_router)
app.include_router(macro_router)
app.include_router(agent_router)
