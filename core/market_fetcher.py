"""Fetch live market quotes from yfinance (stocks/indexes) and CoinGecko (crypto).

Per-asset failures never raise to the caller — they are returned as a Quote with
`error` set, so the table can still render the surviving rows.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

log = logging.getLogger("timecell.market")

DEFAULT_RETRIES: int = 3
DEFAULT_BACKOFF_SEC: float = 1.5
HTTP_TIMEOUT_SEC: float = 10.0
COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"
IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class AssetSpec:
    name: str       # display name (e.g. "NIFTY50")
    source: str     # "yfinance" | "coingecko"
    symbol: str     # yfinance ticker (e.g. "^NSEI") or coingecko coin id (e.g. "bitcoin")
    currency: str   # display currency (e.g. "INR", "USD")


@dataclass(frozen=True)
class Quote:
    name: str
    price: float | None
    currency: str
    source: str
    fetched_at: datetime
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.price is not None


# ---------- low-level provider calls (each raises on failure) ----------

def fetch_yfinance_price(symbol: str) -> float:
    import yfinance as yf  # local import: only paid when actually needed
    ticker = yf.Ticker(symbol)
    history = ticker.history(period="1d")
    if history.empty:
        raise RuntimeError(f"yfinance returned empty history for {symbol!r}")
    price = float(history["Close"].iloc[-1])
    if price <= 0:
        raise RuntimeError(f"yfinance returned non-positive price {price} for {symbol!r}")
    return price


def fetch_coingecko_price(coin_id: str, vs_currency: str = "usd") -> float:
    import requests
    url = f"{COINGECKO_BASE_URL}/simple/price"
    params = {"ids": coin_id, "vs_currencies": vs_currency}
    response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_SEC)
    response.raise_for_status()
    payload = response.json()
    if coin_id not in payload or vs_currency not in payload[coin_id]:
        raise RuntimeError(f"coingecko response missing {coin_id}/{vs_currency}: {payload!r}")
    return float(payload[coin_id][vs_currency])


# ---------- retry wrapper ----------

def _with_retries(
    operation: Callable[[], float],
    *,
    attempts: int,
    backoff: float,
    label: str,
) -> float:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            last_exc = exc
            log.warning("attempt %d/%d failed for %s: %s", attempt, attempts, label, exc)
            if attempt < attempts:
                time.sleep(backoff * attempt)  # linear backoff: 1x, 2x, 3x
    assert last_exc is not None
    raise last_exc


# ---------- public fetch API ----------

def fetch_quote(
    spec: AssetSpec,
    *,
    attempts: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF_SEC,
) -> Quote:
    fetched_at = datetime.now(tz=IST)
    label = f"{spec.source}:{spec.symbol}"
    try:
        if spec.source == "yfinance":
            price = _with_retries(
                lambda: fetch_yfinance_price(spec.symbol),
                attempts=attempts, backoff=backoff, label=label,
            )
        elif spec.source == "coingecko":
            currency_lower = spec.currency.lower()
            price = _with_retries(
                lambda: fetch_coingecko_price(spec.symbol, currency_lower),
                attempts=attempts, backoff=backoff, label=label,
            )
        else:
            raise ValueError(f"unknown source {spec.source!r} for asset {spec.name!r}")
        log.info("fetched %s = %.4f %s (source=%s)", spec.name, price, spec.currency, spec.source)
        return Quote(
            name=spec.name,
            price=price,
            currency=spec.currency,
            source=spec.source,
            fetched_at=fetched_at,
        )
    except Exception as exc:
        log.error("FAILED to fetch %s from %s: %s", spec.name, spec.source, exc)
        return Quote(
            name=spec.name,
            price=None,
            currency=spec.currency,
            source=spec.source,
            fetched_at=fetched_at,
            error=str(exc),
        )


def fetch_all(
    specs: list[AssetSpec],
    *,
    attempts: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF_SEC,
) -> list[Quote]:
    return [fetch_quote(s, attempts=attempts, backoff=backoff) for s in specs]


# ---------- terminal rendering ----------

def render_market_table(quotes: list[Quote]) -> str:
    if not quotes:
        return "(no quotes to display)"

    headers = ["Asset", "Price", "Currency", "Source"]
    rows: list[list[str]] = []
    for q in quotes:
        price_cell = f"{q.price:,.2f}" if q.ok else "FAILED"
        rows.append([q.name, price_cell, q.currency, q.source])

    widths = [
        max(len(headers[i]), max((len(r[i]) for r in rows), default=0)) + 2
        for i in range(len(headers))
    ]

    def hline(left: str, mid: str, right: str) -> str:
        return left + mid.join("─" * w for w in widths) + right

    def render_row(cells: list[str]) -> str:
        return "│" + "│".join(f" {c}".ljust(w) for c, w in zip(cells, widths)) + "│"

    timestamp = quotes[0].fetched_at.strftime("%Y-%m-%d %H:%M:%S %Z")
    out: list[str] = [
        f"Asset Prices — fetched at {timestamp}",
        "",
        hline("┌", "┬", "┐"),
        render_row(headers),
        hline("├", "┼", "┤"),
        *(render_row(r) for r in rows),
        hline("└", "┴", "┘"),
    ]

    failed = [q for q in quotes if not q.ok]
    if failed:
        out.append("")
        out.append(f"Errors ({len(failed)} of {len(quotes)} failed):")
        for q in failed:
            out.append(f"  - {q.name} via {q.source}: {q.error}")

    return "\n".join(out)
