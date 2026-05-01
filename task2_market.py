"""Task 2 entry point: Live Market Data Fetch.

Fetches current prices for the assets defined in config/market_assets.py
and prints them as a clean terminal table. Per-asset failures do not
abort the script; failed rows are listed separately under the table.

Run:
    python task2_market.py             # fetch and render once
    python task2_market.py --interactive
    python task2_market.py --verbose   # also echo log lines to stderr
    python task2_market.py --retries 5 # override retry attempts (default 3)
    python task2_market.py --no-cache  # disable stale-cache fallback
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from config.market_assets import DEFAULT_ASSETS
from config.market_catalog import MARKET_CATALOG
from core.market_fetcher import AssetSpec, fetch_all, render_market_table

log = logging.getLogger("task2")
DEFAULT_CACHE_PATH = Path("data") / "market_cache.json"


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
    p = argparse.ArgumentParser(description="Task 2 - Live Market Data Fetch")
    p.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="prompt for custom yfinance/CoinGecko assets instead of defaults",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="echo log lines to stderr")
    p.add_argument(
        "--retries", type=int, default=3,
        help="retry attempts per asset (default 3)",
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="disable fallback to the last successful cached price",
    )
    args = p.parse_args()
    if args.retries < 1:
        p.error("--retries must be at least 1")
    return args


def prompt_required(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  ! value cannot be blank")


def prompt_choice(prompt: str, allowed: set[str]) -> str:
    allowed_display = "/".join(sorted(allowed))
    while True:
        value = input(f"{prompt} ({allowed_display}) : ").strip().lower()
        if value in allowed:
            return value
        print(f"  ! choose one of: {allowed_display}")


def prompt_number(prompt: str, *, min_value: int, max_value: int) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("  ! enter a number")
            continue
        if min_value <= value <= max_value:
            return value
        print(f"  ! enter a number from {min_value} to {max_value}")


def prompt_yes_no(prompt: str, *, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        value = input(f"{prompt} {suffix} : ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("  ! enter y or n")


def catalog_options() -> list[AssetSpec]:
    options: list[AssetSpec] = []
    for group in ("stocks", "crypto"):
        options.extend(MARKET_CATALOG[group])
    return options


def print_catalog(options: list[AssetSpec]) -> None:
    print()
    print("Available assets")
    for i, asset in enumerate(options, start=1):
        label = "Stock/Index" if asset.source == "yfinance" else "Crypto"
        print(f"  {i:2d}. {asset.name.ljust(12)} {label.ljust(11)} {asset.currency}")
    print("   0. Done")


def collect_interactive_assets() -> list[AssetSpec]:
    print()
    print("Custom asset fetch mode")
    print("Select assets by number. Backend API symbols are mapped automatically.")

    options = catalog_options()
    assets: list[AssetSpec] = []
    while True:
        print_catalog(options)
        choice = prompt_number("Choose asset number : ", min_value=0, max_value=len(options))
        if choice == 0:
            break

        selected = options[choice - 1]
        if selected in assets:
            print(f"  ! {selected.name} already selected")
        else:
            assets.append(selected)
            print(f"  + added {selected.name}")

        if not prompt_yes_no("Add another asset?", default=False):
            break

    return assets


def quote_summary(quotes: list) -> tuple[int, int, int]:
    live = sum(1 for q in quotes if q.ok and q.source != "cache")
    cached = sum(1 for q in quotes if q.ok and q.source == "cache")
    failed = sum(1 for q in quotes if not q.ok)
    return live, cached, failed


def render_fetch_summary(quotes: list) -> str:
    live, cached, failed = quote_summary(quotes)
    lines = [f"Fetch complete: {live} live, {cached} cached, {failed} failed."]
    if cached:
        lines.append("Cached prices are fallback data from the last successful fetch.")
    if failed:
        lines.append("Some providers were unavailable. See errors above.")
    return "\n".join(lines)


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
    assets = collect_interactive_assets() if args.interactive else DEFAULT_ASSETS
    if not assets:
        print("No assets selected. Nothing to fetch.")
        return 1

    log.info("task2 start retries=%d assets=%d", args.retries, len(assets))

    cache_path = None if args.no_cache else DEFAULT_CACHE_PATH
    print()
    print("Fetching live prices...")
    print("This may take a few seconds because market data APIs can be slow.")
    if cache_path is not None:
        print("Cache fallback is enabled for provider failures.")
    else:
        print("Cache fallback is disabled; failed providers will show as FAILED.")
    print()

    quotes = fetch_all(assets, attempts=args.retries, cache_path=cache_path)
    print(render_market_table(quotes))
    print()
    print(render_fetch_summary(quotes))

    failed = sum(1 for q in quotes if not q.ok)
    log.info("task2 complete ok=%d failed=%d", len(quotes) - failed, failed)
    # exit non-zero only if every fetch failed (so CI can detect a complete outage)
    return 0 if failed < len(quotes) else 2


if __name__ == "__main__":
    sys.exit(main())
