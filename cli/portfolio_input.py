"""Interactive portfolio collection — shared by every task CLI.

Returns the canonical Task 01 portfolio dict shape:

    {
        "total_value_inr":      float,
        "monthly_expenses_inr": float,
        "assets": [
            {"name": str, "allocation_pct": float, "expected_crash_pct": float},
            ...
        ],
    }

Crash percentages are looked up from `config.crash_assumptions` so the
non-expert user is never asked for them.
"""

from __future__ import annotations

import logging

from config.crash_assumptions import (
    FALLBACK_CRASH_PCT,
    grouped_for_display,
    is_known_asset,
    lookup_crash_pct,
)

log = logging.getLogger("timecell.cli.portfolio_input")

BANNER_WIDTH: int = 64


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


def print_banner(title: str) -> None:
    print("=" * BANNER_WIDTH)
    print(f" {title} ".center(BANNER_WIDTH, "="))
    print("=" * BANNER_WIDTH)


def collect_portfolio_dict(*, banner: str | None = None) -> dict:
    """Collect a portfolio interactively. Returns the Task 01 dict shape."""
    if banner is not None:
        print_banner(banner)

    total = prompt_float("\nTotal portfolio value (INR) : ", allow_zero=False)
    monthly = prompt_float("Monthly expenses (INR)      : ", allow_zero=False)

    show_known_assets()
    print("Enter your assets one by one. Leave the name blank to finish.")

    assets: list[dict] = []
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
            max_value=remaining,
        )
        if alloc == 0:
            print("  (zero allocation -- skipping this asset)")
            continue
        assets.append(
            {
                "name": name,
                "allocation_pct": alloc,
                "expected_crash_pct": crash,
            }
        )
        remaining -= alloc
        log.info("added asset %s alloc=%.2f%% crash=%+.1f%%", name, alloc, crash)

    if remaining > 0.01:
        print(f"\n  (unallocated {remaining:.2f}% -> treated as Cash @ 0% crash)")
        assets.append(
            {
                "name": "Cash",
                "allocation_pct": remaining,
                "expected_crash_pct": 0.0,
            }
        )

    return {
        "total_value_inr": total,
        "monthly_expenses_inr": monthly,
        "assets": assets,
    }
