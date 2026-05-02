"""Tests for core/ai_explainer.py.

Real API calls are mocked. We test:
- prompt construction (the right numbers reach the prompt)
- response parsing (valid JSON, missing fields, bad verdict, fenced JSON)
- orchestration (explain_portfolio wires the three layers correctly)
- the critique flow (parse_critique + critique_explanation)
"""

from __future__ import annotations

import json
import sys
import types

import pytest

from core.ai_explainer import (
    VALID_VERDICTS,
    build_user_prompt,
    call_openai,
    critique_explanation,
    explain_portfolio,
    parse_critique,
    parse_response,
)
from config.prompts import CRITIQUE_SYSTEM_PROMPT, SYSTEM_PROMPT
from core.risk_calculator import build_report, Asset


SAMPLE_PORTFOLIO = {
    "total_value_inr": 10_000_000,
    "monthly_expenses_inr": 80_000,
    "assets": [
        {"name": "BTC",     "allocation_pct": 30, "expected_crash_pct": -80},
        {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
        {"name": "GOLD",    "allocation_pct": 20, "expected_crash_pct": -15},
        {"name": "CASH",    "allocation_pct": 10, "expected_crash_pct":   0},
    ],
}


def _report():
    return build_report(
        total_value=SAMPLE_PORTFOLIO["total_value_inr"],
        monthly_expenses=SAMPLE_PORTFOLIO["monthly_expenses_inr"],
        assets=[Asset(**a) for a in SAMPLE_PORTFOLIO["assets"]],
    )


# ---------- 1. prompt logic ----------

def test_build_user_prompt_includes_all_assets():
    prompt = build_user_prompt(SAMPLE_PORTFOLIO, _report(), tone="beginner")
    for asset in SAMPLE_PORTFOLIO["assets"]:
        assert asset["name"] in prompt
    assert "30% of portfolio" in prompt
    assert "-80%" in prompt


def test_build_user_prompt_includes_computed_metrics():
    prompt = build_user_prompt(SAMPLE_PORTFOLIO, _report(), tone="beginner")
    # post_crash_value for the spec portfolio is exactly 5,700,000
    assert "5,700,000" in prompt
    # runway = 5,700,000 / 80,000 = 71.25 months -> PASS
    assert "71.2" in prompt or "71.3" in prompt
    assert "PASS" in prompt
    assert "BTC" in prompt  # largest risk asset


def test_system_prompt_contains_verdict_and_suggestion_rules():
    assert "Verdict guidance" in SYSTEM_PROMPT
    assert "Aggressive: runway < 12 months" in SYSTEM_PROMPT
    assert "target percentage" in SYSTEM_PROMPT
    assert "Do not call a low-runway portfolio safe" in SYSTEM_PROMPT


def test_user_prompt_contains_silent_quality_checklist():
    prompt = build_user_prompt(SAMPLE_PORTFOLIO, _report(), tone="beginner")
    assert "Did I mention post-crash value, loss %, runway, and ruin test?" in prompt
    assert "Is my suggested change specific, numerical, and actionable?" in prompt


def test_critique_prompt_checks_verdict_and_missing_metrics():
    assert "Verdict correctness" in CRITIQUE_SYSTEM_PROMPT
    assert "Missing metrics" in CRITIQUE_SYSTEM_PROMPT
    assert "Narrative consistency" in CRITIQUE_SYSTEM_PROMPT


def test_build_user_prompt_renders_concentration_no():
    # spec portfolio: 40% NIFTY50 is exactly at threshold; strict > 40 means NO
    prompt = build_user_prompt(SAMPLE_PORTFOLIO, _report(), tone="beginner")
    assert "Concentration warning (any asset > 40%): NO" in prompt


def test_build_user_prompt_picks_correct_tone():
    beginner = build_user_prompt(SAMPLE_PORTFOLIO, _report(), tone="beginner")
    expert = build_user_prompt(SAMPLE_PORTFOLIO, _report(), tone="expert")
    assert "new to investing" in beginner
    assert "comfortable with portfolio mechanics" in expert
    assert beginner != expert


def test_build_user_prompt_rejects_bad_tone():
    with pytest.raises(ValueError, match="tone must be one of"):
        build_user_prompt(SAMPLE_PORTFOLIO, _report(), tone="rude")


def test_build_user_prompt_handles_zero_expenses_runway():
    portfolio = {
        "total_value_inr": 1_000_000,
        "monthly_expenses_inr": 0,
        "assets": SAMPLE_PORTFOLIO["assets"],
    }
    report = build_report(
        total_value=1_000_000,
        monthly_expenses=0,
        assets=[Asset(**a) for a in portfolio["assets"]],
    )
    prompt = build_user_prompt(portfolio, report, tone="beginner")
    assert "infinite" in prompt


# ---------- 3. parsing (tested before 2 because it's pure) ----------

def test_parse_response_accepts_valid_json():
    raw = json.dumps({
        "summary": "Portfolio is risky.",
        "doing_well": "Cash buffer of 10%.",
        "consider_changing": "Reduce BTC from 30% to 15%.",
        "verdict": "Aggressive",
    })
    parsed = parse_response(raw)
    assert parsed["verdict"] == "Aggressive"
    assert parsed["summary"] == "Portfolio is risky."


def test_parse_response_strips_markdown_fence():
    fenced = "```json\n" + json.dumps({
        "summary": "ok", "doing_well": "ok",
        "consider_changing": "ok", "verdict": "Balanced",
    }) + "\n```"
    parsed = parse_response(fenced)
    assert parsed["verdict"] == "Balanced"


def test_parse_response_rejects_invalid_verdict():
    raw = json.dumps({
        "summary": "x", "doing_well": "x",
        "consider_changing": "x", "verdict": "YOLO",
    })
    with pytest.raises(ValueError, match="not one of"):
        parse_response(raw)


def test_parse_response_rejects_missing_field():
    raw = json.dumps({
        "summary": "x", "doing_well": "x", "verdict": "Aggressive",
        # consider_changing missing
    })
    with pytest.raises(ValueError, match="missing required fields"):
        parse_response(raw)


def test_parse_response_rejects_invalid_json():
    with pytest.raises(ValueError, match="not return valid JSON"):
        parse_response("this is not json")


def test_parse_response_rejects_non_object_json():
    with pytest.raises(ValueError, match="non-object JSON"):
        parse_response('["a", "b"]')


def test_valid_verdicts_constant_matches_spec():
    assert VALID_VERDICTS == {"Aggressive", "Balanced", "Conservative"}


# ---------- critique parsing ----------

def test_parse_critique_accepts_valid_json():
    raw = json.dumps({
        "accuracy_issues": ["misquoted runway as 70 months"],
        "specificity_issues": [],
        "missed_points": ["did not flag 30% BTC"],
        "overall_grade": "B",
    })
    parsed = parse_critique(raw)
    assert parsed["overall_grade"] == "B"
    assert parsed["specificity_issues"] == []


def test_parse_critique_rejects_bad_grade():
    raw = json.dumps({
        "accuracy_issues": [], "specificity_issues": [],
        "missed_points": [], "overall_grade": "Z",
    })
    with pytest.raises(ValueError, match="not A/B/C/D/F"):
        parse_critique(raw)


# ---------- 2. orchestration (mocking the API call) ----------

def _fake_response(verdict: str = "Aggressive") -> str:
    return json.dumps({
        "summary": "Portfolio leans aggressive due to BTC.",
        "doing_well": "10% in cash provides a stable runway.",
        "consider_changing": "Cut BTC from 30% to 15% to reduce single-asset risk.",
        "verdict": verdict,
    })


def test_explain_portfolio_orchestrates_three_layers(monkeypatch):
    captured: dict[str, str] = {}

    def fake_call(system: str, user: str, *, model: str, **_kwargs) -> str:
        captured["system"] = system
        captured["user"] = user
        captured["model"] = model
        return _fake_response("Aggressive")

    monkeypatch.setattr("core.ai_explainer.call_openai", fake_call)

    explanation = explain_portfolio(SAMPLE_PORTFOLIO, tone="beginner", model="test-model")

    assert "BTC" in captured["user"]
    assert "5,700,000" in captured["user"]
    assert "JSON" in captured["system"]
    assert explanation.verdict == "Aggressive"
    assert explanation.model == "test-model"
    assert explanation.tone == "beginner"
    assert explanation.raw_response == _fake_response("Aggressive")


def test_explain_portfolio_propagates_parse_error(monkeypatch):
    monkeypatch.setattr(
        "core.ai_explainer.call_openai",
        lambda *args, **kwargs: '{"summary": "x"}',  # missing fields
    )
    with pytest.raises(ValueError, match="missing required fields"):
        explain_portfolio(SAMPLE_PORTFOLIO, tone="beginner")


def test_explain_portfolio_rejects_unknown_tone():
    with pytest.raises(ValueError, match="tone must be one of"):
        explain_portfolio(SAMPLE_PORTFOLIO, tone="grumpy")


def test_call_openai_wraps_provider_errors(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class BrokenCompletions:
        def create(self, **kwargs):
            raise RuntimeError("network down")

    class BrokenClient:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {
                "completions": BrokenCompletions()
            })()

    fake_openai = types.SimpleNamespace(OpenAI=BrokenClient)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    with pytest.raises(RuntimeError, match="OpenAI API call failed after 1 attempt"):
        call_openai("system", "user", attempts=1)


def test_call_openai_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    sleeps: list[float] = []
    call_count = {"n": 0}

    class FlakyCompletions:
        def create(self, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError("temporary provider error")
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(content=_fake_response("Balanced"))
                    )
                ]
            )

    class FlakyClient:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {
                "completions": FlakyCompletions()
            })()

    fake_openai = types.SimpleNamespace(OpenAI=FlakyClient)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setattr("core.ai_explainer.random.uniform", lambda *_args: 0.0)
    monkeypatch.setattr("core.ai_explainer.time.sleep", sleeps.append)

    raw = call_openai("system", "user", attempts=3, backoff_sec=0.1)

    assert json.loads(raw)["verdict"] == "Balanced"
    assert call_count["n"] == 3
    assert sleeps == [0.1, 0.2]


