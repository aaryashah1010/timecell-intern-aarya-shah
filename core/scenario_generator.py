"""Generate portfolio-specific macro stress scenarios with AI.

The model returns narrative fields and shock percentages only. Portfolio values,
runway, loss amounts, and verdicts are computed by deterministic Python modules.
"""

from __future__ import annotations

import json
import logging
import re

from config.prompts import CRASH_STORY_SYSTEM_PROMPT
from core.ai_explainer import call_openai

log = logging.getLogger("crash_story.scenario_generator")

OPENAI_MODEL: str = "gpt-4o"
OPENAI_TEMPERATURE: float = 0.7
OPENAI_TIMEOUT_SEC: float = 30.0
OPENAI_ATTEMPTS: int = 3
OPENAI_BACKOFF_SEC: float = 2.0
SCENARIO_COUNT: int = 5
MIN_SCENARIO_COUNT: int = 4
MAX_SCENARIO_COUNT: int = 5

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def build_user_prompt(portfolio: dict) -> str:
    """Build a portfolio-aware prompt for stress-scenario generation."""
    total = portfolio["total_value_inr"]
    expenses = portfolio["monthly_expenses_inr"]
    asset_names = [asset["name"] for asset in portfolio["assets"]]

    lines = ["PORTFOLIO COMPOSITION:"]
    for asset in portfolio["assets"]:
        name = asset["name"]
        pct = asset["allocation_pct"]
        flag = _concentration_flag(name, pct)
        lines.append(f"  {name}: {pct}%{flag}")

    lines.append(f"\nTotal Portfolio Value: INR {total:,.0f}")
    lines.append(f"Monthly Expenses: INR {expenses:,.0f}")
    lines.append(
        f"""
INSTRUCTION:
Generate exactly {SCENARIO_COUNT} macro stress scenarios for this specific
portfolio. Return a JSON array of exactly {SCENARIO_COUNT} objects.

Each object must have these exact keys:

  "scenario_id"       : integer 1 through {SCENARIO_COUNT}
  "name"              : string - specific named macro event, not generic
  "narrative"         : string - exactly 2-3 sentences, Bloomberg brief style
  "shock_map"         : object - keys are asset names, values are integer
                        percentage change, for example -71, 8, or 0
  "severity"          : "EXTREME" | "HIGH" | "MEDIUM" | "LOW"
  "severity_reason"   : string - one sentence explaining severity rating
  "likelihood"        : "HIGH" | "MEDIUM" | "LOW"
  "likelihood_reason" : string - one sentence explaining likelihood rating
  "takeaway"          : string - one sentence, plain English, investor-facing

CRITICAL SHOCK MAP REQUIREMENT:
Your shock_map MUST include every asset listed below. No exceptions.
If an asset is unaffected by the scenario, use 0. Do not skip any asset.

Assets to cover in every shock_map: {asset_names}

PORTFOLIO-AWARE REQUIREMENT:
Tie each scenario directly to specific assets in this portfolio.
- Reliance -> oil prices, Indian macro, fiscal policy, and regulation risk.
- Zomato -> consumer demand, startup funding environment, and discretionary spending.
- Tesla -> interest rates, US technology sentiment, and growth-stock valuation risk.
- Crypto -> regulation, exchange risk, custody risk, and liquidity stress.
- If portfolio has BTC, include crypto regulation, exchange, or custody risk.
- If portfolio has Tesla, include US technology and rate-sensitivity risk.
- If portfolio has Indian equities, include RBI, FII flows, election, or rupee risk.
- If portfolio has DOGE, include speculative-token crash risk.
- If portfolio has high cash, include inflation erosion or bank-failure risk where relevant.
- Avoid generic scenarios. Each scenario must explicitly affect at least 2 assets
  in the portfolio through the shock_map and narrative.

SEVERITY AND TAIL-RISK REQUIREMENT:
- At least one scenario MUST either likely reduce runway below 12 months or cause loss above 25%.
- At least one scenario MUST be HIGH or EXTREME severity.
- Include one EXTREME tail-risk scenario, such as BTC -70% to -85% and equities -30% to -50%.
- Severity guidelines: LOW = under 10% loss, MEDIUM = 10-25% loss,
  HIGH = 25-40% loss, EXTREME = above 40% loss.

TAKEAWAY QUALITY REQUIREMENT:
Make the takeaway asset-specific and actionable.
Bad: "Consider diversification."
Good: "Your BTC allocation alone can materially affect survival in stress events;
reducing crypto exposure or increasing defensive assets improves resilience."

Return nothing except the raw JSON array.
No markdown. No explanation. No code fences.
"""
    )
    return "\n".join(lines)


