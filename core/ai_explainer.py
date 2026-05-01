"""AI advisor: build prompt, call OpenAI, parse the structured response.

Separation of concerns (per the rubric):
    1. PROMPT LOGIC      -> build_user_prompt (uses templates from config/prompts.py)
    2. API CALL          -> call_openai
    3. OUTPUT PARSING    -> parse_response

`explain_portfolio` orchestrates the three. `critique_explanation` is the bonus
second LLM call that critiques the first.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass
from math import isfinite

from config.prompts import (
    CRITIQUE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    TONE_INSTRUCTIONS,
    USER_PROMPT_TEMPLATE,
    build_asset_lines,
)
from core.risk_calculator import Asset, RiskReport, build_report

log = logging.getLogger("timecell.advisor")

VALID_VERDICTS: frozenset[str] = frozenset({"Aggressive", "Balanced", "Conservative"})
DEFAULT_MODEL: str = "gpt-4o-mini"
DEFAULT_TEMPERATURE: float = 0.4
DEFAULT_TIMEOUT_SEC: float = 30.0
DEFAULT_OPENAI_ATTEMPTS: int = 3
DEFAULT_OPENAI_BACKOFF_SEC: float = 1.5


@dataclass(frozen=True)
class Explanation:
    summary: str
    doing_well: str
    consider_changing: str
    verdict: str
    raw_response: str
    model: str
    tone: str


@dataclass(frozen=True)
class Critique:
    accuracy_issues: tuple[str, ...]
    specificity_issues: tuple[str, ...]
    missed_points: tuple[str, ...]
    overall_grade: str
    raw_response: str
    model: str


# ---------- 1. PROMPT LOGIC ----------

def build_user_prompt(portfolio: dict, report: RiskReport, tone: str) -> str:
    if tone not in TONE_INSTRUCTIONS:
        raise ValueError(
            f"tone must be one of {sorted(TONE_INSTRUCTIONS)}, got {tone!r}"
        )

    runway_display = (
        f"{report.runway_months:.1f}"
        if isfinite(report.runway_months)
        else "infinite (no monthly expenses)"
    )

    return USER_PROMPT_TEMPLATE.format(
        total_value=portfolio["total_value_inr"],
        monthly_expenses=portfolio["monthly_expenses_inr"],
        asset_lines=build_asset_lines(portfolio["assets"]),
        post_crash_value=report.post_crash_value,
        absolute_loss=report.absolute_loss,
        loss_pct=report.loss_pct,
        runway_display=runway_display,
        ruin_test="PASS" if report.survives_one_year else "FAIL",
        largest_risk_asset=report.largest_risk_asset or "none (no crash exposure)",
        concentration_warning=(
            f"YES ({', '.join(report.concentrated_assets)})"
            if report.concentration_warning
            else "NO"
        ),
        tone_instruction=TONE_INSTRUCTIONS[tone],
    )


# ---------- 2. API CALL ----------

def call_openai(
    system: str,
    user: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    attempts: int = DEFAULT_OPENAI_ATTEMPTS,
    backoff_sec: float = DEFAULT_OPENAI_BACKOFF_SEC,
    json_response: bool = True,
) -> str:
    """Send a chat completion to OpenAI and return the raw text content."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if backoff_sec < 0:
        raise ValueError("backoff_sec cannot be negative")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env or export it in your shell."
        )

    from openai import OpenAI  # local import: don't pay it for unit tests

    client = OpenAI(api_key=api_key, timeout=timeout_sec)
    log.info("calling openai model=%s temperature=%.2f", model, temperature)

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
            }
            if json_response:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            break
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                raise RuntimeError(
                    f"OpenAI API call failed after {attempts} attempt(s): {exc}"
                ) from exc

            delay = backoff_sec * (2 ** (attempt - 1))
            jitter = random.uniform(0.0, max(0.0, delay * 0.25))
            sleep_for = delay + jitter
            log.warning(
                "openai call failed attempt=%d/%d; retrying in %.2fs: %s",
                attempt,
                attempts,
                sleep_for,
                exc,
            )
            time.sleep(sleep_for)
    else:
        raise RuntimeError(f"OpenAI API call failed: {last_error}")

    try:
        content = response.choices[0].message.content or ""
    except (AttributeError, IndexError) as exc:
        raise RuntimeError("OpenAI response did not include message content") from exc

    if not content.strip():
        raise RuntimeError("OpenAI returned an empty response")

    log.info("openai response received chars=%d", len(content))
    return content


