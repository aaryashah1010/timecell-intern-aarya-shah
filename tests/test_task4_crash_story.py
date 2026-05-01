"""Focused tests for Task 4 crash scenario story generator."""

from __future__ import annotations

import json

import pytest

from core.breakpoint_detector import find_portfolio_breakpoint
from core.crash_engine import (
    apply_scenario_shocks,
    compute_scenario_result,
    compute_why_this_breaks,
)
from core.decision_insight import build_decision_insight, compute_baseline_runway
from core.report_formatter import ScenarioRenderContext, print_scenario
from core.scenario_generator import (
    build_user_prompt,
    parse_scenarios,
    validate_scenarios,
)
from task4_crash_story import main as task4_main


BASE_PORTFOLIO = {
    "total_value_inr": 1_000_000,
    "monthly_expenses_inr": 50_000,
    "assets": [
        {"name": "BTC", "allocation_pct": 50, "expected_crash_pct": -70},
        {"name": "NIFTY50", "allocation_pct": 30, "expected_crash_pct": -40},
        {"name": "Cash", "allocation_pct": 20, "expected_crash_pct": 0},
    ],
}


def _scenario(scenario_id: int = 1, shock_map: dict | None = None) -> dict:
    return {
        "scenario_id": scenario_id,
        "name": f"Scenario {scenario_id}",
        "narrative": "A realistic stress event hits multiple risk assets.",
        "shock_map": shock_map or {"BTC": -50, "NIFTY50": -20, "Cash": 0},
        "severity": "HIGH",
        "severity_reason": "Risk assets sell off together.",
        "likelihood": "MEDIUM",
        "likelihood_reason": "The scenario is plausible with a clear catalyst.",
        "takeaway": "Reduce concentrated risk if this scenario is unacceptable.",
    }


def test_parse_scenarios_accepts_markdown_fenced_json_array():
    raw = "```json\n" + json.dumps([_scenario()]) + "\n```"

    parsed = parse_scenarios(raw)

    assert parsed[0]["name"] == "Scenario 1"
    assert parsed[0]["shock_map"]["BTC"] == -50


def test_validate_scenarios_skips_invalid_items_and_truncates_to_five(caplog):
    scenarios = [
        _scenario(1),
        {"name": "", "shock_map": {"BTC": -50}},
        {"name": "Bad shock", "shock_map": {"BTC": "down"}},
        _scenario(2),
        _scenario(3),
        _scenario(4),
        _scenario(5),
        _scenario(6),
    ]

    valid = validate_scenarios(scenarios)

    assert len(valid) == 5
    assert [s["scenario_id"] for s in valid] == [1, 2, 3, 4, 5]
    assert "Invalid scenario skipped" in caplog.text


def test_build_user_prompt_requires_every_portfolio_asset_in_shock_map():
    prompt = build_user_prompt(BASE_PORTFOLIO)

    assert "Assets to cover in every shock_map" in prompt
    assert "BTC" in prompt
    assert "NIFTY50" in prompt
    assert "Cash" in prompt
    assert "Avoid generic scenarios" in prompt


def test_apply_scenario_shocks_is_case_insensitive_and_does_not_mutate_original(caplog):
    shock_map = {"btc": -60, "nifty50": -25}

    modified = apply_scenario_shocks(BASE_PORTFOLIO, shock_map)

    assert modified is not BASE_PORTFOLIO
    assert BASE_PORTFOLIO["assets"][0]["expected_crash_pct"] == -70
    assert modified["assets"][0]["expected_crash_pct"] == -60
    assert modified["assets"][1]["expected_crash_pct"] == -25
    assert modified["assets"][2]["expected_crash_pct"] == 0
    assert "not found in shock_map" in caplog.text


def test_compute_scenario_result_uses_ai_shock_map_values_only():
    metrics = compute_scenario_result(
        BASE_PORTFOLIO,
        {"BTC": -50, "NIFTY50": -20, "Cash": 0},
    )

    assert metrics["post_crash_value"] == pytest.approx(690_000)
    assert metrics["runway_months"] == pytest.approx(13.8)
    assert metrics["ruin_test"] == "PASS"


def test_compute_why_this_breaks_identifies_largest_actual_loss_contributor():
    shock_map = {"BTC": -50, "NIFTY50": -20, "Cash": 0}
    metrics = compute_scenario_result(BASE_PORTFOLIO, shock_map)
    metrics["pre_crash_value"] = BASE_PORTFOLIO["total_value_inr"]

    why = compute_why_this_breaks(BASE_PORTFOLIO, shock_map, metrics)

    assert why["largest_loss_asset"] == "BTC"
    assert why["total_loss_inr"] == pytest.approx(310_000)
    assert why["loss_breakdown"][0]["loss_inr"] == pytest.approx(250_000)
    assert why["largest_loss_pct_of_total"] == pytest.approx(250_000 / 310_000 * 100)


def test_breakpoint_detects_already_failing_portfolio():
    portfolio = {
        "total_value_inr": 100_000,
        "monthly_expenses_inr": 20_000,
        "assets": [{"name": "Cash", "allocation_pct": 100, "expected_crash_pct": 0}],
    }

    result = find_portfolio_breakpoint(portfolio)

    assert result["already_failing"] is True
    assert result["break_pct"] == 0.0


