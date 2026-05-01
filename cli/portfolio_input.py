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

log = logging.getLogger("portfolio_input")

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


def get_portfolio_from_user() -> dict:
    """
    Interactive CLI to build a custom portfolio from user input.
    Does not rely on crash_assumptions.py — shock percentages for
    Task 4 will be provided entirely by AI at scenario generation time.
    Returns a portfolio dict in the same shape as the default portfolio.
    """
    print("\n  ── PORTFOLIO SETUP ──────────────────────────────────")

    try:
        total_str = input("  Total portfolio value (INR): ₹").replace(",", "").strip()
        total = float(total_str)
    except ValueError:
        print("  [ERROR] Invalid amount. Using default ₹1,00,00,000")
        total = 10_000_000

    try:
        expenses_str = input("  Monthly expenses (INR): ₹").replace(",", "").strip()
        expenses = float(expenses_str)
    except ValueError:
        print("  [ERROR] Invalid amount. Using default ₹80,000")
        expenses = 80_000

    assets: list[dict] = []
    total_alloc = 0.0

    print("\n  Enter your assets one by one.")
    print("  Examples: BTC, ETH, NIFTY50, GOLD, CASH, Reliance, Apple")
    print("  Type 'done' when finished.\n")

    while True:
        name = input("  Asset name (or 'done'): ").strip()
        if name.lower() == "done":
            if not assets:
                print("  [ERROR] You must enter at least one asset.")
                continue
            break
        if not name:
            continue

        remaining = 100.0 - total_alloc
        while True:
            try:
                pct = float(input(f"  Allocation % for {name}: ").strip())
            except ValueError:
                print("  [ERROR] Invalid percentage. Try again.")
                continue

            if pct < 0:
                print("  [ERROR] Allocation cannot be negative. Please re-enter.")
                continue
            if pct > remaining + 1e-9:
                print("[ERROR] Total allocation exceeds 100%. Please re-enter.")
                print(f"  Remaining allocation available: {remaining:.1f}%")
                continue
            break

        if pct == 0:
            print(f"  {name} skipped (0%).\n")
            continue

        total_alloc += pct

        # expected_crash_pct is a placeholder only.
        # Task 4 will override this entirely with AI scenario values.
        assets.append({
            "name": name,
            "allocation_pct": pct,
            "expected_crash_pct": -30.0,
        })

        print(f"  ✓ {name} added ({pct}%)")
        print("    Note: crash % will be set by AI per scenario\n")

        if abs(total_alloc - 100.0) <= 1e-9:
            print("  Total allocation reached 100%.\n")
            break

    remaining = 100.0 - total_alloc
    if remaining > 0.01:
        print(f"\n  Unallocated {remaining:.1f}% assigned to Cash.")
        assets.append({
            "name": "Cash",
            "allocation_pct": remaining,
            "expected_crash_pct": 0.0,
        })
        total_alloc = 100.0

    if abs(total_alloc - 100.0) > 0.5:
        print(f"\n  [WARNING] Allocations sum to {total_alloc:.1f}%, not 100%.")
        print("  Results will still compute but ratios may be off.\n")
    else:
        print(f"\n  ✓ Total allocation: {total_alloc:.1f}%\n")

    return {
        "total_value_inr": total,
        "monthly_expenses_inr": expenses,
        "assets": assets,
    }
