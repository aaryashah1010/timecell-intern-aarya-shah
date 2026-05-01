"""Tests for core/market_fetcher.py.

Network calls are mocked so the tests are deterministic and run offline.
A real-API smoke test belongs in a separate, manually-run script.
"""

from datetime import datetime
from pathlib import Path

import pytest

from core.market_fetcher import (
    AssetSpec,
    Quote,
    fetch_all,
    fetch_quote,
    fetch_coingecko_price,
    render_market_table,
)


# ---------- Quote dataclass ----------

def test_quote_ok_when_price_is_set_and_no_error():
    q = Quote(name="X", price=100.0, currency="USD", source="t", fetched_at=datetime.now())
    assert q.ok is True


def test_quote_not_ok_when_error_set():
    q = Quote(name="X", price=None, currency="USD", source="t",
              fetched_at=datetime.now(), error="boom")
    assert q.ok is False


# ---------- routing ----------

def test_fetch_quote_routes_yfinance(monkeypatch):
    captured: dict[str, str] = {}

    def fake_yf(symbol: str) -> float:
        captured["symbol"] = symbol
        return 22500.0

    monkeypatch.setattr("core.market_fetcher.fetch_yfinance_price", fake_yf)
    quote = fetch_quote(
        AssetSpec("NIFTY50", "yfinance", "^NSEI", "INR"),
        attempts=1, backoff=0.0,
    )
    assert quote.ok
    assert quote.price == 22500.0
    assert captured["symbol"] == "^NSEI"


def test_fetch_quote_routes_coingecko(monkeypatch):
    captured: dict[str, str] = {}

    def fake_cg(coin_id: str, vs_currency: str = "usd") -> float:
        captured["coin_id"] = coin_id
        captured["vs_currency"] = vs_currency
        return 60_000.0

    monkeypatch.setattr("core.market_fetcher.fetch_coingecko_price", fake_cg)
    quote = fetch_quote(
        AssetSpec("BTC", "coingecko", "bitcoin", "USD"),
        attempts=1, backoff=0.0,
    )
    assert quote.ok
    assert quote.price == 60_000.0
    assert captured == {"coin_id": "bitcoin", "vs_currency": "usd"}


def test_fetch_quote_unknown_source_returns_failed_quote():
    quote = fetch_quote(
        AssetSpec("X", "myspace", "X", "USD"),
        attempts=1, backoff=0.0,
    )
    assert not quote.ok
    assert "unknown source" in quote.error.lower()


# ---------- retry behavior ----------

def test_fetch_quote_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky(symbol: str) -> float:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return 42.0

    monkeypatch.setattr("core.market_fetcher.fetch_yfinance_price", flaky)
    quote = fetch_quote(
        AssetSpec("X", "yfinance", "X", "USD"),
        attempts=3, backoff=0.0,
    )
    assert quote.ok
    assert quote.price == 42.0
    assert calls["n"] == 3


def test_fetch_quote_returns_failed_quote_when_all_attempts_exhausted(monkeypatch):
    def boom(symbol: str) -> float:
        raise RuntimeError("network down")

    monkeypatch.setattr("core.market_fetcher.fetch_yfinance_price", boom)
    quote = fetch_quote(
        AssetSpec("X", "yfinance", "X", "USD"),
        attempts=2, backoff=0.0,
    )
    assert not quote.ok
    assert quote.price is None
    assert "network down" in quote.error


# ---------- fetch_all isolation ----------

def test_fetch_all_continues_after_individual_failure(monkeypatch):
    def maybe_fail(symbol: str) -> float:
        if symbol == "AAA":
            raise RuntimeError("first one is down")
        return 99.0

    monkeypatch.setattr("core.market_fetcher.fetch_yfinance_price", maybe_fail)
    quotes = fetch_all(
        [
            AssetSpec("A", "yfinance", "AAA", "USD"),
            AssetSpec("B", "yfinance", "BBB", "USD"),
        ],
        attempts=1, backoff=0.0,
    )
    assert len(quotes) == 2
    assert quotes[0].ok is False
    assert quotes[1].ok is True
    assert quotes[1].price == 99.0


def test_fetch_all_writes_successful_quotes_to_cache(monkeypatch):
    def fake_yf(symbol: str) -> float:
        return 123.45

    monkeypatch.setattr("core.market_fetcher.fetch_yfinance_price", fake_yf)
    cache_path = Path("data") / "test_market_cache_write.json"
    quotes = fetch_all(
        [AssetSpec("A", "yfinance", "AAA", "USD")],
        attempts=1,
        backoff=0.0,
        cache_path=cache_path,
    )

    assert quotes[0].ok is True
    assert cache_path.exists()
    assert "yfinance:AAA:usd" in cache_path.read_text(encoding="utf-8")


def test_fetch_all_uses_cache_when_live_fetch_fails(monkeypatch):
    def boom(symbol: str) -> float:
        raise RuntimeError("network down")

    monkeypatch.setattr("core.market_fetcher.fetch_yfinance_price", boom)
    cache_path = Path("data") / "test_market_cache_read.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        '{"yfinance:AAA:usd": {"name": "A", "price": 77.0, "currency": "USD", '
        '"source": "yfinance", "fetched_at": "2026-04-29T19:14:32+05:30"}}',
        encoding="utf-8",
    )

    quotes = fetch_all(
        [AssetSpec("A", "yfinance", "AAA", "USD")],
        attempts=1,
        backoff=0.0,
        cache_path=cache_path,
    )

    assert quotes[0].ok is True
    assert quotes[0].price == 77.0
    assert quotes[0].source == "cache"
    assert "using cached" in quotes[0].warning


def test_coingecko_rate_limit_error_is_clear(monkeypatch):
    class Response:
        status_code = 429
        headers = {"Retry-After": "60"}

    def fake_get(*args, **kwargs):
        return Response()

    monkeypatch.setattr("requests.get", fake_get)

    with pytest.raises(RuntimeError, match="rate limit hit.*retry after 60s"):
        fetch_coingecko_price("bitcoin", "usd")


# ---------- table rendering ----------

def test_render_market_table_includes_every_quote():
    now = datetime.now()
    table = render_market_table([
        Quote("BTC", 62_341.20, "USD", "coingecko", now),
        Quote("NIFTY50", 22_541.80, "INR", "yfinance", now),
    ])
    assert "BTC" in table
    assert "NIFTY50" in table
    assert "62,341.20" in table
    assert "22,541.80" in table
    assert "coingecko" in table
    assert "yfinance" in table


def test_render_market_table_marks_failed_rows_and_lists_errors():
    now = datetime.now()
    table = render_market_table([
        Quote("BTC", 62_341.20, "USD", "coingecko", now),
        Quote("BAD", None, "INR", "yfinance", now, error="API timeout"),
    ])
    assert "FAILED" in table
    assert "Errors (1 of 2 failed)" in table
    assert "API timeout" in table


def test_render_market_table_lists_cached_warnings():
    now = datetime.now()
    table = render_market_table([
        Quote("BTC", 62_341.20, "USD", "cache", now, warning="live fetch failed"),
    ])
    assert "cache" in table
    assert "Warnings (1 cached)" in table
    assert "live fetch failed" in table


def test_render_market_table_empty_input():
    assert "no quotes" in render_market_table([]).lower()
