"""Task 4 - Crash Scenario Story Generator.

Architecture:
  AI -> scenario JSON (narrative + shock_map only)
  crash_engine.py -> all numeric computation using Task 1 risk engine
  breakpoint_detector.py -> binary search for crash tolerance
  decision_insight.py -> portfolio-level recommendations
  report_formatter.py -> terminal rendering

Run modes:
  python task4_crash_story.py
  python task4_crash_story.py --input
  python task4_crash_story.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from cli.portfolio_input import get_portfolio_from_user
from core import report_formatter as fmt
from core.breakpoint_detector import find_portfolio_breakpoint
from core.crash_engine import compute_scenario_result, compute_why_this_breaks
from core.decision_insight import build_decision_insight, compute_baseline_runway
from core.report_formatter import ScenarioRenderContext
from core.scenario_generator import (
    MAX_SCENARIO_COUNT,
    MIN_SCENARIO_COUNT,
    generate_scenarios,
    validate_scenarios,
)

log = logging.getLogger("crash_story")

DATA_DIR: Path = Path(__file__).parent / "data"
DEFAULT_PORTFOLIO_PATH: Path = DATA_DIR / "crash_story_default_portfolio.json"
DRY_RUN_SCENARIOS_PATH: Path = DATA_DIR / "crash_story_dry_run_scenarios.json"


def setup_logging(log_dir: Path, *, verbose: bool) -> None:
    """Configure file logging plus optional stderr logging."""
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


def _load_json(path: Path):
    if not path.exists():
        raise SystemExit(f"data file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}") from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Task 4 - Crash Scenario Story Generator"
    )
    parser.add_argument(
        "--input",
        action="store_true",
        help="Enter a custom portfolio interactively instead of using the default.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip AI API call. Use hardcoded scenarios to test math engine.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="echo logs to stderr"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the crash scenario story generator CLI."""
    _configure_stdout()
    args = parse_args(argv)
    setup_logging(Path("logs"), verbose=args.verbose)
    load_dotenv_if_present()

    if args.input:
        portfolio = get_portfolio_from_user()
        if not portfolio.get("assets"):
            print("\nNo assets entered. Nothing to analyze.")
            return 1
    else:
        portfolio = _load_json(DEFAULT_PORTFOLIO_PATH)

    baseline_runway = compute_baseline_runway(portfolio)

    fmt.print_header(portfolio)

    print("  Computing portfolio break point...")
    breakpoint_result = find_portfolio_breakpoint(portfolio)
    fmt.print_breakpoint(breakpoint_result)
    fmt.print_critical_insight(baseline_runway)

    if args.dry_run:
        print("  [DRY RUN] Skipping AI call. Using hardcoded scenarios.\n")
        scenarios = validate_scenarios(_load_json(DRY_RUN_SCENARIOS_PATH))
    else:
        print("  Calling AI to generate portfolio-specific scenarios...")
        print("  (this takes 5-10 seconds)\n")
        try:
            scenarios = generate_scenarios(portfolio)
        except (EnvironmentError, ValueError) as exc:
            log.error("scenario generation failed: %s", exc)
            print(f"\n[ERROR] {exc}")
            return 1

    if not MIN_SCENARIO_COUNT <= len(scenarios) <= MAX_SCENARIO_COUNT:
        print(
            "[ERROR] Scenario validation failed: "
            f"expected {MIN_SCENARIO_COUNT}-{MAX_SCENARIO_COUNT} valid scenarios, "
            f"got {len(scenarios)}."
        )
        return 1

    ranking_data: list[dict] = []

    for index, scenario in enumerate(scenarios, 1):
        shock_map = scenario.get("shock_map", {})

        metrics = compute_scenario_result(portfolio, shock_map)
        metrics["pre_crash_value"] = portfolio["total_value_inr"]

        why = compute_why_this_breaks(portfolio, shock_map, metrics)

        fmt.print_scenario(
            ScenarioRenderContext(
                scenario=scenario,
                metrics=metrics,
                why=why,
                index=index,
                total=len(scenarios),
                portfolio=portfolio,
                baseline_runway=baseline_runway,
            )
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
    log.info("crash_story complete scenarios=%d", len(scenarios))
    return 0


def _configure_stdout() -> None:
    """Use UTF-8 output when the host Python exposes stdout reconfiguration."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
