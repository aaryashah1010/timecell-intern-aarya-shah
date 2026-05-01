# Task 1 - Portfolio Risk Engine

A terminal-first simulator that stress-tests a portfolio against an extreme
market crash. It answers three concrete questions:

1. What is my portfolio worth after a crash?
2. How many months of expenses would the surviving capital cover?
3. Where is my risk concentrated?

This file documents Task 1 only. The system-wide vision is in
[Timecell_README_TOP1.md](Timecell_README_TOP1.md).

---

## Spec-compatible entry point

The core module exposes the exact function requested in the assessment:

```python
from core.risk_calculator import compute_risk_metrics

result = compute_risk_metrics(portfolio)
```

It accepts the Task 01 portfolio dictionary:

```python
portfolio = {
    "total_value_inr": 10_000_000,
    "monthly_expenses_inr": 80_000,
    "assets": [
        {"name": "BTC", "allocation_pct": 30, "expected_crash_pct": -80},
        {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
        {"name": "GOLD", "allocation_pct": 20, "expected_crash_pct": -15},
        {"name": "CASH", "allocation_pct": 10, "expected_crash_pct": 0},
    ],
}
```

It returns the five required keys:

- `post_crash_value`
- `runway_months`
- `ruin_test`
- `largest_risk_asset`
- `concentration_warning`

---

## CLI mode

The CLI is designed for a non-expert user. It asks for total portfolio value,
monthly expenses, and asset allocation percentages. Crash assumptions are not
asked from the user; they are looked up from `config/crash_assumptions.py`.

If allocations sum to less than 100%, the remainder is treated as
`Cash @ 0% crash` so the portfolio always reconciles to 100%.

Run it:

```bash
python task1_risk.py             # severe crash scenario
python task1_risk.py --moderate  # bonus: 50% of severe crash assumptions
```

Sample interaction:

```text
Total portfolio value (INR) : 10,00,000
Monthly expenses (INR)      : 50000

Known asset classes (case-insensitive lookup):
  -75.0%   eth, ethereum
  -70.0%   btc, bitcoin, crypto
  -40.0%   nifty, sensex, stocks, equity
  ...

Asset name [100.00% remaining] : BTC
  Allocation % for BTC (max 100.00) : 40
Asset name [ 60.00% remaining] : NIFTY
  Allocation % for NIFTY (max 60.00) : 30
Asset name [ 30.00% remaining] : Gold
  Allocation % for Gold (max 30.00) : 20
Asset name [ 10.00% remaining] :

  (unallocated 10.00% -> treated as Cash @ 0% crash)
```

---

## Formulas implemented

| Quantity               | Formula                                |
| ---------------------- | -------------------------------------- |
| Asset value            | `total_value * allocation_pct / 100`   |
| Post-crash asset value | `value * (1 + crash_pct / 100)`        |
| Portfolio post-crash   | `sum(post_crash_asset_values)`         |
| Runway months          | `post_crash_value / monthly_expenses`  |
| Ruin test              | `PASS` if `runway > 12`, else `FAIL`   |
| Asset risk score       | `allocation_pct * abs(crash_pct)`      |
| Concentration warning  | any `allocation_pct > 40`              |

---

## Project layout

```text
Timecell/
|-- core/
|   |-- __init__.py
|   |-- risk_calculator.py     # pure math + spec-compatible function
|   `-- visualizer.py          # ASCII report rendering
|-- config/
|   |-- __init__.py
|   `-- crash_assumptions.py   # predefined crash percentages + lookup
|-- tests/
|   `-- test_risk_calculator.py
|-- task1_risk.py              # interactive CLI for Task 1
|-- task2_market.py            # interactive CLI for Task 2
|-- main.py                    # future combined pipeline entry point
|-- requirements.txt
|-- README_TASK1.md
`-- Timecell_README_TOP1.md
```

The split is deliberate:

- `core/risk_calculator.py` is deterministic and has no input, printing,
  logging, or file I/O.
- `core/visualizer.py` is the only layer that knows about terminal formatting.
- `task1_risk.py` handles CLI prompts and user-facing validation.

---

## Edge cases handled

| Edge case                         | Handling                                      |
| --------------------------------- | --------------------------------------------- |
| Zero allocation                   | CLI skips it; pure math also handles it.      |
| 100% cash portfolio               | No loss, no largest risk asset.               |
| No monthly expenses               | CLI rejects it; core returns infinite runway. |
| Allocations below 100%            | Remainder becomes cash.                       |
| Allocations above 100%            | CLI prevents the entry.                       |
| Unknown asset name                | Falls back to `-30%` with a notice.           |
| Runway exactly 12 months          | Fails because the spec says `> 12`.           |
| Allocation exactly 40%            | No warning because threshold is `> 40`.       |
| Invalid spec dictionary inputs    | `compute_risk_metrics()` raises `ValueError`. |

---

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

The tests include the exact portfolio example from the PDF, required return
keys, strict boundary behavior, moderate-crash behavior, invalid input checks,
and arithmetic invariants.

---

## AI usage

Claude was used as a pair-programming assistant for architecture suggestions,
edge-case enumeration, crash-assumption brainstorming, INR formatting, and test
scaffolding. I reviewed the implementation and kept control over the public
`RiskReport` shape, the final crash assumptions, and the UX decision to treat
unallocated remainder as cash.
