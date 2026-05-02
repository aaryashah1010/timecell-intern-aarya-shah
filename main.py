"""Combined pipeline entry point."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable


TaskMain = Callable[[], int]


def main() -> int:
    parser = argparse.ArgumentParser(description="Combined CLI")
    task_group = parser.add_mutually_exclusive_group()
    task_group.add_argument(
        "--task1",
        action="store_true",
        help="run Task 1 portfolio risk calculator",
    )
    task_group.add_argument(
        "--task2",
        action="store_true",
        help="run Task 2 live market data fetcher",
    )
    task_group.add_argument(
        "--task3",
        action="store_true",
        help="run Task 3 AI portfolio explainer",
    )
    task_group.add_argument(
        "--task4",
        action="store_true",
        help="run Task 4 crash scenario story generator",
    )
    task_group.add_argument(
        "--crash-story",
        action="store_true",
        help="alias for --task4",
    )
    args, task_args = parser.parse_known_args()

    if args.task1:
        from task1_risk import main as task_main

        return _run_task_with_args("task1_risk.py", task_main, task_args)

    if args.task2:
        from task2_market import main as task_main

        return _run_task_with_args("task2_market.py", task_main, task_args)

    if args.task3:
        from task3_advisor import main as task_main

        return _run_task_with_args("task3_advisor.py", task_main, task_args)

    if args.task4 or args.crash_story:
        from task4_crash_story import main as task4_main

        return task4_main(task_args)

    if task_args:
        parser.error(
            "task-specific arguments require one of "
            "--task1, --task2, --task3, --task4, or --crash-story"
        )

    return _run_interactive_menu()


def _run_task_with_args(script_name: str, task_main: TaskMain, args: list[str]) -> int:
    """Run a task whose parser reads from sys.argv, then restore sys.argv."""
    original_argv = sys.argv[:]
    try:
        sys.argv = [script_name, *args]
        return task_main()
    finally:
        sys.argv = original_argv


def _run_interactive_menu() -> int:
    """Show a numbered task menu and run the selected task."""
    print()
    print("Choose a task to run")
    print("--------------------")
    print("  1. Task 1 - Portfolio Risk Calculator")
    print("  2. Task 2 - Live Market Data Fetch")
    print("  3. Task 3 - AI Portfolio Explainer")
    print("  4. Task 4 - Crash Scenario Story Generator")
    print("  0. Exit")
    print()

    try:
        choice = input("Enter choice (1-4, or 0 to exit): ").strip().lower()
    except EOFError:
        print("No task selected.")
        return 0

    if choice in {"0", "q", "quit", "exit", ""}:
        print("No task selected.")
        return 0

    if choice == "1":
        from task1_risk import main as task_main

        return _run_task_with_args("task1_risk.py", task_main, [])

    if choice == "2":
        from task2_market import main as task_main

        return _run_task_with_args("task2_market.py", task_main, [])

    if choice == "3":
        from task3_advisor import main as task_main

        return _run_task_with_args("task3_advisor.py", task_main, [])

    if choice == "4":
        from task4_crash_story import main as task4_main

        return task4_main([])

    print(f"Invalid choice: {choice}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
