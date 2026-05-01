"""User-facing asset catalog mapped to provider-specific symbols."""

from __future__ import annotations

from core.market_fetcher import AssetSpec

MARKET_CATALOG: dict[str, list[AssetSpec]] = {
    "stocks": [
        AssetSpec(name="NIFTY50", source="yfinance", symbol="^NSEI", currency="INR"),
        AssetSpec(name="SENSEX", source="yfinance", symbol="^BSESN", currency="INR"),
        AssetSpec(name="BANKNIFTY", source="yfinance", symbol="^NSEBANK", currency="INR"),
        AssetSpec(name="RELIANCE", source="yfinance", symbol="RELIANCE.NS", currency="INR"),
        AssetSpec(name="TCS", source="yfinance", symbol="TCS.NS", currency="INR"),
        AssetSpec(name="INFOSYS", source="yfinance", symbol="INFY.NS", currency="INR"),
        AssetSpec(name="HDFC BANK", source="yfinance", symbol="HDFCBANK.NS", currency="INR"),
        AssetSpec(name="ICICI BANK", source="yfinance", symbol="ICICIBANK.NS", currency="INR"),
        AssetSpec(name="APPLE", source="yfinance", symbol="AAPL", currency="USD"),
        AssetSpec(name="MICROSOFT", source="yfinance", symbol="MSFT", currency="USD"),
    ],
    "crypto": [
        AssetSpec(name="BTC", source="coingecko", symbol="bitcoin", currency="USD"),
        AssetSpec(name="ETH", source="coingecko", symbol="ethereum", currency="USD"),
        AssetSpec(name="SOL", source="coingecko", symbol="solana", currency="USD"),
        AssetSpec(name="BNB", source="coingecko", symbol="binancecoin", currency="USD"),
        AssetSpec(name="XRP", source="coingecko", symbol="ripple", currency="USD"),
        AssetSpec(name="DOGE", source="coingecko", symbol="dogecoin", currency="USD"),
    ],
}


def default_assets() -> list[AssetSpec]:
    return [
        MARKET_CATALOG["stocks"][0],
        MARKET_CATALOG["stocks"][1],
        MARKET_CATALOG["stocks"][3],
        MARKET_CATALOG["crypto"][0],
        MARKET_CATALOG["crypto"][1],
    ]
