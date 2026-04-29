"""Correctness tests for the Task 1 risk-calculation layer.

Tests cover: spec example portfolio, edge cases (zero allocation, 100% cash,
runway boundary, concentration boundary), moderate scenario, and risk-score ranking.
"""

from math import isclose, isfinite

import pytest

from core.risk_calculator import (
    Asset,
    CONCENTRATION_THRESHOLD_PCT,
    RUIN_TEST_THRESHOLD_MONTHS,
    asset_value,
    asset_value_after_crash,
    build_report,
    compute_risk_metrics,
    risk_score,
)

# ---------- spec example portfolio (Task 01 PDF, page 2) ----------

SPEC_PORTFOLIO = {
    "total_value_inr": 10_000_000,
    "monthly_expenses_inr": 80_000,
    "assets": [
        {"name": "BTC",     "allocation_pct": 30, "expected_crash_pct": -80},
        {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
        {"name": "GOLD",    "allocation_pct": 20, "expected_crash_pct": -15},
        {"name": "CASH",    "allocation_pct": 10, "expected_crash_pct":   0},
    ],
}


def test_compute_risk_metrics_returns_required_keys():
    result = compute_risk_metrics(SPEC_PORTFOLIO)
    assert set(result.keys()) == {
        "post_crash_value",
        "runway_months",
        "ruin_test",
        "largest_risk_asset",
        "concentration_warning",
    }


def test_compute_risk_metrics_spec_portfolio_math():
    # BTC:     30% of 10M = 3M  -> 3M * (1 - 0.80) = 600_000
    # NIFTY50: 40% of 10M = 4M  -> 4M * (1 - 0.40) = 2_400_000
    # GOLD:    20% of 10M = 2M  -> 2M * (1 - 0.15) = 1_700_000
    # CASH:    10% of 10M = 1M  -> 1M * (1 - 0.00) = 1_000_000
    # post_crash_value = 5_700_000
    # runway = 5_700_000 / 80_000 = 71.25 months -> PASS
    result = compute_risk_metrics(SPEC_PORTFOLIO)
    assert result["post_crash_value"] == pytest.approx(5_700_000)
    assert result["runway_months"] == pytest.approx(71.25)
    assert result["ruin_test"] == "PASS"
    assert result["largest_risk_asset"] == "BTC"   # 30 * 80 = 2400 > 40 * 40 = 1600
    # NIFTY50 is exactly 40% - threshold is strict > 40, so no warning
    assert result["concentration_warning"] is False


def test_compute_risk_metrics_ruin_test_is_string():
    result = compute_risk_metrics(SPEC_PORTFOLIO)
    assert result["ruin_test"] in ("PASS", "FAIL")
    assert isinstance(result["ruin_test"], str)


def test_compute_risk_metrics_moderate_scenario():
    result = compute_risk_metrics(SPEC_PORTFOLIO, moderate=True)
    # BTC crash halved: -40%  -> 3M * 0.60 = 1_800_000
    # NIFTY50: -20%           -> 4M * 0.80 = 3_200_000
    # GOLD:    -7.5%          -> 2M * 0.925 = 1_850_000
    # CASH:      0%           -> 1M
    # post_crash = 7_850_000
    assert result["post_crash_value"] == pytest.approx(7_850_000)


def test_compute_risk_metrics_rejects_invalid_portfolio_shape():
    with pytest.raises(ValueError, match="portfolio must be a dictionary"):
        compute_risk_metrics(None)

    bad = dict(SPEC_PORTFOLIO)
    bad["assets"] = []
    with pytest.raises(ValueError, match="non-empty list"):
        compute_risk_metrics(bad)


def test_compute_risk_metrics_rejects_invalid_numbers():
    bad = dict(SPEC_PORTFOLIO)
    bad["monthly_expenses_inr"] = -1
    with pytest.raises(ValueError, match="monthly_expenses_inr"):
        compute_risk_metrics(bad)

    bad = dict(SPEC_PORTFOLIO)
    bad["assets"] = [
        {"name": "BTC", "allocation_pct": 10, "expected_crash_pct": -120}
    ]
    with pytest.raises(ValueError, match="below -100"):
        compute_risk_metrics(bad)


# ---------- primitives ----------

def test_asset_value_basic():
    assert asset_value(1_000_000, 40) == 400_000


def test_asset_value_zero_allocation_is_zero():
    assert asset_value(1_000_000, 0) == 0


def test_post_crash_severe_drop():
    assert asset_value_after_crash(100, -70) == pytest.approx(30)


def test_post_crash_no_drop():
    assert asset_value_after_crash(100, 0) == 100


def test_post_crash_total_loss():
    assert asset_value_after_crash(100, -100) == 0


def test_risk_score_uses_absolute_value():
    assert risk_score(40, -70) == risk_score(40, 70) == 2800


# ---------- 100% cash edge case ----------

def test_pure_cash_portfolio_loses_nothing():
    r = build_report(
        total_value=1_000_000,
        monthly_expenses=50_000,
        assets=[Asset("Cash", 100, 0)],
    )
    assert r.post_crash_value == 1_000_000
    assert r.loss_pct == 0
    assert r.runway_months == 20
    assert r.survives_one_year is True
    assert r.largest_risk_asset is None  # no asset has crash exposure
    assert r.concentration_warning is True  # 100% > 40% threshold
    assert r.concentrated_assets == ("Cash",)


# ---------- zero-allocation edge case ----------

def test_zero_allocation_asset_does_not_affect_totals():
    r = build_report(
        total_value=1_000_000,
        monthly_expenses=10_000,
        assets=[Asset("BTC", 0, -70), Asset("Cash", 100, 0)],
    )
    assert r.post_crash_value == 1_000_000
    # BTC carried zero allocation, so it should not be the largest-risk asset
    assert r.largest_risk_asset != "BTC"


# ---------- realistic aggressive portfolio ----------

def test_aggressive_portfolio_fails_ruin_test():
    r = build_report(
        total_value=1_000_000,
        monthly_expenses=80_000,
        assets=[Asset("BTC", 80, -70), Asset("Cash", 20, 0)],
    )
    # 80% * 30% (post-crash) + 20% * 100% = 24% + 20% = 44% of 10L = 4.4L
    assert isclose(r.post_crash_value, 440_000)
    assert isclose(r.loss_pct, 56.0)
    assert r.survives_one_year is False
    assert r.largest_risk_asset == "BTC"
    assert "BTC" in r.concentrated_assets


# ---------- moderate scenario ----------

def test_moderate_halves_the_crash_impact():
    severe = build_report(
        total_value=1_000_000,
        monthly_expenses=50_000,
        assets=[Asset("BTC", 100, -70)],
    )
    moderate = build_report(
        total_value=1_000_000,
        monthly_expenses=50_000,
        assets=[Asset("BTC", 100, -70)],
        moderate=True,
    )
    assert severe.post_crash_value == pytest.approx(300_000)    # 100% * (1 - 0.70)
    assert moderate.post_crash_value == pytest.approx(650_000)  # 100% * (1 - 0.35)
    assert moderate.assets[0].crash_pct == pytest.approx(-35.0)


# ---------- runway / monthly expenses edge cases ----------

def test_runway_is_infinite_when_no_expenses():
    r = build_report(1_000_000, 0, [Asset("Cash", 100, 0)])
    assert not isfinite(r.runway_months)
    assert r.survives_one_year is True


def test_ruin_test_is_strict_greater_than_12():
    # runway = 12 exactly should fail (threshold is strictly > 12)
    r = build_report(
        total_value=120_000,
        monthly_expenses=10_000,
        assets=[Asset("Cash", 100, 0)],
    )
    assert r.runway_months == RUIN_TEST_THRESHOLD_MONTHS
    assert r.survives_one_year is False


# ---------- concentration boundary ----------

def test_concentration_warning_is_strict_greater_than_40():
    # exactly 40% should NOT trip the warning
    r = build_report(
        total_value=1_000_000,
        monthly_expenses=50_000,
        assets=[
            Asset("BTC", 40, -70),
            Asset("NIFTY", 40, -40),
            Asset("Cash", 20, 0),
        ],
    )
    assert r.concentration_warning is False
    assert CONCENTRATION_THRESHOLD_PCT == 40.0


def test_concentration_warning_lists_every_offender():
    r = build_report(
        total_value=1_000_000,
        monthly_expenses=50_000,
        assets=[
            Asset("BTC", 50, -70),
            Asset("NIFTY", 45, -40),
            Asset("Cash", 5, 0),
        ],
    )
    assert r.concentration_warning is True
    assert set(r.concentrated_assets) == {"BTC", "NIFTY"}


# ---------- largest-risk ranking ----------

def test_largest_risk_uses_alloc_times_abs_crash():
    r = build_report(
        total_value=1_000_000,
        monthly_expenses=50_000,
        assets=[
            Asset("BTC", 30, -70),     # score 2100
            Asset("NIFTY", 50, -40),   # score 2000
            Asset("Cash", 20, 0),      # score 0
        ],
    )
    assert r.largest_risk_asset == "BTC"


# ---------- absolute-loss arithmetic ----------

def test_absolute_loss_equals_pre_minus_post():
    r = build_report(
        total_value=1_000_000,
        monthly_expenses=50_000,
        assets=[Asset("BTC", 50, -70), Asset("Cash", 50, 0)],
    )
    assert isclose(r.absolute_loss, r.pre_crash_value - r.post_crash_value)
    assert isclose(r.loss_pct, r.absolute_loss / r.pre_crash_value * 100.0)
