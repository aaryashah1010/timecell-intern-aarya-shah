# Task 2 - Live Market Data Fetch

A terminal-first market data fetcher that retrieves live prices from free public
APIs and renders a clean CLI table.

It satisfies the assessment requirement to fetch at least three assets, including
at least one stock/index and at least one crypto asset.

---

## Run

Fetch the default asset set:

```bash
python task2_market.py
```

Choose assets from a user-friendly catalog:

```bash
python task2_market.py --interactive
```

Show logs in the terminal as well as `logs/app.log`:

```bash
python task2_market.py --verbose
```

Change retry attempts:

```bash
python task2_market.py --retries 5
```

Disable cache fallback:

```bash
python task2_market.py --no-cache
```

---

## Default Assets

The default run fetches:

| Asset    | Type        | Provider  | Backend symbol |
| -------- | ----------- | --------- | -------------- |
| NIFTY50  | Stock/index | yfinance  | `^NSEI`        |
| SENSEX   | Stock/index | yfinance  | `^BSESN`       |
| RELIANCE | Stock       | yfinance  | `RELIANCE.NS`  |
| BTC      | Crypto      | CoinGecko | `bitcoin`      |
| ETH      | Crypto      | CoinGecko | `ethereum`     |

---

## Interactive Mode

Interactive mode displays user-facing asset names and maps them to backend API
symbols automatically.

Example menu:

```text
Available assets
   1. NIFTY50      Stock/Index INR
   2. SENSEX       Stock/Index INR
   3. BANKNIFTY    Stock/Index INR
   4. RELIANCE     Stock/Index INR
   ...
  11. BTC          Crypto      USD
  12. ETH          Crypto      USD
   0. Done
```

The mapping lives in:

```text
config/market_catalog.py
```

The fetcher core never asks for user input. It receives clean `AssetSpec`
objects such as:

```python
AssetSpec(name="NIFTY50", source="yfinance", symbol="^NSEI", currency="INR")
AssetSpec(name="BTC", source="coingecko", symbol="bitcoin", currency="USD")
```

---

## Output

The CLI prints a loading message first:

```text
Fetching live prices...
This may take a few seconds because market data APIs can be slow.
Cache fallback is enabled for provider failures.
```

Then it prints a table:

```text
Asset Prices - fetched at 2026-04-29 19:42:08 IST

+----------+-----------+----------+-----------+
| Asset    | Price     | Currency | Source    |
+----------+-----------+----------+-----------+
| NIFTY50  | 24,177.65 | INR      | yfinance  |
| BTC      | 76,565.00 | USD      | coingecko |
+----------+-----------+----------+-----------+
```

Finally it prints a summary:

```text
Fetch complete: 2 live, 0 cached, 0 failed.
```

---

## Resilience

Task 2 includes:

- Retry logic per asset
- Jittered exponential backoff
- Clear provider-specific errors
- CoinGecko rate-limit handling for HTTP `429`
- Per-asset failure isolation
- Optional cache fallback
- File logging

If one API fails, the script continues with the other assets.

---

## Cache Fallback

Live successful prices are cached in:

```text
data/market_cache.json
```

If a later live fetch fails, the fetcher can use the last successful cached
price. Cached rows are marked clearly:

```text
| BTC | 76,565.00 | USD | cache |
```

Warnings are printed below the table:

```text
Warnings (1 cached):
  - BTC: live fetch failed; using cached coingecko price (...)
```

Disable this behavior with:

```bash
python task2_market.py --no-cache
```

---

## Logging

Logs are written to:

```text
logs/app.log
```

Logged events include:

- Task start and completion
- Successful provider fetches
- Retry attempts
- Provider failures
- Cache fallback warnings

Use `--verbose` to also print logs to the terminal:

```bash
python task2_market.py --verbose
```

---

## Code Layout

```text
task2_market.py              # CLI args, prompts, loading/summary messages
core/market_fetcher.py       # fetch logic, retries, cache, rendering
config/market_catalog.py     # user-facing catalog to backend symbol mapping
config/market_assets.py      # default asset selection
tests/test_market_fetcher.py # fetcher tests with mocked network calls
tests/test_task2_market_cli.py
```

This keeps user interaction separate from provider/API logic.

---

## Tests

Run:

```bash
pytest -q
```

The tests mock network calls so they run offline and deterministically.