# ---------- 3. OUTPUT PARSING ----------

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_markdown_fence(text: str) -> str:
    return _FENCE_RE.sub("", text.strip()).strip()


def parse_response(raw: str) -> dict[str, str]:
    """Parse a primary-explanation JSON response. Validates required fields and verdict."""
    cleaned = _strip_markdown_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM did not return valid JSON: {exc.msg}; first 200 chars: {raw[:200]!r}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(f"LLM returned non-object JSON ({type(data).__name__})")

    required = ("summary", "doing_well", "consider_changing", "verdict")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"LLM response missing required fields: {missing}")

    verdict = str(data["verdict"]).strip()
    if verdict not in VALID_VERDICTS:
        raise ValueError(
            f"LLM verdict {verdict!r} is not one of {sorted(VALID_VERDICTS)}"
        )

    return {
        "summary": str(data["summary"]).strip(),
        "doing_well": str(data["doing_well"]).strip(),
        "consider_changing": str(data["consider_changing"]).strip(),
        "verdict": verdict,
    }


def parse_critique(raw: str) -> dict:
    """Parse a critique JSON response. Validates required fields and grade."""
    cleaned = _strip_markdown_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Critique LLM did not return valid JSON: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Critique JSON is not an object ({type(data).__name__})")

    required = ("accuracy_issues", "specificity_issues", "missed_points", "overall_grade")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Critique response missing required fields: {missing}")

    if str(data["overall_grade"]).strip().upper() not in {"A", "B", "C", "D", "F"}:
        raise ValueError(f"Critique grade {data['overall_grade']!r} is not A/B/C/D/F")

    return data


# ---------- ORCHESTRATION ----------

def _build_report_from_portfolio(portfolio: dict) -> RiskReport:
    return build_report(
        total_value=portfolio["total_value_inr"],
        monthly_expenses=portfolio["monthly_expenses_inr"],
        assets=[
            Asset(
                name=a["name"],
                allocation_pct=a["allocation_pct"],
                expected_crash_pct=a["expected_crash_pct"],
            )
            for a in portfolio["assets"]
        ],
    )


def explain_portfolio(
    portfolio: dict,
    *,
    tone: str = "beginner",
    model: str = DEFAULT_MODEL,
) -> Explanation:
    report = _build_report_from_portfolio(portfolio)
    user_prompt = build_user_prompt(portfolio, report, tone)
    raw = call_openai(SYSTEM_PROMPT, user_prompt, model=model)
    parsed = parse_response(raw)
    return Explanation(
        summary=parsed["summary"],
        doing_well=parsed["doing_well"],
        consider_changing=parsed["consider_changing"],
        verdict=parsed["verdict"],
        raw_response=raw,
        model=model,
        tone=tone,
    )


def critique_explanation(
    explanation: Explanation,
    portfolio: dict,
    *,
    model: str = DEFAULT_MODEL,
) -> Critique:
    report = _build_report_from_portfolio(portfolio)
    metrics_block = build_user_prompt(portfolio, report, tone=explanation.tone)
    advisor_block = json.dumps(
        {
            "summary": explanation.summary,
            "doing_well": explanation.doing_well,
            "consider_changing": explanation.consider_changing,
            "verdict": explanation.verdict,
        },
        indent=2,
    )
    user_prompt = (
        "## Portfolio metrics (source of truth)\n\n"
        f"{metrics_block}\n\n"
        "## Advisor explanation under review\n\n"
        f"```json\n{advisor_block}\n```\n\n"
        "Critique the explanation now. Respond with the JSON object."
    )
    raw = call_openai(CRITIQUE_SYSTEM_PROMPT, user_prompt, model=model)
    parsed = parse_critique(raw)
    return Critique(
        accuracy_issues=tuple(str(x) for x in parsed["accuracy_issues"]),
        specificity_issues=tuple(str(x) for x in parsed["specificity_issues"]),
        missed_points=tuple(str(x) for x in parsed["missed_points"]),
        overall_grade=str(parsed["overall_grade"]).strip().upper(),
        raw_response=raw,
        model=model,
    )
