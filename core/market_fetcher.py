"""Fetch live market quotes from yfinance and CoinGecko with graceful fallback."""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

log = logging.getLogger("market")

DEFAULT_RETRIES: int = 3
DEFAULT_BACKOFF_SEC: float = 1.5
HTTP_TIMEOUT_SEC: float = 10.0
COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"
IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class AssetSpec:
    name: str       # display name, e.g. "NIFTY50"
    source: str     # "yfinance" or "coingecko"
    symbol: str     # yfinance ticker or CoinGecko coin id
    currency: str   # display currency, e.g. "INR", "USD"


@dataclass(frozen=True)
class Quote:
    name: str
    price: float | None
    currency: str
    source: str
    fetched_at: datetime
    error: str | None = None
    warning: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.price is not None


def fetch_yfinance_price(symbol: str) -> float:
    try:
        import yfinance as yf  # local import: only paid when actually needed

        ticker = yf.Ticker(symbol)
        history = ticker.history(period="1d")
    except Exception as exc:
        raise RuntimeError(f"Yahoo Finance request failed for {symbol}: {exc}") from exc

    if history.empty:
        raise RuntimeError(f"Yahoo Finance returned no price data for {symbol}")

    price = float(history["Close"].iloc[-1])
    if price <= 0:
        raise RuntimeError(f"Yahoo Finance returned non-positive price {price} for {symbol}")
    return price


def fetch_coingecko_price(coin_id: str, vs_currency: str = "usd") -> float:
    import requests

    url = f"{COINGECKO_BASE_URL}/simple/price"
    params = {"ids": coin_id, "vs_currencies": vs_currency}

    try:
        response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_SEC)
    except requests.RequestException as exc:
        raise RuntimeError(f"CoinGecko network error for {coin_id}: {exc}") from exc

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        suffix = f"; retry after {retry_after}s" if retry_after else ""
        raise RuntimeError(f"CoinGecko rate limit hit for {coin_id}{suffix}")

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"CoinGecko HTTP {response.status_code} for {coin_id}: {response.text[:120]}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"CoinGecko returned invalid JSON for {coin_id}") from exc

    if coin_id not in payload or vs_currency not in payload[coin_id]:
        raise RuntimeError(f"CoinGecko response missing {coin_id}/{vs_currency}")
    return float(payload[coin_id][vs_currency])


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
                delay = backoff * (2 ** (attempt - 1))
                jitter = random.uniform(0.0, min(backoff, delay * 0.25))
                time.sleep(delay + jitter)

    assert last_exc is not None
    raise last_exc


def _cache_key(spec: AssetSpec) -> str:
    return f"{spec.source}:{spec.symbol}:{spec.currency.lower()}"


def load_cache(cache_path: Path) -> dict[str, dict[str, object]]:
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("market cache could not be read from %s: %s", cache_path, exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def save_cache(cache_path: Path, cache: dict[str, dict[str, object]]) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
    except OSError as exc:
        log.warning("market cache could not be written to %s: %s", cache_path, exc)


def _cache_quote(spec: AssetSpec, quote: Quote) -> dict[str, object]:
    return {
        "name": spec.name,
        "price": quote.price,
        "currency": spec.currency,
        "source": spec.source,
        "fetched_at": quote.fetched_at.isoformat(),
    }


def _quote_from_cache(spec: AssetSpec, cached: dict[str, object], error: str) -> Quote | None:
    try:
        price = float(cached["price"])
        fetched_at = datetime.fromisoformat(str(cached["fetched_at"]))
    except (KeyError, TypeError, ValueError):
        return None

    return Quote(
        name=spec.name,
        price=price,
        currency=spec.currency,
        source="cache",
        fetched_at=fetched_at,
        warning=f"live fetch failed; using cached {spec.source} price ({error})",
    )


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
                attempts=attempts,
                backoff=backoff,
                label=label,
            )
        elif spec.source == "coingecko":
            price = _with_retries(
                lambda: fetch_coingecko_price(spec.symbol, spec.currency.lower()),
                attempts=attempts,
                backoff=backoff,
                label=label,
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
    cache_path: Path | None = None,
) -> list[Quote]:
    cache = load_cache(cache_path) if cache_path is not None else {}
    quotes: list[Quote] = []
    cache_changed = False

    for spec in specs:
        quote = fetch_quote(spec, attempts=attempts, backoff=backoff)
        key = _cache_key(spec)

        if quote.ok:
            if cache_path is not None:
                cache[key] = _cache_quote(spec, quote)
                cache_changed = True
            quotes.append(quote)
            continue

        cached = cache.get(key)
        cached_quote = (
            _quote_from_cache(spec, cached, quote.error or "unknown error")
            if isinstance(cached, dict)
            else None
        )
        if cached_quote is not None:
            log.warning("using cached quote for %s after live fetch failed", spec.name)
            quotes.append(cached_quote)
        else:
            quotes.append(quote)

    if cache_path is not None and cache_changed:
        save_cache(cache_path, cache)

    return quotes


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
        return left + mid.join("-" * w for w in widths) + right

    def render_row(cells: list[str]) -> str:
        return "|" + "|".join(f" {c}".ljust(w) for c, w in zip(cells, widths)) + "|"

    timestamp = quotes[0].fetched_at.strftime("%Y-%m-%d %H:%M:%S %Z")
    out: list[str] = [
        f"Asset Prices - fetched at {timestamp}",
        "",
        hline("+", "+", "+"),
        render_row(headers),
        hline("+", "+", "+"),
        *(render_row(r) for r in rows),
        hline("+", "+", "+"),
    ]

    warnings = [q for q in quotes if q.warning]
    if warnings:
        out.append("")
        out.append(f"Warnings ({len(warnings)} cached):")
        for q in warnings:
            out.append(f"  - {q.name}: {q.warning}")

    failed = [q for q in quotes if not q.ok]
    if failed:
        out.append("")
        out.append(f"Errors ({len(failed)} of {len(quotes)} failed):")
        for q in failed:
            out.append(f"  - {q.name} via {q.source}: {q.error}")

    return "\n".join(out)
