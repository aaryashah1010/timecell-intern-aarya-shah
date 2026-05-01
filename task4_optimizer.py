"""Timecell - Task 4 entry point: Portfolio Strategy Improvement Simulator."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from math import isfinite
from pathlib import Path

from cli.portfolio_input import collect_portfolio_dict
from core.ai_explainer import DEFAULT_MODEL
from core.portfolio_optimizer import (
    STRATEGIES,
    compare_portfolios,
    detect_strategy,
    generate_ai_verdict,
    generate_impact_summary,
    suggest_portfolio,
)
from core.risk_calculator import compute_risk_metrics

log = logging.getLogger("timecell.task4")

WIDTH: int = 64


def setup_logging(log_dir: Path, *, verbose: bool) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    ]
    handlers[0].setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    if verbose:
        stderr = logging.StreamHandler(sys.stderr)
        stderr.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
        handlers.append(stderr)
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


def load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def load_portfolio_from_file(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"portfolio file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"portfolio file {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or not data.get("assets"):
        raise SystemExit(f"{path}: expected a portfolio object with assets")
    return data


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Timecell Task 4 - Portfolio Strategy Improvement Simulator"
    )
    parser.add_argument(
        "--portfolio",
        type=Path,
        default=None,
        help="optional path to portfolio JSON; omitted means interactive input",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model for optional AI verdict (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        help="skip the AI prompt and request the optional AI final verdict",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="echo logs to stderr")
    return parser.parse_args(argv)


def ask_yes_no(prompt: str) -> bool:
    while True:
        raw = input(prompt).strip().casefold()
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("  ! please enter yes or no")


def ask_target_strategy() -> str:
    print()
    print("Choose target strategy:")
    for idx, strategy in enumerate(STRATEGIES, start=1):
        print(f"{idx}. {strategy}")

    while True:
        raw = input("Selection: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(STRATEGIES):
            return STRATEGIES[int(raw) - 1]
        for strategy in STRATEGIES:
            if raw.casefold() == strategy.casefold():
                return strategy
        print("  ! choose 1, 2, 3, or type the strategy name")


def render_strategy_summary(strategy: str, portfolio: dict, metrics: dict) -> str:
    return "\n".join(
        [
            "",
            "=" * WIDTH,
            " CURRENT STRATEGY ".center(WIDTH, "="),
            "=" * WIDTH,
            f"Detected strategy     : {strategy}",
            f"Post-crash value      : INR {_format_money(metrics['post_crash_value'])}",
            f"Loss percentage       : {_loss_pct(portfolio, metrics):.1f}%",
            f"Runway months         : {_format_runway(metrics['runway_months'])}",
            f"Ruin test             : {metrics['ruin_test']}",
            f"Largest risk asset    : {metrics['largest_risk_asset'] or 'None'}",
            f"Concentration warning : {_yes_no(metrics['concentration_warning'])}",
        ]
    )


def render_comparison(comparison: dict, target_strategy: str) -> str:
    current = comparison["current_metrics"]
    suggested = comparison["suggested_metrics"]
    lines = [
        "",
        "=" * WIDTH,
        " PORTFOLIO COMPARISON ".center(WIDTH, "="),
        "=" * WIDTH,
        f"{'Metric':<24}{'Current':<20}{target_strategy:<20}",
        "-" * (WIDTH - 1),
        f"{'Post-crash value':<24}INR {_format_money(current['post_crash_value']):<16}"
        f"INR {_format_money(suggested['post_crash_value'])}",
        f"{'Loss %':<24}{current['loss_pct']:<20.1f}{suggested['loss_pct']:.1f}",
        f"{'Runway months':<24}{_format_runway(current['runway_months']):<20}"
        f"{_format_runway(suggested['runway_months'])}",
        f"{'Ruin Test':<24}{current['ruin_test']:<20}{suggested['ruin_test']}",
        f"{'Largest Risk Asset':<24}{(current['largest_risk_asset'] or 'None'):<20}"
        f"{suggested['largest_risk_asset'] or 'None'}",
        f"{'Concentration':<24}{_yes_no(current['concentration_warning']):<20}"
        f"{_yes_no(suggested['concentration_warning'])}",
        "",
        "ALLOCATION CHANGE:",
    ]
    changes = comparison["allocation_changes"]
    if not changes:
        lines.append("No allocation changes needed under the selected strategy.")
    else:
        for change in changes:
            lines.append(
                f"{change['name']:<12}"
                f"{change['current_allocation_pct']:>6.1f}% -> "
                f"{change['suggested_allocation_pct']:>6.1f}%"
            )
    return "\n".join(lines)


def render_impact_summary(impact: dict) -> str:
    loss = impact["loss_pct"]
    runway = impact["runway_months"]
    concentration = impact["concentration_warning"]
    ruin = impact["ruin_test"]
    return "\n".join(
        [
            "",
            "=" * WIDTH,
            " IMPACT SUMMARY ".center(WIDTH, "="),
            "=" * WIDTH,
            f"Loss reduced       : {loss['current']:.1f}% -> "
            f"{loss['suggested']:.1f}%  ({loss['label']})",
            f"Runway improved    : {_format_runway(runway['current'])} -> "
            f"{_format_runway(runway['suggested'])} months  ({runway['label']})",
            f"Concentration      : {_yes_no(concentration['current'])} -> "
            f"{_yes_no(concentration['suggested'])}  ({concentration['label']})",
            f"Ruin Test          : {ruin['current']} -> {ruin['suggested']}  "
            f"({ruin['label']})",
            "",
            f"Result: {impact['result']}",
        ]
    )


def render_next_action(suggested_metrics: dict) -> str:
    if suggested_metrics["ruin_test"] == "PASS":
        return ""
    return "\n".join(
        [
            "",
            "NEXT ACTION",
            "Even after optimization, runway is below 12 months.",
            "Consider increasing defensive allocation, reducing monthly expenses, "
            "or increasing capital.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(Path("logs"), verbose=args.verbose)
    load_dotenv_if_present()

    if args.portfolio:
        portfolio = load_portfolio_from_file(args.portfolio)
    else:
        portfolio = collect_portfolio_dict(
            banner="TIMECELL  -  Strategy Improvement Simulator"
        )

    if not portfolio["assets"]:
        print("\nNo assets entered. Nothing to optimize.")
        return 1

    try:
        current_metrics = compute_risk_metrics(portfolio)
        current_strategy = detect_strategy(portfolio, current_metrics)
    except ValueError as exc:
        print(f"Portfolio error: {exc}", file=sys.stderr)
        return 1

    print(render_strategy_summary(current_strategy, portfolio, current_metrics))

    if not ask_yes_no("\nDo you want to generate a better strategy? yes/no: "):
        print("\nNo alternate strategy generated.")
        return 0

    target_strategy = ask_target_strategy()
    log.info("target strategy selected=%s", target_strategy)
    suggested = suggest_portfolio(portfolio, target_strategy)
    comparison = compare_portfolios(portfolio, suggested)
    impact = generate_impact_summary(
        comparison["current_metrics"], comparison["suggested_metrics"]
    )
    print(render_comparison(comparison, target_strategy))
    print(render_impact_summary(impact))
    next_action = render_next_action(comparison["suggested_metrics"])
    if next_action:
        print(next_action)

    should_call_ai = args.ai or ask_yes_no("\nDo you want an AI final verdict? yes/no: ")
    if should_call_ai:
        try:
            print()
            print("Sending comparison to the AI advisor...")
            print("Kindly wait for the final verdict. This can take a few seconds.")
            verdict = generate_ai_verdict(
                current_strategy=current_strategy,
                target_strategy=target_strategy,
                comparison=comparison,
                impact=impact,
                model=args.model,
            )
        except (RuntimeError, ValueError) as exc:
            log.error("ai verdict failed: %s", exc)
            print(
                "\nAI verdict unavailable right now. "
                "The rule-based comparison above is still valid."
            )
            return 0

        print()
        print("=" * WIDTH)
        print(" AI FINAL VERDICT ".center(WIDTH, "="))
        print("=" * WIDTH)
        print(verdict)

    log.info(
        "task4 complete current_strategy=%s target_strategy=%s ai=%s",
        current_strategy,
        target_strategy,
        should_call_ai,
    )
    return 0


def _format_money(value: float) -> str:
    return f"{value:,.0f}"


def _format_runway(value: float) -> str:
    return f"{value:.1f}" if isfinite(value) else "infinite"


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _loss_pct(portfolio: dict, metrics: dict) -> float:
    total = float(portfolio["total_value_inr"])
    if total <= 0:
        return 0.0
    return (1.0 - float(metrics["post_crash_value"]) / total) * 100.0


if __name__ == "__main__":
    raise SystemExit(main())
