"""AI Agent endpoint with streaming SSE support."""
import json
import os
import re
from typing import Optional, List, Any
from datetime import datetime

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from waraqah.core.models import (
    AgentChatRequest,
    ScreenerFilters,
    Position,
    PortfolioRequest,
    StockProfile,
)
from waraqah.core.db import get_db
from waraqah.engine.fetcher import fetch_one, fetch_global, fetch_macro
from waraqah.engine.metrics import composite_score, rating

load_dotenv()

router = APIRouter(prefix="/agent", tags=["agent"])


AGENT_LLM_API_KEY = os.getenv("AGENT_LLM_API_KEY")
AGENT_LLM_BASE_URL = os.getenv("AGENT_LLM_BASE_URL", "https://api.z.ai/api/paas/v4/")
AGENT_LLM_MODEL = os.getenv("AGENT_LLM_MODEL", "glm-5.3-flash")


SYSTEM_PROMPT_EN = """You are Waraqah AI Analyst, an expert on Saudi Arabian stocks.

RULES:
1. Every numeric claim MUST come from a tool result. Never make up numbers.
2. Always cite which tool provided the data in your answer.
3. You provide educational analysis only, NOT financial advice.
4. Never recommend buying or selling specific stocks.
5. Be concise and factual.

When answering, structure your response clearly and cite the tool source for each fact."""

SYSTEM_PROMPT_AR = """أنت وراقة المحلل الذكي، خبير في الأسهم السعودية.

القواعد:
1. كل رقم يجب أن يأتي من نتائج الأدوات. لا تخترع أرقاماً.
2. اذكر دائماً الأداة التي أعطتك البيانات.
3. تقدم تحليلاً تعليمياً فقط، وليس نصيحة مالية.
4. لا توصي أبداً بشراء أو بيع أسهم معينة.
5. كن موجزاً ودقيقاً.

عند الإجابة، نظم ردك بوضوح واذكر مصدر كل حقيقة."""


def detect_language(text: str) -> str:
    """Detect if text is Arabic or English based on character ratio."""
    arabic_chars = len(re.findall(r'[؀-ۿ]', text))
    return "ar" if arabic_chars > len(text) * 0.3 else "en"


def is_global_symbol(symbol: str) -> bool:
    """Determine if a symbol is global (non-Tadawul) vs Tadawul.

    Tadawul: 4-digit codes, optionally with .SR suffix (e.g. 2222, 2222.SR)
    Global: contains letters and is not 4-digit.SR (e.g. AAPL, RELIANCE.NS, 7203.T)
    """
    s = symbol.strip().upper()
    if re.match(r'^\d{4}$', s):
        return False
    if re.match(r'^\d{4}\.SR$', s):
        return False
    return True


def infer_currency(symbol: str, info_currency: Optional[str] = None) -> str:
    """Infer currency from symbol suffix or info.currency."""
    if info_currency:
        return info_currency
    s = symbol.strip().upper()
    if s.endswith(".SR"):
        return "SAR"
    if s.endswith(".NS") or s.endswith(".BO"):
        return "INR"
    if s.endswith(".T"):
        return "JPY"
    if s.endswith(".L"):
        return "GBp"
    if s.endswith(".DE") or s.endswith(".F"):
        return "EUR"
    if re.match(r'^\d{4}$', s):
        return "SAR"
    return "USD"


