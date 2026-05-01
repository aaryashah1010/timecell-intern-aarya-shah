"""Build the portfolio-level decision insight shown at the end of Task 4.

Pulled out of `task4_crash_story.py` so the entry point only orchestrates
I/O and rendering. All numeric inputs come from `compute_risk_metrics`
and the per-scenario `compute_why_this_breaks` results.
"""

from __future__ import annotations

from config.asset_categories import is_cash, is_crypto, is_gold
from config.thresholds import CONCENTRATION_ALERT_PCT, RUNWAY_THRESHOLD_MONTHS


def compute_baseline_runway(portfolio: dict) -> float:
    """Return runway in months before any market stress is applied."""
    monthly_expenses = portfolio["monthly_expenses_inr"]
    if monthly_expenses <= 0:
        return float("inf")
    return portfolio["total_value_inr"] / monthly_expenses


def build_decision_insight(
    portfolio: dict,
    ranked: list[dict],
    baseline_runway: float,
) -> dict:
    """Build portfolio-level strengths, vulnerabilities, and recommendations."""
    assets = portfolio["assets"]
    total_scenarios = len(ranked)
    fail_count = sum(1 for item in ranked if item["verdict"] == "FAIL")
    worst = ranked[0]
    best = ranked[-1]
    dominant_asset = max(assets, key=lambda asset: asset["allocation_pct"])
    has_market_loss = worst.get("loss_pct", 0.0) > 0
    high_loss_asset: str | None = (
        worst.get("primary_culprit") or dominant_asset["name"]
    ) if has_market_loss else None

    status_label, status_text = _portfolio_status(fail_count, total_scenarios)
    cash_allocation = sum(a["allocation_pct"] for a in assets if is_cash(a["name"]))
    gold_allocation = sum(a["allocation_pct"] for a in assets if is_gold(a["name"]))
    crypto_allocation = sum(a["allocation_pct"] for a in assets if is_crypto(a["name"]))

    reasons = _reasons(fail_count, total_scenarios, worst, best, baseline_runway)
    strengths = _strengths(fail_count, total_scenarios, cash_allocation, gold_allocation, len(assets))
    vulnerabilities = _vulnerabilities(
        crypto_allocation=crypto_allocation,
        dominant_asset=dominant_asset,
        high_loss_asset=high_loss_asset,
        baseline_runway=baseline_runway,
    )

    recommendations = _recommendations(
        baseline_runway=baseline_runway,
        dominant_asset=dominant_asset,
        high_loss_asset=high_loss_asset,
    )

    return {
        "status_label": status_label,
        "status_text": status_text,
        "reasons": reasons,
        "strengths": strengths,
        "vulnerabilities": vulnerabilities,
        "recommendations": recommendations,
        "primary_issue": _primary_issue(baseline_runway, dominant_asset, high_loss_asset),
        "secondary_risk": _secondary_risk(baseline_runway, dominant_asset, high_loss_asset),
        "key_insight": _key_insight(baseline_runway, fail_count, total_scenarios),
        "action_priority": _action_priority(
            baseline_runway=baseline_runway,
            dominant_asset=dominant_asset,
            high_loss_asset=high_loss_asset,
        ),
        "fixability": (
            "This portfolio cannot pass the survival threshold through "
            "allocation changes alone."
            if baseline_runway < RUNWAY_THRESHOLD_MONTHS
            else "This can be improved through allocation adjustments."
        ),
    }


def _portfolio_status(fail_count: int, total_scenarios: int) -> tuple[str, str]:
    if fail_count == total_scenarios:
        return "NOT RESILIENT", "NOT resilient"
    if fail_count > total_scenarios / 2:
        return "FRAGILE", "fragile"
    if fail_count > 0:
        return "MODERATELY RESILIENT", "moderately resilient"
    return "RESILIENT", "resilient"


def _reasons(
    fail_count: int,
    total_scenarios: int,
    worst: dict,
    best: dict,
    baseline_runway: float,
) -> list[str]:
    if fail_count == total_scenarios:
        reasons = [
            f"All {total_scenarios} scenarios result in failure",
            "Runway remains below 12 months in every modeled case",
        ]
    elif fail_count == 0:
        reasons = [
            f"All {total_scenarios} scenarios pass the 12-month runway test",
            f"worst modeled runway is {worst['runway']:.1f} months",
        ]
    else:
        reasons = [
            f"{fail_count} of {total_scenarios} scenarios fail the 12-month runway test",
            f"modeled runway ranges from {worst['runway']:.1f} to {best['runway']:.1f} months",
        ]
    if baseline_runway < RUNWAY_THRESHOLD_MONTHS:
        reasons.append("baseline runway is already below 12 months before any market shock")
    return reasons


def _strengths(
    fail_count: int,
    total_scenarios: int,
    cash_allocation: float,
    gold_allocation: float,
    asset_count: int,
) -> list[str]:
    if fail_count >= total_scenarios:
        return []
    strengths: list[str] = []
    if cash_allocation >= 20:
        strengths.append("strong cash allocation")
    elif cash_allocation > 0:
        strengths.append("some cash allocation that cushions immediate drawdowns")
    if gold_allocation > 0:
        strengths.append("diversification into gold")
    if asset_count > 2:
        strengths.append("risk spread across multiple asset classes")
    return strengths


