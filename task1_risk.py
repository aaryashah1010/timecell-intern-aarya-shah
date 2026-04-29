"""Timecell - Task 1 entry point: Portfolio Risk Engine (CLI).

Inputs collected from the user:
    - total portfolio value (INR)
    - monthly expenses (INR)
    - per-asset allocation % (one or more assets)

`expected_crash_pct` is NOT asked from the user - it is domain knowledge
that lives in config/crash_assumptions.py.

Run:
    python task1_risk.py             # severe crash scenario
    python task1_risk.py --moderate  # 50% of severe
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from config.crash_assumptions import (
    FALLBACK_CRASH_PCT,
    grouped_for_display,
    is_known_asset,
    lookup_crash_pct,
)
from core.risk_calculator import Asset, build_report
from core.visualizer import render_report

log = logging.getLogger("timecell.task1")


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


def prompt_float(
    prompt: str,
    *,
    allow_zero: bool = True,
    max_value: float | None = None,
) -> float:
    while True:
        raw = input(prompt).strip().replace(",", "").replace("_", "")
        if not raw:
            print("  ! please enter a number")
            continue
        try:
            value = float(raw)
        except ValueError:
            print("  ! not a valid number")
            continue
        if value < 0:
            print("  ! cannot be negative")
            continue
        if value == 0 and not allow_zero:
            print("  ! cannot be zero")
            continue
        if max_value is not None and value > max_value + 1e-9:
            print(f"  ! cannot exceed {max_value:.2f}")
            continue
        return value


def show_known_assets() -> None:
    print()
    print("Known asset classes (case-insensitive lookup):")
    for crash, names in grouped_for_display():
        print(f"  {crash:+6.1f}%   {', '.join(names)}")
    print(f"  (unknown asset names default to {FALLBACK_CRASH_PCT:+.1f}%)")
    print()


def collect_assets() -> list[Asset]:
    show_known_assets()
    print("Enter your assets one by one. Leave the name blank to finish.")

    assets: list[Asset] = []
    remaining = 100.0
    while remaining > 1e-9:
        name = input(f"Asset name [{remaining:6.2f}% remaining] : ").strip()
        if not name:
            break
        if not is_known_asset(name):
            print(
                f"  (unknown asset '{name}' -- using fallback "
                f"crash assumption {FALLBACK_CRASH_PCT:+.1f}%)"
            )
        crash = lookup_crash_pct(name)
        alloc = prompt_float(
            f"  Allocation % for {name} (max {remaining:.2f}) : ",
            allow_zero=True,
            max_value=remaining,
        )
        if alloc == 0:
            print("  (zero allocation -- skipping this asset)")
            continue
        assets.append(Asset(name=name, allocation_pct=alloc, expected_crash_pct=crash))
        remaining -= alloc
        log.info("added asset %s alloc=%.2f%% crash=%+.1f%%", name, alloc, crash)

    if remaining > 0.01:
        print(f"\n  (unallocated {remaining:.2f}% -> treated as Cash @ 0% crash)")
        assets.append(Asset(name="Cash", allocation_pct=remaining, expected_crash_pct=0.0))
    return assets


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Timecell Task 1 - Portfolio Risk Engine"
    )
    p.add_argument(
        "--moderate",
        action="store_true",
        help="apply moderate crash (50%% of severe)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging(Path("logs"))
    log.info("task1 start moderate=%s", args.moderate)

    print("=" * 64)
    print(" TIMECELL  -  Portfolio Risk Engine ".center(64, "="))
    print("=" * 64)

    total = prompt_float("\nTotal portfolio value (INR) : ", allow_zero=False)
    monthly = prompt_float("Monthly expenses (INR)      : ", allow_zero=False)
    assets = collect_assets()

    if not assets:
        print("\nNo assets entered. Nothing to evaluate.")
        return 1

    report = build_report(total, monthly, assets, moderate=args.moderate)
    print(render_report(report))

    log.info("task1 complete assets=%d", len(assets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
