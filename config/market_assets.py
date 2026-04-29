"""Default asset specs for Task 2 — covers spec requirement (>=1 stock/index, >=1 crypto)."""

from core.market_fetcher import AssetSpec

DEFAULT_ASSETS: list[AssetSpec] = [
    AssetSpec(name="NIFTY50",  source="yfinance",  symbol="^NSEI",       currency="INR"),
    AssetSpec(name="SENSEX",   source="yfinance",  symbol="^BSESN",      currency="INR"),
    AssetSpec(name="RELIANCE", source="yfinance",  symbol="RELIANCE.NS", currency="INR"),
    AssetSpec(name="BTC",      source="coingecko", symbol="bitcoin",     currency="USD"),
    AssetSpec(name="ETH",      source="coingecko", symbol="ethereum",    currency="USD"),
]