def get_snapshot(code: str) -> Optional[dict]:
    """Get snapshot from DB."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT data FROM snapshots WHERE code = ?", (code,)
        ).fetchone()
        if row:
            return json.loads(row["data"])
    return None


def build_profile_dict(data: dict, is_global: bool = False) -> dict:
    """Build a profile dict from snapshot data."""
    info = data.get("info") or {}
    pe = info.get("pe")
    roe = info.get("roe")
    div_yield = info.get("div_yield") or info.get("div5y")
    tech_pair = (data.get("sma200_flag"), data.get("momentum"))
    maxdd = data.get("maxdd_2y")
    score = composite_score(pe, roe, div_yield, tech_pair, maxdd)

    code = data.get("code", "")
    if is_global:
        currency = infer_currency(code, info.get("currency"))
    else:
        currency = "SAR"

    return {
        "code": code,
        "name": data.get("name_en"),
        "sector": data.get("sector"),
        "price": data.get("price"),
        "currency": currency,
        "returns": {
            "1W": data.get("ret_1w"),
            "1M": data.get("ret_1m"),
            "3M": data.get("ret_3m"),
            "6M": data.get("ret_6m"),
            "1Y": data.get("ret_1y"),
        },
        "metrics": {
            "pe": pe,
            "roe": roe,
            "div_yield": div_yield,
            "payout": info.get("payout"),
            "market_cap": info.get("market_cap"),
            "maxdd_2y": maxdd,
        },
        "sma200_flag": data.get("sma200_flag"),
        "rsi14": data.get("rsi14"),
        "vol_regime": data.get("vol_regime"),
        "score": score,
        "rating": rating(score),
    }


def tool_get_stock_profile(symbol: str) -> dict:
    """Get stock profile with metrics and returns (same logic as GET /stock/{symbol})."""
    symbol_clean = symbol.strip()

    if is_global_symbol(symbol_clean):
        data = fetch_global(symbol_clean)
        if not data:
            return {"error": f"Symbol {symbol} not found"}
        return build_profile_dict(data, is_global=True)

    code = symbol_clean.replace(".SR", "").strip()
    data = get_snapshot(code)
    if not data:
        data = fetch_one(code)
        if not data:
            return {"error": f"Symbol {symbol} not found"}
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO snapshots (code, data, updated_at) VALUES (?, ?, ?)",
                (code, json.dumps(data), datetime.utcnow().isoformat()),
            )
            conn.commit()
    return build_profile_dict(data, is_global=False)


def tool_screener_query(
    sector: Optional[str] = None,
    pe_min: Optional[float] = None,
    pe_max: Optional[float] = None,
    div_yield_min: Optional[float] = None,
    roe_min: Optional[float] = None,
    rsi_min: Optional[float] = None,
    rsi_max: Optional[float] = None,
    trend: Optional[str] = None,
    score_min: Optional[float] = None,
    limit: int = 20,
) -> dict:
    """Screen stocks by various filters (same logic as GET /screener)."""
    results = []

    with get_db() as conn:
        rows = conn.execute("SELECT code, data FROM snapshots").fetchall()

    for row in rows:
        try:
            data = json.loads(row["data"])
        except Exception:
            continue

        info = data.get("info") or {}
        pe = info.get("pe")
        roe = info.get("roe")
        div_yield = info.get("div_yield") or info.get("div5y")
        rsi = data.get("rsi14")
        sma_flag = data.get("sma200_flag")
        stock_sector = data.get("sector")

        tech_pair = (sma_flag, data.get("momentum"))
        maxdd = data.get("maxdd_2y")
        score = composite_score(pe, roe, div_yield, tech_pair, maxdd)

        if sector and stock_sector and sector.lower() not in stock_sector.lower():
            continue
        if pe_min is not None and (pe is None or pe < pe_min):
            continue
        if pe_max is not None and (pe is None or pe > pe_max):
            continue
        if div_yield_min is not None and (div_yield is None or div_yield < div_yield_min):
            continue
        if roe_min is not None and (roe is None or roe < roe_min):
            continue
        if rsi_min is not None and (rsi is None or rsi < rsi_min):
            continue
        if rsi_max is not None and (rsi is None or rsi > rsi_max):
            continue
        if trend and sma_flag != trend:
            continue
        if score_min is not None and score < score_min:
            continue

        results.append({
            "code": data.get("code"),
            "name": data.get("name_en"),
            "sector": stock_sector,
            "price": data.get("price"),
            "pe": pe,
            "roe": roe,
            "div_yield": div_yield,
            "score": score,
            "rating": rating(score),
        })

    results.sort(key=lambda x: x.get("score") or 0, reverse=True)
    return {"count": len(results), "results": results[:limit]}


def tool_compare_stocks(symbols: List[str]) -> dict:
    """Compare multiple stocks side-by-side (same logic as GET /compare)."""
    if len(symbols) < 2:
        return {"error": "Provide at least 2 symbols"}
    if len(symbols) > 10:
        return {"error": "Maximum 10 symbols"}

    profiles = []
    for symbol in symbols:
        symbol_clean = symbol.strip()
        if is_global_symbol(symbol_clean):
            data = fetch_global(symbol_clean)
            if data:
                profiles.append(build_profile_dict(data, is_global=True))
        else:
            code = symbol_clean.replace(".SR", "").strip()
            data = get_snapshot(code)
            if not data:
                data = fetch_one(code)
            if data:
                profiles.append(build_profile_dict(data, is_global=False))

    if len(profiles) < 2:
        return {"error": "Not enough valid symbols found"}

    return {
        "symbols": [p["code"] for p in profiles],
        "profiles": profiles,
        "comparison_matrix": {
            "price": {p["code"]: p["price"] for p in profiles},
            "pe": {p["code"]: p["metrics"].get("pe") for p in profiles},
            "roe": {p["code"]: p["metrics"].get("roe") for p in profiles},
            "div_yield": {p["code"]: p["metrics"].get("div_yield") for p in profiles},
            "score": {p["code"]: p["score"] for p in profiles},
        },
    }


def tool_portfolio_analysis(positions: List[dict]) -> dict:
    """Analyze a portfolio of positions (same logic as POST /portfolio)."""
    positions_out = []
    total_value = 0.0
    total_cost = 0.0
    vol_regimes = []
    concentration_flags = []
    currencies_seen = set()

    for pos in positions:
        symbol = pos.get("symbol", "").strip()
        shares = pos.get("shares", 0)
        avg_cost = pos.get("avg_cost", 0)

        if is_global_symbol(symbol):
            data = fetch_global(symbol)
            code = symbol
            is_global = True
        else:
            code = symbol.replace(".SR", "").strip()
            data = get_snapshot(code)
            if not data:
                data = fetch_one(code)
            is_global = False

        price = None
        vol_regime = None
        currency = "SAR"
        if data:
            price = data.get("price")
            vol_regime = data.get("vol_regime")
            info = data.get("info") or {}
            if is_global:
                currency = infer_currency(code, info.get("currency"))
            else:
                currency = "SAR"

        currencies_seen.add(currency)
        cost_basis = shares * avg_cost
        market_value = shares * price if price else None
        pnl = market_value - cost_basis if market_value else None
        pnl_pct = (pnl / cost_basis) if pnl and cost_basis else None

        positions_out.append({
            "symbol": code,
            "shares": shares,
            "avg_cost": avg_cost,
            "price": price,
            "currency": currency,
            "market_value": round(market_value, 2) if market_value else None,
            "cost_basis": round(cost_basis, 2),
            "pnl": round(pnl, 2) if pnl else None,
            "pnl_pct": round(pnl_pct, 4) if pnl_pct else None,
            "vol_regime": vol_regime,
        })

        if market_value:
            total_value += market_value
        total_cost += cost_basis
        if vol_regime:
            vol_regimes.append(vol_regime)

    for p in positions_out:
        if p["market_value"] and total_value > 0:
            weight = p["market_value"] / total_value
            p["weight"] = round(weight, 4)
            if weight >= 0.40:
                concentration_flags.append(f"{p['symbol']}: {weight*100:.1f}% >= 40% HARD CAP")
            elif weight >= 0.20:
                concentration_flags.append(f"{p['symbol']}: {weight*100:.1f}% >= 20% guideline")

    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost if total_cost else 0
    portfolio_vol = "HIGH" if vol_regimes.count("HIGH") > len(vol_regimes) / 2 else "NORMAL"

    result = {
        "positions": positions_out,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "concentration_flags": concentration_flags,
        "vol_regime": portfolio_vol,
    }

    if len(currencies_seen) == 1:
        result["currency"] = currencies_seen.pop()

    return result


def tool_market_overview() -> dict:
    """Get market overview: macro indicators + top movers."""
    with get_db() as conn:
        macro_rows = conn.execute("SELECT symbol, price, change_1d FROM macro_cache").fetchall()

    macro = {}
    if macro_rows:
        macro = {r["symbol"]: {"price": r["price"], "change_1d": r["change_1d"]} for r in macro_rows}
    else:
        macro_data = fetch_macro()
        now = datetime.utcnow().isoformat()
        with get_db() as conn:
            for key, val in macro_data.items():
                conn.execute(
                    "INSERT OR REPLACE INTO macro_cache (symbol, price, change_1d, updated_at) VALUES (?, ?, ?, ?)",
                    (key, val.get("price"), val.get("change_1d"), now),
                )
            conn.commit()
        macro = macro_data

    stocks = []
    with get_db() as conn:
        rows = conn.execute("SELECT code, data FROM snapshots").fetchall()
    for row in rows:
        try:
            data = json.loads(row["data"])
            change = data.get("ret_1w")
            if change is not None:
                stocks.append({
                    "symbol": data.get("code"),
                    "name": data.get("name_en"),
                    "price": data.get("price"),
                    "change_pct": round(change * 100, 2),
                })
        except Exception:
            continue

    sorted_stocks = sorted(stocks, key=lambda x: x["change_pct"], reverse=True)
    gainers = sorted_stocks[:5]
    losers = sorted_stocks[-5:][::-1] if len(sorted_stocks) >= 5 else []

    return {
        "macro": {
            "brent": macro.get("brent", {}).get("price"),
            "gold": macro.get("gold", {}).get("price"),
            "usd_sar": macro.get("usd_sar", {}).get("price"),
            "btc": macro.get("btc", {}).get("price"),
        },
        "gainers": gainers,
        "losers": losers,
    }


def tool_dividend_info(symbol: str) -> dict:
    """Get dividend information for a symbol."""
    symbol_clean = symbol.strip()

    if is_global_symbol(symbol_clean):
        data = fetch_global(symbol_clean)
        if not data:
            return {"error": f"Symbol {symbol} not found"}
        code = symbol_clean
        is_global = True
    else:
        code = symbol_clean.replace(".SR", "").strip()
        data = get_snapshot(code)
        if not data:
            data = fetch_one(code)
            if not data:
                return {"error": f"Symbol {symbol} not found"}
        is_global = False

    info = data.get("info") or {}
    price = data.get("price") or 0
    div_yield = info.get("div_yield") or info.get("div5y") or 0

    if is_global:
        currency = infer_currency(code, info.get("currency"))
    else:
        currency = "SAR"

    annual_div_per_share = price * (div_yield / 100) if price and div_yield else 0

    return {
        "symbol": code,
        "name": data.get("name_en"),
        "price": price,
        "currency": currency,
        "div_yield_pct": div_yield,
        "annual_dividend_per_share": round(annual_div_per_share, 4),
        "payout_ratio": info.get("payout"),
    }


TOOL_FUNCTIONS = {
    "get_stock_profile": tool_get_stock_profile,
    "screener_query": tool_screener_query,
    "compare_stocks": tool_compare_stocks,
    "portfolio_analysis": tool_portfolio_analysis,
    "market_overview": tool_market_overview,
    "dividend_info": tool_dividend_info,
}

TOOL_DESCRIPTIONS = {
    "get_stock_profile": "Get detailed stock profile including price, metrics (PE, ROE, dividend yield), returns, and rating for a Saudi stock symbol",
    "screener_query": "Screen and filter Saudi stocks by criteria like sector, PE ratio, dividend yield, ROE, RSI, trend, or minimum score",
    "compare_stocks": "Compare multiple Saudi stocks side-by-side on key metrics",
    "portfolio_analysis": "Analyze a portfolio of positions showing value, P&L, weights, and concentration warnings",
    "market_overview": "Get market overview including macro indicators (Brent, Gold, USD/SAR, BTC) and top gainers/losers",
    "dividend_info": "Get dividend information for a stock including yield and annual dividend per share",
}


class AgentChatResponse(BaseModel):
    """Response model for agent chat."""
    answer: str
    language: str
    tools_used: List[str] = Field(default_factory=list)
    confidence: str = "medium"


def format_sse_event(event_type: str, data: Any) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_agent_with_tools(
    message: str,
    symbol: Optional[str] = None,
    portfolio_positions: Optional[List[dict]] = None,
):
    """Run the agent with tools and yield SSE events."""
    language = detect_language(message)
    system_prompt = SYSTEM_PROMPT_AR if language == "ar" else SYSTEM_PROMPT_EN
    tools_used = []
    tool_results = {}

    yield format_sse_event("start", {"language": language, "timestamp": datetime.utcnow().isoformat()})

    message_lower = message.lower()
    if any(ar_word in message for ar_word in ["سوق", "السوق", "نظرة عامة", "المؤشرات"]):
        message_lower = "market overview"

    if portfolio_positions:
        tool_name = "portfolio_analysis"
        yield format_sse_event("tool_call", {"tool": tool_name, "args": {"positions_count": len(portfolio_positions)}})
        result = tool_portfolio_analysis(portfolio_positions)
        tool_results[tool_name] = result
        tools_used.append(tool_name)
        yield format_sse_event("tool_result", {"tool": tool_name, "data": result})

    elif symbol:
        tool_name = "get_stock_profile"
        yield format_sse_event("tool_call", {"tool": tool_name, "args": {"symbol": symbol}})
        result = tool_get_stock_profile(symbol)
        tool_results[tool_name] = result
        tools_used.append(tool_name)
        yield format_sse_event("tool_result", {"tool": tool_name, "data": result})

        if any(word in message_lower for word in ["dividend", "توزيعات", "أرباح"]):
            tool_name = "dividend_info"
            yield format_sse_event("tool_call", {"tool": tool_name, "args": {"symbol": symbol}})
            result = tool_dividend_info(symbol)
            tool_results[tool_name] = result
            tools_used.append(tool_name)
            yield format_sse_event("tool_result", {"tool": tool_name, "data": result})

    elif any(word in message_lower for word in ["compare", "مقارنة", "قارن"]):
        symbols = re.findall(r'\b\d{4}\b', message)
        if len(symbols) >= 2:
            tool_name = "compare_stocks"
            yield format_sse_event("tool_call", {"tool": tool_name, "args": {"symbols": symbols}})
            result = tool_compare_stocks(symbols)
            tool_results[tool_name] = result
            tools_used.append(tool_name)
            yield format_sse_event("tool_result", {"tool": tool_name, "data": result})

    elif any(word in message_lower for word in ["screen", "filter", "فلتر", "بحث"]):
        tool_name = "screener_query"
        filters = {}
        if "dividend" in message_lower or "توزيعات" in message:
            filters["div_yield_min"] = 3.0
        if "growth" in message_lower or "نمو" in message:
            filters["roe_min"] = 15.0
        yield format_sse_event("tool_call", {"tool": tool_name, "args": filters})
        result = tool_screener_query(**filters)
        tool_results[tool_name] = result
        tools_used.append(tool_name)
        yield format_sse_event("tool_result", {"tool": tool_name, "data": result})

    elif any(word in message_lower for word in ["market", "overview", "macro", "السوق", "نظرة"]):
        tool_name = "market_overview"
        yield format_sse_event("tool_call", {"tool": tool_name, "args": {}})
        result = tool_market_overview()
        tool_results[tool_name] = result
        tools_used.append(tool_name)
        yield format_sse_event("tool_result", {"tool": tool_name, "data": result})

    else:
        symbols = re.findall(r'\b\d{4}\b', message)
        if symbols:
            tool_name = "get_stock_profile"
            yield format_sse_event("tool_call", {"tool": tool_name, "args": {"symbol": symbols[0]}})
            result = tool_get_stock_profile(symbols[0])
            tool_results[tool_name] = result
            tools_used.append(tool_name)
            yield format_sse_event("tool_result", {"tool": tool_name, "data": result})
        else:
            tool_name = "market_overview"
            yield format_sse_event("tool_call", {"tool": tool_name, "args": {}})
            result = tool_market_overview()
            tool_results[tool_name] = result
            tools_used.append(tool_name)
            yield format_sse_event("tool_result", {"tool": tool_name, "data": result})

    if not AGENT_LLM_API_KEY:
        answer = _generate_fallback_answer(message, tool_results, language)
        yield format_sse_event("answer", {
            "text": answer,
            "tools_used": tools_used,
            "confidence": "high" if tools_used else "low",
            "language": language,
            "llm_used": False,
        })
        yield format_sse_event("done", {"success": True})
        return

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=AGENT_LLM_API_KEY,
            base_url=AGENT_LLM_BASE_URL,
        )

        tool_context = "\n\n".join([
            f"[{tool}]: {json.dumps(data, ensure_ascii=False, indent=2)}"
            for tool, data in tool_results.items()
        ])

        llm_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{message}\n\n--- Tool Results ---\n{tool_context}"},
        ]

        response = await client.chat.completions.create(
            model=AGENT_LLM_MODEL,
            messages=llm_messages,
            max_tokens=2000,
            temperature=0.7,
        )

        answer = response.choices[0].message.content or ""

        yield format_sse_event("answer", {
            "text": answer,
            "tools_used": tools_used,
            "confidence": "high" if tools_used else "medium",
            "language": language,
            "llm_used": True,
        })
        yield format_sse_event("done", {"success": True})

    except Exception as e:
        answer = _generate_fallback_answer(message, tool_results, language)
        yield format_sse_event("answer", {
            "text": answer,
            "tools_used": tools_used,
            "confidence": "medium",
            "language": language,
            "llm_used": False,
            "error": str(e),
        })
        yield format_sse_event("done", {"success": True, "llm_fallback": True})


def _generate_fallback_answer(message: str, tool_results: dict, language: str) -> str:
    """Generate a structured answer from tool results without LLM."""
    parts = []

    if "get_stock_profile" in tool_results:
        profile = tool_results["get_stock_profile"]
        if "error" not in profile:
            currency = profile.get("currency", "SAR")
            if language == "ar":
                parts.append(f"**{profile.get('name', profile.get('code'))}** ({profile.get('code')})")
                parts.append(f"- السعر: {profile.get('price')} {currency}")
                if profile.get('metrics', {}).get('pe'):
                    parts.append(f"- مكرر الربحية: {profile['metrics']['pe']:.2f}")
                if profile.get('metrics', {}).get('div_yield'):
                    parts.append(f"- العائد التوزيعي: {profile['metrics']['div_yield']:.2f}%")
                parts.append(f"- التقييم: {profile.get('rating', 'N/A')}")
                parts.append(f"\n*المصدر: get_stock_profile*")
            else:
                parts.append(f"**{profile.get('name', profile.get('code'))}** ({profile.get('code')})")
                parts.append(f"- Price: {profile.get('price')} {currency}")
                if profile.get('metrics', {}).get('pe'):
                    parts.append(f"- P/E Ratio: {profile['metrics']['pe']:.2f}")
                if profile.get('metrics', {}).get('div_yield'):
                    parts.append(f"- Dividend Yield: {profile['metrics']['div_yield']:.2f}%")
                parts.append(f"- Rating: {profile.get('rating', 'N/A')}")
                parts.append(f"\n*Source: get_stock_profile*")

    if "portfolio_analysis" in tool_results:
        analysis = tool_results["portfolio_analysis"]
        currency = analysis.get("currency", "SAR")
        if language == "ar":
            parts.append(f"**تحليل المحفظة**")
            parts.append(f"- القيمة الإجمالية: {analysis['total_value']:,.2f} {currency}")
            parts.append(f"- الربح/الخسارة: {analysis['total_pnl']:,.2f} {currency} ({analysis['total_pnl_pct']*100:.2f}%)")
            if analysis.get('concentration_flags'):
                parts.append(f"- تحذيرات التركز: {', '.join(analysis['concentration_flags'])}")
            parts.append(f"\n*المصدر: portfolio_analysis*")
        else:
            parts.append(f"**Portfolio Analysis**")
            parts.append(f"- Total Value: {analysis['total_value']:,.2f} {currency}")
            parts.append(f"- P&L: {analysis['total_pnl']:,.2f} {currency} ({analysis['total_pnl_pct']*100:.2f}%)")
            if analysis.get('concentration_flags'):
                parts.append(f"- Concentration Warnings: {', '.join(analysis['concentration_flags'])}")
            parts.append(f"\n*Source: portfolio_analysis*")

    if "market_overview" in tool_results:
        overview = tool_results["market_overview"]
        if language == "ar":
            parts.append(f"**نظرة على السوق**")
            macro = overview.get("macro", {})
            if macro.get("brent"):
                parts.append(f"- برنت: ${macro['brent']:.2f}")
            if macro.get("gold"):
                parts.append(f"- الذهب: ${macro['gold']:.2f}")
            if overview.get("gainers"):
                parts.append(f"- أعلى الرابحين: {', '.join([g['symbol'] for g in overview['gainers'][:3]])}")
            parts.append(f"\n*المصدر: market_overview*")
        else:
            parts.append(f"**Market Overview**")
            macro = overview.get("macro", {})
            if macro.get("brent"):
                parts.append(f"- Brent: ${macro['brent']:.2f}")
            if macro.get("gold"):
                parts.append(f"- Gold: ${macro['gold']:.2f}")
            if overview.get("gainers"):
                parts.append(f"- Top Gainers: {', '.join([g['symbol'] for g in overview['gainers'][:3]])}")
            parts.append(f"\n*Source: market_overview*")

    if "dividend_info" in tool_results:
        div = tool_results["dividend_info"]
        if "error" not in div:
            currency = div.get("currency", "SAR")
            if language == "ar":
                parts.append(f"**معلومات التوزيعات**")
                parts.append(f"- العائد: {div.get('div_yield_pct', 0):.2f}%")
                parts.append(f"- التوزيع السنوي للسهم: {div.get('annual_dividend_per_share', 0):.4f} {currency}")
                parts.append(f"\n*المصدر: dividend_info*")
            else:
                parts.append(f"**Dividend Info**")
                parts.append(f"- Yield: {div.get('div_yield_pct', 0):.2f}%")
                parts.append(f"- Annual Dividend/Share: {div.get('annual_dividend_per_share', 0):.4f} {currency}")
                parts.append(f"\n*Source: dividend_info*")

    if "compare_stocks" in tool_results:
        compare = tool_results["compare_stocks"]
        if "error" not in compare:
            if language == "ar":
                parts.append(f"**مقارنة الأسهم**: {', '.join(compare.get('symbols', []))}")
                for profile in compare.get("profiles", [])[:3]:
                    parts.append(f"- {profile['code']}: السعر {profile.get('price')}, التقييم {profile.get('rating')}")
                parts.append(f"\n*المصدر: compare_stocks*")
            else:
                parts.append(f"**Stock Comparison**: {', '.join(compare.get('symbols', []))}")
                for profile in compare.get("profiles", [])[:3]:
                    parts.append(f"- {profile['code']}: Price {profile.get('price')}, Rating {profile.get('rating')}")
                parts.append(f"\n*Source: compare_stocks*")

    if "screener_query" in tool_results:
        screener = tool_results["screener_query"]
        if language == "ar":
            parts.append(f"**نتائج البحث**: {screener.get('count', 0)} سهم")
            for stock in screener.get("results", [])[:5]:
                parts.append(f"- {stock['code']}: {stock.get('name', 'N/A')}, التقييم {stock.get('rating')}")
            parts.append(f"\n*المصدر: screener_query*")
        else:
            parts.append(f"**Screener Results**: {screener.get('count', 0)} stocks")
            for stock in screener.get("results", [])[:5]:
                parts.append(f"- {stock['code']}: {stock.get('name', 'N/A')}, Rating {stock.get('rating')}")
            parts.append(f"\n*Source: screener_query*")

    if not parts:
        if language == "ar":
            return "عذراً، لم أتمكن من العثور على بيانات. حاول ذكر رمز سهم محدد (مثل 2222)."
        return "Sorry, I couldn't find data. Try mentioning a specific stock symbol (e.g., 2222)."

    if language == "ar":
        parts.append("\n---\n*هذا تحليل تعليمي وليس نصيحة مالية.*")
    else:
        parts.append("\n---\n*This is educational analysis, not financial advice.*")

    return "\n".join(parts)


@router.post("/chat")
async def agent_chat(request: AgentChatRequest):
    """AI Agent chat endpoint with streaming SSE response.

    Streams events:
    - start: {language, timestamp}
    - tool_call: {tool, args}
    - tool_result: {tool, data}
    - answer: {text, tools_used, confidence, language}
    - done: {success}
    """
    portfolio_positions = None
    if request.context and "positions" in request.context:
        portfolio_positions = request.context["positions"]

    symbol = request.symbol
    if not symbol and request.context and "symbol" in request.context:
        symbol = request.context["symbol"]

    return StreamingResponse(
        run_agent_with_tools(request.message, symbol, portfolio_positions),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