def test_breakpoint_detects_never_failing_with_large_cash_buffer():
    portfolio = {
        "total_value_inr": 2_000_000,
        "monthly_expenses_inr": 10_000,
        "assets": [
            {"name": "BTC", "allocation_pct": 10, "expected_crash_pct": -70},
            {"name": "Cash", "allocation_pct": 90, "expected_crash_pct": 0},
        ],
    }

    result = find_portfolio_breakpoint(portfolio)

    assert result["never_failing"] is True
    assert result["break_pct"] == 100.0


def test_breakpoint_binary_searches_normal_portfolio_failure_point():
    portfolio = {
        "total_value_inr": 1_000_000,
        "monthly_expenses_inr": 50_000,
        "assets": [
            {"name": "BTC", "allocation_pct": 80, "expected_crash_pct": -70},
            {"name": "Cash", "allocation_pct": 20, "expected_crash_pct": 0},
        ],
    }

    result = find_portfolio_breakpoint(portfolio)

    assert result["already_failing"] is False
    assert result["never_failing"] is False
    assert result["break_pct"] == pytest.approx(50.0, abs=0.1)


def test_decision_insight_marks_baseline_failure_as_not_resilient():
    portfolio = {
        "total_value_inr": 100_000,
        "monthly_expenses_inr": 20_000,
        "assets": [{"name": "Reliance", "allocation_pct": 100, "expected_crash_pct": -30}],
    }
    ranked = [
        {"name": "A", "runway": 4.0, "verdict": "FAIL", "primary_culprit": "Reliance", "loss_pct": 10},
        {"name": "B", "runway": 5.0, "verdict": "FAIL", "primary_culprit": "Reliance", "loss_pct": 5},
        {"name": "C", "runway": 5.0, "verdict": "FAIL", "primary_culprit": "Reliance", "loss_pct": 0},
    ]

    insight = build_decision_insight(portfolio, ranked, compute_baseline_runway(portfolio))

    assert insight["status_label"] == "NOT RESILIENT"
    assert insight["primary_issue"] == "Insufficient capital relative to expenses"
    assert "increase total portfolio value" in insight["recommendations"]
    assert "reduce monthly expenses" in insight["recommendations"]
    assert "cannot pass" in insight["fixability"]


def test_decision_insight_marks_all_pass_scenarios_as_resilient():
    ranked = [
        {"name": "A", "runway": 20.0, "verdict": "PASS", "primary_culprit": "BTC", "loss_pct": 20},
        {"name": "B", "runway": 30.0, "verdict": "PASS", "primary_culprit": "NIFTY50", "loss_pct": 10},
    ]

    insight = build_decision_insight(BASE_PORTFOLIO, ranked, compute_baseline_runway(BASE_PORTFOLIO))

    assert insight["status_label"] == "RESILIENT"
    assert "All 2 scenarios pass" in insight["reasons"][0]
    assert any("BTC" in item for item in insight["vulnerabilities"])


def test_report_formatter_prints_correlation_effect_for_same_category_assets(capsys):
    portfolio = {
        "total_value_inr": 1_000_000,
        "monthly_expenses_inr": 50_000,
        "assets": [
            {"name": "Reliance", "allocation_pct": 50, "expected_crash_pct": -30},
            {"name": "Zomato", "allocation_pct": 50, "expected_crash_pct": -40},
        ],
    }
    scenario = _scenario(
        shock_map={"Reliance": -30, "Zomato": -40},
    )
    metrics = compute_scenario_result(portfolio, scenario["shock_map"])
    metrics["pre_crash_value"] = portfolio["total_value_inr"]
    why = compute_why_this_breaks(portfolio, scenario["shock_map"], metrics)

    print_scenario(
        ScenarioRenderContext(
            scenario=scenario,
            metrics=metrics,
            why=why,
            index=1,
            total=1,
            portfolio=portfolio,
            baseline_runway=20,
        )
    )

    out = capsys.readouterr().out
    assert "CORRELATION EFFECT" in out
    assert "Reliance and Zomato" in out
    assert "Indian equities" in out


def test_task4_dry_run_cli_completes_without_openai(capsys):
    result = task4_main(["--dry-run"])

    out = capsys.readouterr().out
    assert result == 0
    assert "[DRY RUN] Skipping AI call" in out
    assert "SCENARIO RANKING" in out
    assert "FINAL DECISION SUMMARY" in out


def test_task4_input_uses_task4_portfolio_entry_without_crash_assumptions(
    monkeypatch,
    capsys,
):
    def fake_portfolio_input():
        return {
            "total_value_inr": 1_000_000,
            "monthly_expenses_inr": 50_000,
            "assets": [
                {"name": "ETH", "allocation_pct": 40, "expected_crash_pct": -30},
                {"name": "NIFTY", "allocation_pct": 50, "expected_crash_pct": -30},
                {"name": "Cash", "allocation_pct": 10, "expected_crash_pct": 0},
            ],
        }

    monkeypatch.setattr(
        "task4_crash_story.get_portfolio_from_user",
        fake_portfolio_input,
    )

    result = task4_main(["--input", "--dry-run"])

    out = capsys.readouterr().out
    assert result == 0
    assert "Known asset classes" not in out
    assert "CRASH SCENARIO ANALYSIS" in out
