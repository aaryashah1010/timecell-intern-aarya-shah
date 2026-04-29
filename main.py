"""Future combined Timecell pipeline entry point.

Task-specific CLIs are intentionally kept separate:
    python task1_risk.py
    python task2_market.py

The combined pipeline will be wired here after Task 3 is implemented.
"""

from __future__ import annotations


def main() -> int:
    print("Timecell combined pipeline is not wired yet.")
    print("Run Task 1: python task1_risk.py")
    print("Run Task 2: python task2_market.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
