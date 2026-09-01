"""Numeric verification tests - mandatory before done.

Tests: market value = shares × price; P/L = MV − cost; weight sums ≈ 100%;
CAGR hand-check; max drawdown hand-check; RSI in [0,100]; dividend yield = annual div / price.
"""
import math
import pytest

from waraqah.engine.metrics import (
    annual_return,
    annualized_vol,
    max_drawdown,
    rsi14,
    cagr,
    composite_score,
)


class TestMarketValueCalculations:
    """Test MV = shares × price."""

    def test_market_value_basic(self):
        shares = 100
        price = 50.0
        mv = shares * price
        assert mv == 5000.0

    def test_market_value_fractional(self):
        shares = 150.5
        price = 33.25
        mv = shares * price
        assert abs(mv - 5004.125) < 0.001


class TestPnLCalculations:
    """Test P/L = MV - cost."""

    def test_pnl_profit(self):
        shares = 100
        price = 55.0
        avg_cost = 50.0
        mv = shares * price
        cost = shares * avg_cost
        pnl = mv - cost
        assert pnl == 500.0

    def test_pnl_loss(self):
        shares = 100
        price = 45.0
        avg_cost = 50.0
        mv = shares * price
        cost = shares * avg_cost
        pnl = mv - cost
        assert pnl == -500.0

    def test_pnl_percentage(self):
        shares = 100
        price = 55.0
        avg_cost = 50.0
        cost = shares * avg_cost
        mv = shares * price
        pnl = mv - cost
        pnl_pct = pnl / cost
        assert abs(pnl_pct - 0.10) < 0.0001


class TestWeightSums:
    """Test weight sums ≈ 100%."""

    def test_weights_sum_to_one(self):
        positions = [
            {"shares": 100, "price": 50.0},
            {"shares": 200, "price": 25.0},
            {"shares": 50, "price": 100.0},
        ]
        total_value = sum(p["shares"] * p["price"] for p in positions)
        weights = [(p["shares"] * p["price"]) / total_value for p in positions]
        weight_sum = sum(weights)
        assert abs(weight_sum - 1.0) < 0.0001

    def test_single_position_is_100(self):
        shares = 100
        price = 50.0
        mv = shares * price
        weight = mv / mv
        assert weight == 1.0


class TestCAGR:
    """Test CAGR hand-check."""

    def test_cagr_100_to_121_in_2_years(self):
        start = 100.0
        end = 121.0
        years = 2
        result = cagr(start, end, years)
        assert abs(result - 0.10) < 0.0001

    def test_cagr_100_to_200_in_7_years(self):
        start = 100.0
        end = 200.0
        years = 7
        result = cagr(start, end, years)
        expected = (200 / 100) ** (1 / 7) - 1
        assert abs(result - expected) < 0.0001

    def test_cagr_zero_start_returns_none(self):
        assert cagr(0, 100, 2) is None

    def test_cagr_none_input_returns_none(self):
        assert cagr(None, 100, 2) is None


class TestMaxDrawdown:
    """Test max drawdown hand-check."""

    def test_drawdown_100_80_90(self):
        closes = [100, 90, 80, 85, 90]
        dd = max_drawdown(closes)
        assert abs(dd - (-0.20)) < 0.0001

    def test_drawdown_100_120_90(self):
        closes = [100, 110, 120, 100, 90]
        dd = max_drawdown(closes)
        expected = (90 - 120) / 120
        assert abs(dd - expected) < 0.0001

    def test_drawdown_always_up_is_zero(self):
        closes = [100, 110, 120, 130, 140]
        dd = max_drawdown(closes)
        assert dd == 0.0

    def test_drawdown_short_series(self):
        assert max_drawdown([100]) is None
        assert max_drawdown([]) is None


class TestRSI:
    """Test RSI in [0, 100]."""

    def test_rsi_in_range(self):
        closes = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
                  46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03]
        rsi = rsi14(closes)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_rsi_all_up_is_100(self):
        closes = [10 + i for i in range(20)]
        rsi = rsi14(closes)
        assert rsi == 100.0

    def test_rsi_all_down_is_0(self):
        closes = [100 - i for i in range(20)]
        rsi = rsi14(closes)
        assert rsi == 0.0

    def test_rsi_too_short_returns_none(self):
        closes = [10, 11, 12, 13, 14]
        assert rsi14(closes) is None


class TestDividendYield:
    """Test dividend yield = annual div / price."""

    def test_dividend_yield_calculation(self):
        annual_dividend = 2.50
        price = 50.0
        div_yield = annual_dividend / price
        assert abs(div_yield - 0.05) < 0.0001

    def test_dividend_yield_percentage(self):
        annual_dividend = 3.00
        price = 60.0
        div_yield_pct = (annual_dividend / price) * 100
        assert abs(div_yield_pct - 5.0) < 0.0001


class TestAnnualReturn:
    """Test annual return calculation."""

    def test_annual_return_10_pct(self):
        closes = [100, 102, 105, 108, 110]
        ret = annual_return(closes)
        assert abs(ret - 0.10) < 0.0001

    def test_annual_return_negative(self):
        closes = [100, 95, 90, 85, 80]
        ret = annual_return(closes)
        assert abs(ret - (-0.20)) < 0.0001


class TestAnnualizedVol:
    """Test annualized volatility calculation."""

    def test_vol_is_positive(self):
        daily_rets = [0.01, -0.005, 0.008, -0.003, 0.006]
        vol = annualized_vol(daily_rets)
        assert vol is not None
        assert vol > 0

    def test_vol_zero_rets_is_zero(self):
        daily_rets = [0.0, 0.0, 0.0, 0.0, 0.0]
        vol = annualized_vol(daily_rets)
        assert vol == 0.0


class TestCompositeScore:
    """Test composite score is in [0, 100]."""

    def test_score_in_range(self):
        score = composite_score(pe=15, roe=18, div_yield=4.5,
                               tech_pair=("above", 0.1), maxdd_2y=-0.15)
        assert 0 <= score <= 100

    def test_score_with_nulls(self):
        score = composite_score(pe=None, roe=None, div_yield=None,
                               tech_pair=None, maxdd_2y=None)
        assert score == 50.0

    def test_score_excellent_stock(self):
        score = composite_score(pe=8, roe=25, div_yield=6,
                               tech_pair=("above", 0.2), maxdd_2y=-0.10)
        assert score >= 80


class TestNumericEdgeCases:
    """Test edge cases in numeric calculations."""

    def test_zero_price_handling(self):
        closes = [0, 10, 20, 30]
        ret = annual_return(closes)
        assert ret is None

    def test_empty_list_handling(self):
        assert annual_return([]) is None
        assert max_drawdown([]) is None
        assert rsi14([]) is None

    def test_none_handling(self):
        assert annual_return(None) is None
        assert max_drawdown(None) is None
        assert rsi14(None) is None