def _vulnerabilities(
    *,
    crypto_allocation: float,
    dominant_asset: dict,
    high_loss_asset: str | None,
    baseline_runway: float,
) -> list[str]:
    vulnerabilities: list[str] = []
    if crypto_allocation > 0:
        vulnerabilities.append(
            "crypto assets contribute to downside risk in stress scenarios"
        )
    if dominant_asset["allocation_pct"] > CONCENTRATION_ALERT_PCT:
        vulnerabilities.append(
            f"{dominant_asset['name']} concentration is high "
            f"({dominant_asset['allocation_pct']}% allocation)"
        )
    if high_loss_asset:
        vulnerabilities.append(f"{high_loss_asset} contributes the largest modeled loss")
    elif baseline_runway < RUNWAY_THRESHOLD_MONTHS:
        vulnerabilities.append("runway fails before market losses are applied")
    return vulnerabilities


def _recommendations(
    *,
    baseline_runway: float,
    dominant_asset: dict,
    high_loss_asset: str | None,
) -> list[str]:
    if baseline_runway < RUNWAY_THRESHOLD_MONTHS:
        recommendations = ["increase total portfolio value", "reduce monthly expenses"]
        if dominant_asset["allocation_pct"] > CONCENTRATION_ALERT_PCT:
            recommendations.append(
                f"after fixing runway, reduce dominant asset: {dominant_asset['name']}"
            )
        if high_loss_asset and high_loss_asset != dominant_asset["name"]:
            recommendations.append(
                f"after fixing runway, reduce high-loss asset: {high_loss_asset}"
            )
        recommendations.append(
            "treat allocation optimization as secondary after runway is fixed"
        )
        return recommendations

    recommendations: list[str] = []
    if dominant_asset["allocation_pct"] > CONCENTRATION_ALERT_PCT:
        recommendations.append(f"reduce dominant asset: {dominant_asset['name']}")
    if high_loss_asset and high_loss_asset != dominant_asset["name"]:
        recommendation = f"reduce allocation of high-loss asset: {high_loss_asset}"
        if recommendation not in recommendations:
            recommendations.append(recommendation)
    recommendations.append("increase defensive allocation if scenario failures persist")
    return recommendations


def _primary_issue(
    baseline_runway: float,
    dominant_asset: dict,
    high_loss_asset: str | None,
) -> str:
    if baseline_runway < RUNWAY_THRESHOLD_MONTHS:
        return "Insufficient capital relative to expenses"
    if dominant_asset["allocation_pct"] > CONCENTRATION_ALERT_PCT:
        return f"Concentration in {dominant_asset['name']}"
    if not high_loss_asset:
        return "No single asset dominates modeled losses"
    return f"{high_loss_asset} dominates downside risk"


def _secondary_risk(
    baseline_runway: float,
    dominant_asset: dict,
    high_loss_asset: str | None,
) -> str:
    if baseline_runway < RUNWAY_THRESHOLD_MONTHS:
        if dominant_asset["allocation_pct"] > CONCENTRATION_ALERT_PCT:
            return f"Concentration in {dominant_asset['name']}"
        return "Allocation changes cannot solve structural runway shortfall"
    if not high_loss_asset:
        return "No single loss driver identified"
    if high_loss_asset != dominant_asset["name"]:
        return f"{high_loss_asset} is the largest modeled loss contributor"
    return "Limited defensive buffer against severe stress"


def _key_insight(
    baseline_runway: float,
    fail_count: int,
    total_scenarios: int,
) -> str:
    if baseline_runway < RUNWAY_THRESHOLD_MONTHS:
        return (
            "Even without market shocks, the portfolio fails survival thresholds. "
            "This is a structural capital-versus-expenses problem."
        )
    if fail_count == total_scenarios:
        return (
            "Every modeled stress case fails. The portfolio needs a larger "
            "defensive base before risk allocation becomes the main lever."
        )
    if fail_count > total_scenarios / 2:
        return (
            "Most modeled shocks fail. The portfolio is fragile under market "
            "stress even though baseline runway is adequate."
        )
    if fail_count > 0:
        return (
            "The portfolio survives common shocks but remains exposed to severe "
            "tail-risk scenarios."
        )
    return "The portfolio passes all modeled shocks with current assumptions."


def _action_priority(
    *,
    baseline_runway: float,
    dominant_asset: dict,
    high_loss_asset: str | None,
) -> list[str]:
    if baseline_runway < RUNWAY_THRESHOLD_MONTHS:
        return [
            "Reduce monthly expenses",
            "Increase capital",
            "Then consider allocation optimization",
        ]

    actions: list[str] = []
    if dominant_asset["allocation_pct"] > CONCENTRATION_ALERT_PCT:
        actions.append(f"Reduce {dominant_asset['name']} concentration")
    if high_loss_asset:
        action = f"Reduce {high_loss_asset} downside exposure"
        if action not in actions:
            actions.append(action)
    actions.append("Increase defensive assets if failures remain")
    return actions
