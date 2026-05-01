"""Combined Timecell pipeline entry point."""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Timecell combined CLI")
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="run Task 4 portfolio strategy improvement simulator",
    )
    args = parser.parse_args()

    if args.optimize:
        from task4_optimizer import main as task4_main

        return task4_main([])

    print("Run Task 1: python task1_risk.py")
    print("Run Task 2: python task2_market.py")
    print("Run Task 3: python task3_advisor.py")
    print("Run Task 4: python task4_optimizer.py")
    print("Or run Task 4 through this entry point: python main.py --optimize")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
