"""Find the minimum uniform crash that fails the 12-month runway test."""

from __future__ import annotations

import copy

from core.risk_calculator import compute_risk_metrics

RUNWAY_THRESHOLD_MONTHS: float = 12.0
CASH_ASSET_NAMES: frozenset[str] = frozenset({"cash", "fd", "savings", "fixed deposit"})
BINARY_SEARCH_ITERATIONS: int = 20


def find_portfolio_breakpoint(portfolio: dict) -> dict:
    """Binary search the non-cash crash percentage that first fails runway."""
    zero_result = _compute_at_uniform_crash(portfolio, 0.0)
    if zero_result["runway_months"] <= RUNWAY_THRESHOLD_MONTHS:
        return {
            "break_pct": 0.0,
            "break_value_inr": zero_result["post_crash_value"],
            "break_runway": zero_result["runway_months"],
            "interpretation": (
                "Portfolio already fails the 12-month runway test "
                "even without any crash."
            ),
            "implications": [
                "current capital is too low for the monthly burn rate",
                "defensive allocation cannot fix the runway test by itself",
            ],
            "already_failing": True,
            "never_failing": False,
        }

    full_crash_result = _compute_at_uniform_crash(portfolio, 100.0)
    if full_crash_result["runway_months"] > RUNWAY_THRESHOLD_MONTHS:
        return {
            "break_pct": 100.0,
            "break_value_inr": full_crash_result["post_crash_value"],
            "break_runway": round(full_crash_result["runway_months"], 1),
            "interpretation": (
                "Portfolio still passes the 12-month runway test even if "
                "all non-cash assets fall 100%."
            ),
            "implications": [
                "strong defensive buffer relative to monthly expenses",
                "non-cash volatility is not the main survival constraint",
            ],
            "already_failing": False,
            "never_failing": True,
        }

    lo, hi = 0.0, 100.0
    break_pct = 100.0

    for _ in range(BINARY_SEARCH_ITERATIONS):
        mid = (lo + hi) / 2.0
        result = _compute_at_uniform_crash(portfolio, mid)
        if result["runway_months"] <= RUNWAY_THRESHOLD_MONTHS:
            break_pct = mid
            hi = mid
        else:
            lo = mid

    final = _compute_at_uniform_crash(portfolio, break_pct)

    return {
        "break_pct": round(break_pct, 1),
        "break_value_inr": final["post_crash_value"],
        "break_runway": round(final["runway_months"], 1),
        "interpretation": (
            f"Portfolio fails when non-cash assets fall more than {break_pct:.0f}%."
        ),
        "implications": [
            "high exposure to volatile assets",
            "insufficient defensive buffer at deeper drawdowns",
        ],
        "already_failing": False,
        "never_failing": False,
    }


def _compute_at_uniform_crash(portfolio: dict, crash_pct: float) -> dict:
    """Apply a uniform negative crash percentage to all non-cash assets."""
    modified = copy.deepcopy(portfolio)
    for asset in modified["assets"]:
        if asset["name"].lower().strip() not in CASH_ASSET_NAMES:
            asset["expected_crash_pct"] = -abs(crash_pct)
    return compute_risk_metrics(modified)
