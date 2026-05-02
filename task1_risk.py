"""Task 1 entry point: Portfolio Risk Engine (CLI).

Inputs collected from the user:
    - total portfolio value (INR)
    - monthly expenses (INR)
    - per-asset allocation % (one or more assets)

`expected_crash_pct` is NOT asked from the user - it is domain knowledge
that lives in config/crash_assumptions.py.

Run:
    python task1_risk.py             # severe crash scenario
    python task1_risk.py --moderate  # 50% of severe
    python task1_risk.py --compare   # severe and moderate reports
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from cli.portfolio_input import collect_portfolio_dict
from core.risk_calculator import Asset, RiskReport, build_report
from core.visualizer import render_report

log = logging.getLogger("task1")


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if any(isinstance(h, logging.FileHandler) for h in root.handlers):
        root.setLevel(logging.INFO)
        return
    handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task 1 - Portfolio Risk Engine"
    )
    p.add_argument(
        "--moderate",
        action="store_true",
        help="apply moderate crash (50%% of severe)",
    )
    p.add_argument(
        "--compare",
        action="store_true",
        help="show severe and moderate reports using the normal report format",
    )
    args = p.parse_args()
    if args.compare and args.moderate:
        p.error("--compare already includes moderate; do not combine it with --moderate")
    return args


def main() -> int:
    args = parse_args()
    setup_logging(Path("logs"))
    log.info("task1 start moderate=%s compare=%s", args.moderate, args.compare)

    portfolio = collect_portfolio_dict(banner="Portfolio Risk Engine")
    if not portfolio["assets"]:
        print("\nNo assets entered. Nothing to evaluate.")
        return 1

    assets = [Asset(**a) for a in portfolio["assets"]]
    if args.compare:
        severe, moderate = build_comparison_report(
            total_value=portfolio["total_value_inr"],
            monthly_expenses=portfolio["monthly_expenses_inr"],
            assets=assets,
        )
        print(render_comparison(severe, moderate))
        log.info("task1 comparison complete assets=%d", len(assets))
        return 0

    report = build_report(
        total_value=portfolio["total_value_inr"],
        monthly_expenses=portfolio["monthly_expenses_inr"],
        assets=assets,
        moderate=args.moderate,
    )
    print(render_report(report))

    log.info("task1 complete assets=%d", len(assets))
    return 0


def build_comparison_report(
    *,
    total_value: float,
    monthly_expenses: float,
    assets: list[Asset],
) -> tuple[RiskReport, RiskReport]:
    """Build severe and moderate reports from the same portfolio input."""
    severe = build_report(
        total_value=total_value,
        monthly_expenses=monthly_expenses,
        assets=assets,
        moderate=False,
    )
    moderate = build_report(
        total_value=total_value,
        monthly_expenses=monthly_expenses,
        assets=assets,
        moderate=True,
    )
    return severe, moderate


def render_comparison(severe: RiskReport, moderate: RiskReport) -> str:
    """Render severe and moderate reports with the standard Task 1 formatter."""
    return f"{render_report(severe)}\n\n{render_report(moderate)}"


if __name__ == "__main__":
    sys.exit(main())
