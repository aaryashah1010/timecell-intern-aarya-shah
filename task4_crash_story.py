"""Task 4 - Crash Scenario Story Generator.

Architecture:
  ChatGPT -> scenario JSON (narrative + shock_map only)
  crash_engine.py -> all numeric computation using Task 1 risk engine
  breakpoint_detector.py -> binary search for crash tolerance
  report_formatter.py -> terminal rendering

Run modes:
  python task4_crash_story.py
  python task4_crash_story.py --input
  python task4_crash_story.py --dry-run
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from core import report_formatter as fmt
from core.breakpoint_detector import find_portfolio_breakpoint
from core.crash_engine import compute_scenario_result, compute_why_this_breaks
from core.scenario_generator import (
    MAX_SCENARIO_COUNT,
    MIN_SCENARIO_COUNT,
    generate_scenarios,
    validate_scenarios,
)

load_dotenv()

RUNWAY_THRESHOLD_MONTHS: float = 12.0
CONCENTRATION_ALERT_PCT: float = 35.0

DEFAULT_PORTFOLIO: dict = {
    "total_value_inr": 10_000_000,
    "monthly_expenses_inr": 80_000,
    "assets": [
        {"name": "BTC", "allocation_pct": 30, "expected_crash_pct": -80},
        {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
        {"name": "GOLD", "allocation_pct": 20, "expected_crash_pct": -15},
        {"name": "CASH", "allocation_pct": 10, "expected_crash_pct": 0},
    ],
}

DRY_RUN_SCENARIOS: list[dict] = [
    {
        "scenario_id": 1,
        "name": "Crypto Regulatory Crackdown - US SEC + EU Simultaneous Action",
        "narrative": (
            "The US SEC classifies Bitcoin as an unregistered security following "
            "a landmark court ruling. EU regulators act within 48 hours, freezing "
            "withdrawals on major exchanges. Retail panic follows institutional "
            "exit over two weeks."
        ),
        "shock_map": {"BTC": -71, "NIFTY50": -12, "GOLD": 8, "CASH": 0},
        "severity": "HIGH",
        "severity_reason": (
            "Crypto concentration means this scenario alone can breach runway threshold."
        ),
        "likelihood": "MEDIUM",
        "likelihood_reason": (
            "Regulatory action is probable but timing and severity remain uncertain."
        ),
        "takeaway": (
            "Your crypto exposure alone can break this portfolio without any equity "
            "market moving against you."
        ),
    },
    {
        "scenario_id": 2,
        "name": "RBI Emergency Rate Hike - 150bps Rupee Stabilisation",
        "narrative": (
            "The rupee breaches 95 per dollar amid a widening current account "
            "deficit and FII outflows. RBI raises rates by 150bps in an emergency "
            "inter-meeting decision. Indian equities sell off sharply as domestic "
            "liquidity tightens across sectors."
        ),
        "shock_map": {"BTC": -20, "NIFTY50": -35, "GOLD": 12, "CASH": 0},
        "severity": "MEDIUM",
        "severity_reason": (
            "Equity book absorbs most of the shock but gold partially offsets losses."
        ),
        "likelihood": "MEDIUM",
        "likelihood_reason": (
            "Rupee stress is plausible given persistent USD strength through 2025."
        ),
        "takeaway": (
            "A domestic rate shock would hurt your equity book but your gold position "
            "provides meaningful cushion."
        ),
    },
    {
        "scenario_id": 3,
        "name": "Sovereign Capital Lockdown - Bank Bail-In and Market Closure",
        "narrative": (
            "A cascading banking panic forces emergency capital controls and a "
            "temporary freeze across exchanges, brokers, and large bank deposits. "
            "Quoted prices gap lower, but the bigger shock is impaired access to "
            "liquidity during the crisis window. Investors mark portfolios to "
            "distressed executable value rather than normal market value."
        ),
        "shock_map": {"BTC": -85, "NIFTY50": -95, "GOLD": -90, "CASH": -100},
        "severity": "EXTREME",
        "severity_reason": (
            "Market closure and bank bail-in risk can impair even defensive liquidity."
        ),
        "likelihood": "LOW",
        "likelihood_reason": (
            "This requires simultaneous market, banking, and capital-control stress."
        ),
        "takeaway": (
            "Even a large cash buffer can fail if liquidity access breaks, so defensive "
            "assets should be spread across instruments and custodians."
        ),
    },
    {
        "scenario_id": 4,
        "name": "Rupee Freefall - Currency Crisis Triggered by Oil Shock",
        "narrative": (
            "A Middle East escalation drives Brent crude above $140. India's import "
            "bill explodes and the current account deficit hits 5% of GDP. The rupee "
            "falls 22% against the dollar in three months, triggering imported "
            "inflation and equity outflows."
        ),
        "shock_map": {"BTC": -15, "NIFTY50": -28, "GOLD": 22, "CASH": 0},
        "severity": "MEDIUM",
        "severity_reason": (
            "Gold's appreciation in USD terms partially offsets INR-denominated equity losses."
        ),
        "likelihood": "MEDIUM",
        "likelihood_reason": (
            "Oil shock risk is elevated given current geopolitical tensions in the Gulf."
        ),
        "takeaway": (
            "Your gold holding acts as a natural rupee hedge; this is its moment to protect you."
        ),
    },
    {
        "scenario_id": 5,
        "name": "Indian Election Shock - Surprise Hung Parliament",
        "narrative": (
            "General election results produce a hung parliament with no clear "
            "majority coalition. Policy uncertainty halts capex decisions across "
            "Indian corporates. FII outflows accelerate as political risk premium "
            "reprices across Indian assets."
        ),
        "shock_map": {"BTC": -8, "NIFTY50": -22, "GOLD": 6, "CASH": 0},
        "severity": "LOW",
        "severity_reason": (
            "India-specific shock with limited crypto impact; portfolio survives comfortably."
        ),
        "likelihood": "LOW",
        "likelihood_reason": (
            "A hung parliament outcome is possible but current polling suggests it is unlikely."
        ),
        "takeaway": (
            "Political risk is real but your diversification across crypto and gold limits the damage here."
        ),
    },
]


def main() -> None:
    """Run the crash scenario story generator CLI."""
    _configure_stdout()
    parser = argparse.ArgumentParser(
        description="Timecell Task 4 - Crash Scenario Story Generator"
    )
    parser.add_argument(
        "--input",
        action="store_true",
        help="Enter a custom portfolio interactively instead of using the default.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip ChatGPT API call. Use hardcoded scenarios to test math engine.",
    )
    args = parser.parse_args()

    if args.input:
        from cli.portfolio_input import get_portfolio_from_user

        portfolio = get_portfolio_from_user()
    else:
        portfolio = DEFAULT_PORTFOLIO

    baseline_runway = compute_baseline_runway(portfolio)

    fmt.print_header(portfolio)

    print("  Computing portfolio break point...")
    breakpoint_result = find_portfolio_breakpoint(portfolio)
    fmt.print_breakpoint(breakpoint_result)
    fmt.print_critical_insight(baseline_runway)

    if args.dry_run:
        print("  [DRY RUN] Skipping ChatGPT call. Using hardcoded scenarios.\n")
        scenarios = validate_scenarios(DRY_RUN_SCENARIOS)
    else:
        print("  Calling ChatGPT to generate portfolio-specific scenarios...")
        print("  (this takes 5-10 seconds)\n")
        try:
            scenarios = generate_scenarios(portfolio)
        except EnvironmentError as exc:
            print(f"\n[ERROR] {exc}")
            sys.exit(1)
        except ValueError as exc:
            print(f"\n[ERROR] {exc}")
            sys.exit(1)

    if not MIN_SCENARIO_COUNT <= len(scenarios) <= MAX_SCENARIO_COUNT:
        print(
            "[ERROR] Scenario validation failed: "
            f"expected {MIN_SCENARIO_COUNT}-{MAX_SCENARIO_COUNT} valid scenarios, "
            f"got {len(scenarios)}."
        )
        sys.exit(1)

    ranking_data: list[dict] = []

    for index, scenario in enumerate(scenarios, 1):
        shock_map = scenario.get("shock_map", {})

        metrics = compute_scenario_result(portfolio, shock_map)
        metrics["pre_crash_value"] = portfolio["total_value_inr"]

        why = compute_why_this_breaks(portfolio, shock_map, metrics)

        fmt.print_scenario(
            scenario,
            metrics,
            why,
            index,
            len(scenarios),
            portfolio=portfolio,
            baseline_runway=baseline_runway,
        )

        ranking_data.append(
            {
                "name": scenario["name"],
                "runway": metrics["runway_months"],
                "verdict": metrics["ruin_test"],
                "primary_culprit": why["largest_loss_asset"],
                "loss_pct": why["total_loss_pct"],
            }
        )

    ranked = sorted(
        ranking_data,
        key=lambda item: (
            0 if item["verdict"] == "FAIL" else 1,
            item["runway"],
            -item["loss_pct"],
        ),
    )
    fmt.print_ranking(ranked)
    insight = build_decision_insight(portfolio, ranked, baseline_runway)
    fmt.print_decision_insight(insight)
    fmt.print_fixability(insight)
    fmt.print_final_decision_summary(insight, ranked)


def _configure_stdout() -> None:
    """Use UTF-8 output when the host Python exposes stdout reconfiguration."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def compute_baseline_runway(portfolio: dict) -> float:
    """Return runway before market stress."""
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
    pass_count = total_scenarios - fail_count
    worst = ranked[0]
    best = ranked[-1]
    dominant_asset = max(assets, key=lambda asset: asset["allocation_pct"])
    has_market_loss = worst.get("loss_pct", 0.0) > 0
    high_loss_asset = (
        (worst.get("primary_culprit") or dominant_asset["name"])
        if has_market_loss
        else ""
    )

    status_label, status_text = _portfolio_status(fail_count, total_scenarios)
    cash_allocation = sum(
        asset["allocation_pct"]
        for asset in assets
        if asset["name"].lower().strip() in {"cash", "fd", "savings", "fixed deposit"}
    )
    gold_allocation = sum(
        asset["allocation_pct"]
        for asset in assets
        if "gold" in asset["name"].lower()
    )
    crypto_allocation = sum(
        asset["allocation_pct"]
        for asset in assets
        if any(
            token in asset["name"].lower()
            for token in ("btc", "bitcoin", "eth", "crypto", "doge")
        )
    )

    reasons = [
        f"{fail_count} of {total_scenarios} scenarios fail the 12-month runway test",
        (
            f"modeled runway ranges from {worst['runway']:.1f} to "
            f"{best['runway']:.1f} months"
        ),
    ]
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
    if baseline_runway < RUNWAY_THRESHOLD_MONTHS:
        reasons.append(
            "baseline runway is already below 12 months before any market shock"
        )

    strengths: list[str] = []
    if fail_count < total_scenarios and cash_allocation >= 20:
        strengths.append("strong cash allocation")
    elif fail_count < total_scenarios and cash_allocation > 0:
        strengths.append("some cash allocation that cushions immediate drawdowns")
    if fail_count < total_scenarios and gold_allocation > 0:
        strengths.append("diversification into gold")
    if fail_count < total_scenarios and len(assets) > 2:
        strengths.append("risk spread across multiple asset classes")

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

    recommendations = _recommendations(
        baseline_runway=baseline_runway,
        dominant_asset=dominant_asset,
        high_loss_asset=high_loss_asset,
    )
    primary_issue = _primary_issue(baseline_runway, dominant_asset, high_loss_asset)
    secondary_risk = _secondary_risk(baseline_runway, dominant_asset, high_loss_asset)
    key_insight = _key_insight(baseline_runway, fail_count, total_scenarios)
    action_priority = _action_priority(
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
        "primary_issue": primary_issue,
        "secondary_risk": secondary_risk,
        "key_insight": key_insight,
        "action_priority": action_priority,
        "fixability": (
            "This portfolio cannot pass the survival threshold through "
            "allocation changes alone."
            if baseline_runway < RUNWAY_THRESHOLD_MONTHS
            else "This can be improved through allocation adjustments."
        ),
    }


def _portfolio_status(fail_count: int, total_scenarios: int) -> tuple[str, str]:
    """Return machine and readable portfolio status labels."""
    if fail_count == total_scenarios:
        return "NOT RESILIENT", "NOT resilient"
    if fail_count > total_scenarios / 2:
        return "FRAGILE", "fragile"
    if fail_count > 0:
        return "MODERATELY RESILIENT", "moderately resilient"
    return "RESILIENT", "resilient"


def _recommendations(
    *,
    baseline_runway: float,
    dominant_asset: dict,
    high_loss_asset: str,
) -> list[str]:
    """Generate recommendations from structural runway and asset drivers."""
    recommendations: list[str] = []
    if baseline_runway < RUNWAY_THRESHOLD_MONTHS:
        recommendations.extend([
            "increase total portfolio value",
            "reduce monthly expenses",
        ])
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
    high_loss_asset: str,
) -> str:
    """Return the primary decision issue."""
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
    high_loss_asset: str,
) -> str:
    """Return the secondary decision risk."""
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
    """Return the final decision-system insight."""
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
    high_loss_asset: str,
) -> list[str]:
    """Return ordered next actions."""
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


if __name__ == "__main__":
    main()