def test_call_openai_rejects_invalid_retry_config():
    with pytest.raises(ValueError, match="attempts must be at least 1"):
        call_openai("system", "user", attempts=0)

    with pytest.raises(ValueError, match="backoff_sec cannot be negative"):
        call_openai("system", "user", backoff_sec=-1)


def test_critique_explanation_calls_api_with_advisor_block(monkeypatch):
    primary_response = _fake_response("Aggressive")
    critique_response = json.dumps({
        "accuracy_issues": [],
        "specificity_issues": ["doing_well is generic"],
        "missed_points": [],
        "overall_grade": "B",
    })
    seen_prompts: list[str] = []
    call_idx = {"n": 0}

    def fake_call(system: str, user: str, *, model: str, **_kwargs) -> str:
        seen_prompts.append(user)
        call_idx["n"] += 1
        # 1st call -> primary explanation; 2nd call -> critique
        return primary_response if call_idx["n"] == 1 else critique_response

    monkeypatch.setattr("core.ai_explainer.call_openai", fake_call)

    explanation = explain_portfolio(SAMPLE_PORTFOLIO, tone="beginner")
    critique = critique_explanation(explanation, SAMPLE_PORTFOLIO)

    assert critique.overall_grade == "B"
    assert critique.specificity_issues == ("doing_well is generic",)
    # second prompt embeds the advisor's JSON block
    assert "Advisor explanation under review" in seen_prompts[1]
    assert "Aggressive" in seen_prompts[1]
