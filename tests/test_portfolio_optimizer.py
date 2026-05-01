"""Tests for the Task 4 portfolio strategy optimizer."""

from __future__ import annotations

import pytest

from core.portfolio_optimizer import (
    build_ai_verdict_prompt,
    build_allocation_changes,
    compare_portfolios,
    detect_strategy,
    generate_impact_summary,
    normalize_asset_name,
    suggest_portfolio,
)
from core.risk_calculator import compute_risk_metrics


def _portfolio(
    assets: list[dict],
    *,
    total: float = 1_000_000,
    monthly: float = 50_000,
) -> dict:
    return {
        "total_value_inr": total,
        "monthly_expenses_inr": monthly,
        "assets": assets,
    }


def _allocations(portfolio: dict) -> dict[str, float]:
    return {asset["name"]: float(asset["allocation_pct"]) for asset in portfolio["assets"]}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("eth", "ETH"),
        ("ETHEREUM", "ETH"),
        ("bitcoin", "BTC"),
        ("nifty50", "Equity"),
        ("sensex", "Equity"),
        ("bonds", "Bonds"),
        ("cash", "Cash"),
        ("fd", "Cash"),
        ("gold", "Gold"),
        ("mutual funds", "Mutual Funds"),
        ("reit", "Real Estate"),
    ],
)
def test_normalize_asset_name_handles_casing_and_aliases(raw: str, expected: str):
    assert normalize_asset_name(raw) == expected


def test_bonds_and_cash_duplicate_casing_are_merged():
    portfolio = _portfolio([
        {"name": "ETH", "allocation_pct": 50, "expected_crash_pct": -75},
        {"name": "bonds", "allocation_pct": 20, "expected_crash_pct": -10},
        {"name": "Cash", "allocation_pct": 20, "expected_crash_pct": 0},
        {"name": "cash", "allocation_pct": 10, "expected_crash_pct": 0},
    ])

    suggested = suggest_portfolio(portfolio, "Balanced")
    names = [asset["name"] for asset in suggested["assets"]]

    assert names.count("Bonds") == 1
    assert names.count("Cash") == 1
    assert "bonds" not in names
    assert "cash" not in names


def test_detect_strategy_aggressive_for_high_loss_or_concentration():
    portfolio = _portfolio([
        {"name": "BTC", "allocation_pct": 80, "expected_crash_pct": -70},
        {"name": "Cash", "allocation_pct": 20, "expected_crash_pct": 0},
    ])
    metrics = compute_risk_metrics(portfolio)

    assert detect_strategy(portfolio, metrics) == "Aggressive"


def test_detect_strategy_conservative_for_low_loss_high_runway_no_concentration():
    portfolio = _portfolio(
        [
            {"name": "Cash", "allocation_pct": 25, "expected_crash_pct": 0},
            {"name": "Bonds", "allocation_pct": 35, "expected_crash_pct": -10},
            {"name": "Gold", "allocation_pct": 20, "expected_crash_pct": -15},
            {"name": "Equity", "allocation_pct": 20, "expected_crash_pct": -40},
        ],
        monthly=20_000,
    )
    metrics = compute_risk_metrics(portfolio)

    assert detect_strategy(portfolio, metrics) == "Conservative"


def test_detect_strategy_balanced_for_middle_risk():
    portfolio = _portfolio(
        [
            {"name": "Equity", "allocation_pct": 40, "expected_crash_pct": -40},
            {"name": "Gold", "allocation_pct": 20, "expected_crash_pct": -15},
            {"name": "Bonds", "allocation_pct": 20, "expected_crash_pct": -10},
            {"name": "Cash", "allocation_pct": 20, "expected_crash_pct": 0},
        ],
        monthly=35_000,
    )
    metrics = compute_risk_metrics(portfolio)

    assert detect_strategy(portfolio, metrics) == "Balanced"


@pytest.mark.parametrize(
    ("strategy", "cap"),
    [
        ("Conservative", 25.0),
        ("Balanced", 35.0),
        ("Aggressive", 50.0),
    ],
)
def test_high_risk_assets_are_capped_by_mode(strategy: str, cap: float):
    portfolio = _portfolio([
        {"name": "ETH", "allocation_pct": 80, "expected_crash_pct": -75},
        {"name": "Cash", "allocation_pct": 20, "expected_crash_pct": 0},
    ])

    suggested = suggest_portfolio(portfolio, strategy)

    assert _allocations(suggested)["ETH"] == pytest.approx(cap)


def test_missing_defensive_assets_are_added_when_needed():
    portfolio = _portfolio([
        {"name": "ETH", "allocation_pct": 100, "expected_crash_pct": -75},
    ])

    suggested = suggest_portfolio(portfolio, "Balanced")
    names = {asset["name"] for asset in suggested["assets"]}

    assert {"Bonds", "Cash", "Gold"}.issubset(names)


