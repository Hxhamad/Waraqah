"""Engine module tests."""
import pytest

from waraqah.engine.metrics import (
    annual_return,
    annualized_vol,
    max_drawdown,
    momentum_12_1,
    rsi14,
    sma200_flag,
    vol_regime,
    composite_score,
    rating,
    cagr,
)


class TestMetrics:
    def test_annual_return_basic(self):
        closes = [100, 105, 110]
        ret = annual_return(closes)
        assert abs(ret - 0.10) < 0.0001

    def test_annual_return_empty(self):
        assert annual_return([]) is None
        assert annual_return(None) is None

    def test_max_drawdown_basic(self):
        closes = [100, 110, 90, 95]
        dd = max_drawdown(closes)
        expected = (90 - 110) / 110
        assert abs(dd - expected) < 0.0001

    def test_rsi_basic(self):
        closes = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
        rsi = rsi14(closes)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_sma200_flag(self):
        closes = [i for i in range(1, 250)]
        flag = sma200_flag(closes)
        assert flag in ("above", "below", None)

    def test_vol_regime(self):
        closes = [100 + i * 0.1 for i in range(100)]
        regime = vol_regime(closes)
        assert regime in ("HIGH", "NORMAL", None)

    def test_momentum_12_1(self):
        closes = [100 + i for i in range(250)]
        mom = momentum_12_1(closes)
        assert mom is not None


class TestCompositeScore:
    def test_composite_all_good(self):
        score = composite_score(
            pe=10,
            roe=20,
            div_yield=5,
            tech_pair=("above", 0.1),
            maxdd_2y=-0.10
        )
        assert score >= 75

    def test_composite_all_bad(self):
        score = composite_score(
            pe=50,
            roe=-5,
            div_yield=0,
            tech_pair=("below", -0.2),
            maxdd_2y=-0.60
        )
        assert score <= 30

    def test_composite_all_none(self):
        score = composite_score(None, None, None, None, None)
        assert score == 50.0


class TestRating:
    def test_rating_strong_buy(self):
        assert rating(85) == "شراء قوي"

    def test_rating_buy(self):
        assert rating(70) == "شراء"

    def test_rating_hold(self):
        assert rating(55) == "تعزيز/احتفاظ"

    def test_rating_sell(self):
        assert rating(40) == "بيع"

    def test_rating_strong_sell(self):
        assert rating(20) == "بيع قوي"

    def test_rating_none(self):
        assert rating(None) is None


class TestCAGR:
    def test_cagr_basic(self):
        result = cagr(100, 121, 2)
        assert abs(result - 0.10) < 0.0001

    def test_cagr_zero_start(self):
        assert cagr(0, 100, 2) is None

    def test_cagr_negative_years(self):
        assert cagr(100, 200, -1) is None
