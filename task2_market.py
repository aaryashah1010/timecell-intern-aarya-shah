"""Timecell - Task 2 entry point: Live Market Data Fetch.

Fetches current prices for the assets defined in config/market_assets.py
and prints them as a clean terminal table. Per-asset failures do not
abort the script; failed rows are listed separately under the table.

Run:
    python task2_market.py             # fetch and render once
    python task2_market.py --verbose   # also echo log lines to stderr
    python task2_market.py --retries 5 # override retry attempts (default 3)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from config.market_assets import DEFAULT_ASSETS
from core.market_fetcher import fetch_all, render_market_table

log = logging.getLogger("timecell.task2")


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Timecell Task 2 - Live Market Data Fetch")
    p.add_argument("--verbose", "-v", action="store_true", help="echo log lines to stderr")
    p.add_argument(
        "--retries", type=int, default=3,
        help="retry attempts per asset (default 3)",
    )
    args = p.parse_args()
    if args.retries < 1:
        p.error("--retries must be at least 1")
    return args


def _ensure_utf8_stdout() -> None:
    # Windows consoles default to cp1252 which can't render box-drawing chars.
    # reconfigure() is a no-op on already-UTF-8 streams.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass


def main() -> int:
    args = parse_args()
    _ensure_utf8_stdout()
    setup_logging(Path("logs"), verbose=args.verbose)
    log.info("task2 start retries=%d assets=%d", args.retries, len(DEFAULT_ASSETS))

    quotes = fetch_all(DEFAULT_ASSETS, attempts=args.retries)
    print(render_market_table(quotes))

    failed = sum(1 for q in quotes if not q.ok)
    log.info("task2 complete ok=%d failed=%d", len(quotes) - failed, failed)
    # exit non-zero only if every fetch failed (so CI can detect a complete outage)
    return 0 if failed < len(quotes) else 2


if __name__ == "__main__":
    sys.exit(main())