def generate_scenarios(portfolio: dict) -> list[dict]:
    """Call AI and return validated scenario dictionaries.

    Uses the shared `core.ai_explainer.call_openai` wrapper, which handles
    retries, backoff, and provider-error wrapping. ``json_response=False``
    because the model returns a JSON array, not an object.
    """
    user_prompt = build_user_prompt(portfolio)

    try:
        raw = call_openai(
            CRASH_STORY_SYSTEM_PROMPT,
            user_prompt,
            model=OPENAI_MODEL,
            temperature=OPENAI_TEMPERATURE,
            timeout_sec=OPENAI_TIMEOUT_SEC,
            attempts=OPENAI_ATTEMPTS,
            backoff_sec=OPENAI_BACKOFF_SEC,
            json_response=False,
        )
    except RuntimeError as exc:
        # call_openai wraps missing API key + provider failures as RuntimeError;
        # surface as EnvironmentError so the CLI message stays consistent.
        raise EnvironmentError(str(exc)) from exc

    try:
        scenarios = validate_scenarios(parse_scenarios(raw))
    except json.JSONDecodeError as exc:
        log.error("AI returned invalid JSON: %s", exc)
        log.debug("raw response:\n%s", raw)
        raise ValueError("AI returned invalid JSON. Check logs for raw output.") from exc

    if not MIN_SCENARIO_COUNT <= len(scenarios) <= MAX_SCENARIO_COUNT:
        raise ValueError(
            f"Need {MIN_SCENARIO_COUNT}-{MAX_SCENARIO_COUNT} valid scenarios, "
            f"got {len(scenarios)}."
        )

    if len(scenarios) < SCENARIO_COUNT:
        log.warning(
            "Expected %d scenarios, got %d. Continuing with what was returned.",
            SCENARIO_COUNT, len(scenarios),
        )

    log.info("generated %d crash scenarios", len(scenarios))
    return scenarios


def parse_scenarios(raw: str) -> list[dict]:
    """Parse raw model output into a JSON array of scenarios."""
    cleaned = _strip_markdown_fence(raw)
    scenarios = json.loads(cleaned)
    if not isinstance(scenarios, list):
        raise ValueError("Response is not a JSON array.")
    for index, scenario in enumerate(scenarios, 1):
        if not isinstance(scenario, dict):
            raise ValueError(f"Scenario {index} is not a JSON object.")
    return scenarios


def validate_scenarios(scenarios: list[dict]) -> list[dict]:
    """Return only scenarios with required fields and numeric shock values."""
    if not MIN_SCENARIO_COUNT <= len(scenarios) <= MAX_SCENARIO_COUNT:
        log.warning(
            "Scenario count is %d; expected %d-%d.",
            len(scenarios), MIN_SCENARIO_COUNT, MAX_SCENARIO_COUNT,
        )

    valid: list[dict] = []
    for index, scenario in enumerate(scenarios, 1):
        reason = _scenario_validation_error(scenario)
        if reason:
            log.warning("Invalid scenario skipped: #%d - %s", index, reason)
            continue
        valid.append(scenario)

    if len(valid) > MAX_SCENARIO_COUNT:
        log.warning(
            "%d valid scenarios returned; using first %d.",
            len(valid), MAX_SCENARIO_COUNT,
        )
        valid = valid[:MAX_SCENARIO_COUNT]

    return valid


def _strip_markdown_fence(text: str) -> str:
    """Remove accidental markdown fences from model output."""
    return _FENCE_RE.sub("", text.strip()).strip()


def _scenario_validation_error(scenario: dict) -> str | None:
    """Return a validation error string, or None if the scenario is usable."""
    name = scenario.get("name")
    if not isinstance(name, str) or not name.strip():
        return "missing scenario name"

    shock_map = scenario.get("shock_map")
    if not isinstance(shock_map, dict):
        return "missing shock_map"
    if not shock_map:
        return "shock_map is empty"

    for asset_name, shock_value in shock_map.items():
        if not isinstance(asset_name, str) or not asset_name.strip():
            return "shock_map contains an empty asset name"
        if not isinstance(shock_value, (int, float)):
            return f"shock for {asset_name!r} is not numeric"

    return None


def _concentration_flag(name: str, allocation_pct: float) -> str:
    """Return a short prompt hint for concentrated or notable holdings."""
    name_lower = name.lower()
    if any(token in name_lower for token in ("btc", "bitcoin", "eth", "crypto")):
        if allocation_pct >= 25:
            return "  <- HIGH crypto exposure"
    elif any(token in name_lower for token in ("nifty", "sensex", "equity", "stock")):
        if allocation_pct >= 40:
            return "  <- dominant equity position"
    elif "gold" in name_lower:
        if allocation_pct >= 20:
            return "  <- significant gold allocation"
    elif any(token in name_lower for token in ("cash", "fd", "savings")):
        if allocation_pct >= 20:
            return "  <- high cash / conservative buffer"
    elif "real estate" in name_lower or "reit" in name_lower:
        return "  <- illiquid asset"
    return ""
