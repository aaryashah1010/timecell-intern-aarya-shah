"""Tests for the Task 1 severe vs moderate comparison mode."""

from __future__ import annotations

import pytest

from core.risk_calculator import Asset
from task1_risk import build_comparison_report, render_comparison


def test_build_comparison_report_uses_same_portfolio_for_both_scenarios():
    assets = [Asset("BTC", 100, -70)]

    severe, moderate = build_comparison_report(
        total_value=1_000_000,
        monthly_expenses=50_000,
        assets=assets,
    )

    assert severe.post_crash_value == pytest.approx(300_000)
    assert moderate.post_crash_value == pytest.approx(650_000)
    assert severe.assets[0].crash_pct == pytest.approx(-70.0)
    assert moderate.assets[0].crash_pct == pytest.approx(-35.0)


def test_render_comparison_reuses_standard_task1_report_format():
    severe, moderate = build_comparison_report(
        total_value=1_000_000,
        monthly_expenses=50_000,
        assets=[
            Asset("BTC", 50, -70),
            Asset("Cash", 50, 0),
        ],
    )

    output = render_comparison(severe, moderate)

    assert "RISK REPORT (severe scenario)" in output
    assert "RISK REPORT (moderate scenario)" in output
    assert output.count("ALLOCATION") == 2
    assert output.count("CRASH IMPACT (per asset)") == 2
    assert output.count("PORTFOLIO POST-CRASH") == 2
    assert "BTC" in output
    assert "crash -70.0%" in output
    assert "crash -35.0%" in output
