"""Pydantic models for API requests and responses."""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class MetricValue(BaseModel):
    value: Optional[float] = None
    unit: str = ""
    as_of: Optional[str] = None


class StockProfile(BaseModel):
    code: str
    name: Optional[str] = None
    sector: Optional[str] = None
    price: Optional[float] = None
    returns: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    sma200_flag: Optional[str] = None
    rsi14: Optional[float] = None
    vol_regime: Optional[str] = None
    news: List[dict] = Field(default_factory=list)
    score: Optional[float] = None
    rating: Optional[str] = None


class ScreenerFilters(BaseModel):
    sector: Optional[str] = None
    pe_min: Optional[float] = None
    pe_max: Optional[float] = None
    div_yield_min: Optional[float] = None
    roe_min: Optional[float] = None
    rsi_min: Optional[float] = None
    rsi_max: Optional[float] = None
    trend: Optional[str] = None
    score_min: Optional[float] = None
    limit: int = 50


class Position(BaseModel):
    symbol: str
    shares: float
    avg_cost: float


class PortfolioRequest(BaseModel):
    positions: List[Position]


class PortfolioPosition(BaseModel):
    symbol: str
    shares: float
    avg_cost: float
    price: Optional[float] = None
    market_value: Optional[float] = None
    cost_basis: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    weight: Optional[float] = None
    vol_regime: Optional[str] = None


class PortfolioAnalysis(BaseModel):
    positions: List[PortfolioPosition]
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    concentration_flags: List[str] = Field(default_factory=list)
    vol_regime: Optional[str] = None
    horizon_verdicts: dict = Field(default_factory=dict)


class WatchlistItem(BaseModel):
    id: int
    symbol: str
    added_at: str


class AlertCreate(BaseModel):
    symbol: str
    direction: Literal["above", "below"]
    target: float


class Alert(BaseModel):
    id: int
    symbol: str
    direction: str
    target: float
    triggered: bool
    created_at: str


class DividendEvent(BaseModel):
    symbol: str
    ex_date: Optional[str] = None
    amount: Optional[float] = None


class DividendProjection(BaseModel):
    symbol: str
    annual_dividend: float
    shares: float
    income_year1: float
    income_year5_cumulative: float
    income_year5_with_reinvestment: float


class Mover(BaseModel):
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    change_pct: Optional[float] = None


class MacroStrip(BaseModel):
    brent: Optional[float] = None
    gold: Optional[float] = None
    usd_sar: Optional[float] = None
    btc: Optional[float] = None
    msci_ksa: Optional[float] = None
    updated_at: Optional[str] = None


class AgentChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None