def test_redistribution_totals_exactly_100_and_has_no_negative_allocations():
    portfolio = _portfolio([
        {"name": "ETH", "allocation_pct": 100, "expected_crash_pct": -75},
    ])

    suggested = suggest_portfolio(portfolio, "Conservative")

    assert sum(asset["allocation_pct"] for asset in suggested["assets"]) == pytest.approx(100)
    assert all(asset["allocation_pct"] >= 0 for asset in suggested["assets"])


def test_conservative_strategy_enforces_minimum_defensive_allocation():
    portfolio = _portfolio([
        {"name": "BTC", "allocation_pct": 25, "expected_crash_pct": -70},
        {"name": "ETH", "allocation_pct": 25, "expected_crash_pct": -75},
        {"name": "Equity", "allocation_pct": 25, "expected_crash_pct": -40},
        {"name": "Cash", "allocation_pct": 25, "expected_crash_pct": 0},
    ])

    suggested = suggest_portfolio(portfolio, "Conservative")
    allocations = _allocations(suggested)
    defensive_total = (
        allocations.get("Cash", 0)
        + allocations.get("Bonds", 0)
        + allocations.get("Gold", 0)
    )

    assert defensive_total >= 60.0


def test_suggested_portfolio_reduces_concentration_and_improves_loss_or_runway():
    portfolio = _portfolio([
        {"name": "ETH", "allocation_pct": 70, "expected_crash_pct": -75},
        {"name": "Cash", "allocation_pct": 30, "expected_crash_pct": 0},
    ])

    suggested = suggest_portfolio(portfolio, "Balanced")
    comparison = compare_portfolios(portfolio, suggested)
    current = comparison["current_metrics"]
    improved = comparison["suggested_metrics"]

    assert current["concentration_warning"] is True
    assert improved["concentration_warning"] is False
    assert (
        improved["loss_pct"] < current["loss_pct"]
        or improved["runway_months"] > current["runway_months"]
    )


def test_already_safe_portfolio_does_not_get_unnecessary_changes():
    portfolio = _portfolio([
        {"name": "Cash", "allocation_pct": 25, "expected_crash_pct": 0},
        {"name": "Bonds", "allocation_pct": 35, "expected_crash_pct": -10},
        {"name": "Gold", "allocation_pct": 20, "expected_crash_pct": -15},
        {"name": "Equity", "allocation_pct": 20, "expected_crash_pct": -40},
    ])

    suggested = suggest_portfolio(portfolio, "Conservative")

    assert suggested["assets"] == portfolio["assets"]


def test_allocation_changes_print_canonical_names_only():
    current = _portfolio([
        {"name": "ETH", "allocation_pct": 50, "expected_crash_pct": -75},
        {"name": "bonds", "allocation_pct": 20, "expected_crash_pct": -10},
        {"name": "cash", "allocation_pct": 30, "expected_crash_pct": 0},
    ])
    suggested = suggest_portfolio(current, "Balanced")

    changes = build_allocation_changes(current, suggested)
    names = [change["name"] for change in changes]

    assert names == ["ETH", "Bonds", "Cash", "Gold"]
    assert "bonds" not in names
    assert "cash" not in names


def test_generate_impact_summary_labels_still_unsafe_improvement():
    current = _portfolio([
        {"name": "ETH", "allocation_pct": 70, "expected_crash_pct": -75},
        {"name": "Cash", "allocation_pct": 30, "expected_crash_pct": 0},
    ], monthly=500_000)
    suggested = suggest_portfolio(current, "Balanced")
    comparison = compare_portfolios(current, suggested)

    impact = generate_impact_summary(
        comparison["current_metrics"], comparison["suggested_metrics"]
    )

    assert impact["loss_pct"]["label"] == "better"
    assert impact["ruin_test"]["label"] == "still unsafe"
    assert impact["result"] == "Improved but still unsafe"


def test_ai_verdict_prompt_includes_metrics_changes_and_impact():
    current = _portfolio([
        {"name": "ETH", "allocation_pct": 70, "expected_crash_pct": -75},
        {"name": "Cash", "allocation_pct": 30, "expected_crash_pct": 0},
    ])
    suggested = suggest_portfolio(current, "Balanced")
    comparison = compare_portfolios(current, suggested)
    impact = generate_impact_summary(
        comparison["current_metrics"], comparison["suggested_metrics"]
    )

    prompt = build_ai_verdict_prompt(
        current_strategy="Aggressive",
        target_strategy="Balanced",
        comparison=comparison,
        impact=impact,
    )

    assert "Current strategy: Aggressive" in prompt
    assert "Target strategy:  Balanced" in prompt
    assert "Current metrics:" in prompt
    assert "Suggested metrics:" in prompt
    assert "Allocation changes:" in prompt
    assert "Impact summary result:" in prompt
