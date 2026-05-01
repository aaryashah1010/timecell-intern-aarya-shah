"""Tests for Task 2 CLI prompt helpers."""

import sys
from datetime import datetime

from core.market_fetcher import AssetSpec, Quote
from task2_market import (
    catalog_options,
    collect_interactive_assets,
    parse_args,
    prompt_choice,
    prompt_number,
    quote_summary,
    render_fetch_summary,
)


def test_parse_args_accepts_interactive(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["task2_market.py", "--interactive"])
    args = parse_args()
    assert args.interactive is True


def test_prompt_choice_rejects_invalid_then_accepts(monkeypatch, capsys):
    values = iter(["bad", "crypto"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    result = prompt_choice("Asset type", {"stock", "crypto"})

    assert result == "crypto"
    assert "choose one of" in capsys.readouterr().out


def test_prompt_number_rejects_invalid_then_accepts(monkeypatch, capsys):
    values = iter(["x", "99", "2"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    result = prompt_number("Choose asset number : ", min_value=0, max_value=5)

    assert result == 2
    out = capsys.readouterr().out
    assert "enter a number" in out
    assert "from 0 to 5" in out


def test_catalog_options_contains_user_facing_assets():
    options = catalog_options()
    assert AssetSpec("NIFTY50", "yfinance", "^NSEI", "INR") in options
    assert AssetSpec("BTC", "coingecko", "bitcoin", "USD") in options


def test_collect_interactive_assets_builds_stock_spec_from_catalog(monkeypatch):
    values = iter(["1", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    assets = collect_interactive_assets()

    assert assets == [
        AssetSpec(
            name="NIFTY50",
            source="yfinance",
            symbol="^NSEI",
            currency="INR",
        )
    ]


def test_collect_interactive_assets_builds_crypto_spec_from_catalog(monkeypatch):
    values = iter(["11", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    assets = collect_interactive_assets()

    assert assets == [
        AssetSpec(
            name="BTC",
            source="coingecko",
            symbol="bitcoin",
            currency="USD",
        )
    ]


def test_collect_interactive_assets_can_add_multiple_assets(monkeypatch):
    values = iter(["1", "y", "11", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    assets = collect_interactive_assets()

    assert len(assets) == 2
    assert assets[0].source == "yfinance"
    assert assets[1].source == "coingecko"


def test_collect_interactive_assets_skips_duplicate(monkeypatch, capsys):
    values = iter(["1", "y", "1", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    assets = collect_interactive_assets()

    assert len(assets) == 1
    assert "already selected" in capsys.readouterr().out


def test_collect_interactive_assets_can_finish_without_assets(monkeypatch):
    values = iter(["0"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    assert collect_interactive_assets() == []


def test_quote_summary_counts_live_cached_and_failed():
    now = datetime.now()
    quotes = [
        Quote("BTC", 10.0, "USD", "coingecko", now),
        Quote("ETH", 20.0, "USD", "cache", now, warning="cached"),
        Quote("BAD", None, "USD", "coingecko", now, error="down"),
    ]

    assert quote_summary(quotes) == (1, 1, 1)


def test_render_fetch_summary_adds_cache_and_failure_guidance():
    now = datetime.now()
    quotes = [
        Quote("ETH", 20.0, "USD", "cache", now, warning="cached"),
        Quote("BAD", None, "USD", "coingecko", now, error="down"),
    ]

    summary = render_fetch_summary(quotes)

    assert "0 live, 1 cached, 1 failed" in summary
    assert "fallback data" in summary
    assert "providers were unavailable" in summary
