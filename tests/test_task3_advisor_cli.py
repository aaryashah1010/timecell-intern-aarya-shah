"""Tests for the Task 3 CLI surface — argparse + the shared portfolio input helpers."""

import sys

from cli.portfolio_input import collect_portfolio_dict, prompt_float
from core.ai_explainer import Critique
from task3_advisor import parse_args, render_critique


def test_parse_args_defaults_to_interactive(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["task3_advisor.py"])
    args = parse_args()
    assert args.portfolio is None


def test_parse_args_accepts_optional_portfolio_file(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["task3_advisor.py", "--portfolio", "data/x.json"])
    args = parse_args()
    assert str(args.portfolio) in {"data/x.json", "data\\x.json"}


def test_prompt_float_rejects_bad_then_accepts(monkeypatch, capsys):
    values = iter(["", "abc", "-1", "1,00,000"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    assert prompt_float("Value : ", allow_zero=False) == 100000
    out = capsys.readouterr().out
    assert "please enter a number" in out
    assert "not a valid number" in out
    assert "cannot be negative" in out


def test_collect_portfolio_dict_uses_crash_assumptions(monkeypatch):
    values = iter([
        "1000000",  # total value
        "50000",    # monthly expenses
        "BTC",
        "40",
        "Gold",
        "20",
        "",         # finish; remaining 40% becomes Cash
    ])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    portfolio = collect_portfolio_dict()

    assert portfolio["total_value_inr"] == 1_000_000
    assert portfolio["monthly_expenses_inr"] == 50_000
    assert portfolio["assets"] == [
        {"name": "BTC",  "allocation_pct": 40.0, "expected_crash_pct": -70.0},
        {"name": "Gold", "allocation_pct": 20.0, "expected_crash_pct": -15.0},
        {"name": "Cash", "allocation_pct": 40.0, "expected_crash_pct":   0.0},
    ]


def test_collect_portfolio_dict_unknown_asset_uses_fallback(monkeypatch):
    values = iter([
        "1000000",
        "50000",
        "Pepsi",
        "100",
    ])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    portfolio = collect_portfolio_dict()

    assert portfolio["assets"] == [
        {"name": "Pepsi", "allocation_pct": 100.0, "expected_crash_pct": -30.0},
    ]


def test_render_critique_uses_sentence_when_issue_list_is_empty():
    critique = Critique(
        accuracy_issues=(),
        specificity_issues=(),
        missed_points=(),
        overall_grade="A",
        raw_response="{}",
        model="test-model",
    )

    output = render_critique(critique)

    assert "(none)" not in output
    assert "No major accuracy issue" in output
    assert "No major specificity gap" in output
    assert "No major missed point" in output
