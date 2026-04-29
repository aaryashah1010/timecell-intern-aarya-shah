"""Predefined severe-crash assumptions per asset class (historical extreme drawdowns)."""

from __future__ import annotations

DEFAULT_CRASH_ASSUMPTIONS_PCT: dict[str, float] = {
    "btc":          -70.0,
    "bitcoin":      -70.0,
    "eth":          -75.0,
    "ethereum":     -75.0,
    "crypto":       -70.0,
    "nifty":        -40.0,
    "sensex":       -40.0,
    "stocks":       -40.0,
    "equity":       -40.0,
    "mutual fund":  -35.0,
    "mutual funds": -35.0,
    "etf":          -35.0,
    "real estate":  -25.0,
    "reit":         -25.0,
    "silver":       -25.0,
    "gold":         -15.0,
    "bonds":        -10.0,
    "fd":             0.0,
    "cash":           0.0,
    "savings":        0.0,
}

FALLBACK_CRASH_PCT: float = -30.0  # used when an unknown asset name is entered


def lookup_crash_pct(name: str) -> float:
    return DEFAULT_CRASH_ASSUMPTIONS_PCT.get(name.strip().lower(), FALLBACK_CRASH_PCT)


def is_known_asset(name: str) -> bool:
    return name.strip().lower() in DEFAULT_CRASH_ASSUMPTIONS_PCT


def grouped_for_display() -> list[tuple[float, list[str]]]:
    """Group asset names by crash assumption for the CLI help table."""
    by_crash: dict[float, list[str]] = {}
    for name, crash in DEFAULT_CRASH_ASSUMPTIONS_PCT.items():
        by_crash.setdefault(crash, []).append(name)
    return sorted(by_crash.items(), key=lambda kv: kv[0])
