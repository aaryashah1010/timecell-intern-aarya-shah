"""Single source of truth for asset-name classification.

All Task 4 modules use these helpers instead of inlining their own
substring checks. This guarantees that "BTC", "bitcoin", and "BTC-USD"
are treated as the same category everywhere.
"""

from __future__ import annotations

CASH_TOKENS: frozenset[str] = frozenset({"cash", "fd", "savings", "fixed deposit"})

CRYPTO_TOKENS: tuple[str, ...] = ("btc", "bitcoin", "eth", "ethereum", "doge", "crypto")

GOLD_TOKENS: tuple[str, ...] = ("gold",)

INDIAN_EQUITY_TOKENS: tuple[str, ...] = (
    "nifty", "sensex", "reliance", "zomato", "tata",
    "hdfc", "icici", "infosys", "tcs", "indian equity",
)

GLOBAL_TECH_TOKENS: tuple[str, ...] = (
    "tesla", "apple", "amazon", "microsoft", "nvidia",
    "meta", "google", "alphabet", "netflix",
)

DEFENSIVE_TOKENS: tuple[str, ...] = ("cash", "fd", "savings", "gold", "bond", "gilt")


def _norm(name: str) -> str:
    return name.lower().strip()


def is_cash(name: str) -> bool:
    """Return True for cash-like instruments (cash, FD, savings)."""
    return _norm(name) in CASH_TOKENS


def is_crypto(name: str) -> bool:
    """Return True for any cryptocurrency holding."""
    lowered = _norm(name)
    return any(token in lowered for token in CRYPTO_TOKENS)


def is_gold(name: str) -> bool:
    """Return True for any gold holding."""
    lowered = _norm(name)
    return any(token in lowered for token in GOLD_TOKENS)


def category(name: str) -> str | None:
    """Return a high-level correlation category for an asset, or None.

    Categories: 'crypto', 'Indian equities', 'global tech',
    'defensive assets'.
    """
    lowered = _norm(name)
    if any(token in lowered for token in CRYPTO_TOKENS):
        return "crypto"
    if any(token in lowered for token in INDIAN_EQUITY_TOKENS):
        return "Indian equities"
    if any(token in lowered for token in GLOBAL_TECH_TOKENS):
        return "global tech"
    if any(token in lowered for token in DEFENSIVE_TOKENS):
        return "defensive assets"
    return None
