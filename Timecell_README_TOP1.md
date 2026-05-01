# Timecell AI Internship - Advanced README

## Product Vision

This project is a terminal-first AI-powered wealth intelligence system inspired
by modern fintech products.

Core flow:

```text
User Portfolio -> Market Data -> Risk Engine -> AI Advisor
```

The system is designed to answer:

- What happens to my portfolio in a crash?
- Can I survive financially?
- What should I improve?
- Can the system explain the result like a human advisor?

---

## System Architecture

```text
User Input
    |
    v
Market Data Layer      (Task 2)
    |
    v
Risk Engine            (Task 1)
    |
    v
AI Advisor             (Task 3)
```

---

## Tech Stack

- Python 3.10+
- yfinance for stocks and indexes
- CoinGecko API for crypto
- requests
- logging
- python-dotenv
- OpenAI, Gemini, or Claude for the LLM layer

---

## Project Structure

```text
project/
|-- core/
|   |-- risk_calculator.py
|   |-- market_fetcher.py
|   `-- ai_explainer.py
|-- config/
|-- logs/
|-- data/
|-- task1_risk.py
|-- task2_market.py
|-- main.py
`-- README.md
```

---

## Task 1 - Risk Engine

### Objective

Simulate portfolio behavior under extreme market crashes.

### Inputs

- `total_value_inr`
- `monthly_expenses_inr`
- `assets`
  - `name`
  - `allocation_pct`
  - `expected_crash_pct`

### Core Formulas

```text
asset_value = total_value * allocation_pct / 100
value_after_crash = asset_value * (1 + crash_pct / 100)
post_crash_value = sum(value_after_crash for all assets)
runway_months = post_crash_value / monthly_expenses
ruin_test = PASS if runway_months > 12 else FAIL
risk_score = allocation_pct * abs(crash_pct)
concentration_warning = True if any allocation_pct > 40
```

### Bonus

- Moderate crash scenario: `crash_pct * 0.5`
- CLI visualization using ASCII bars

---

## Task 2 - Market Data Layer

### Objective

Fetch real-time asset prices.

### APIs

- yfinance for stocks and indexes
- CoinGecko for crypto

### Features

- Fetch at least 3 assets
- Include at least one stock/index and one crypto asset
- Retry logic
- Graceful failure handling
- Logging
- Clean terminal table

Example output:

```text
Asset Prices - fetched at timestamp

BTC     62,341.20 USD
NIFTY   22,541.80 INR
GOLD     7,312.00 INR/g
```

---

## Task 3 - AI Advisor

### Objective

Transform raw financial metrics into human-understandable insights.

The AI should behave like a friendly but honest financial advisor for a
non-expert client.

### Required Output

1. Risk summary in 3-4 sentences
2. One positive observation
3. One actionable improvement
4. Verdict: `Aggressive`, `Balanced`, or `Conservative`

### Critical Requirements

- Print the raw LLM response
- Print structured parsed output separately

### Bonus

- Tone control: beginner, experienced, expert
- Second LLM call that critiques the first explanation for accuracy

---

## Combined Pipeline

### Objective

Simulate a real-world investment flow.

```text
1. User selects assets
2. User enters quantities
3. Fetch prices
4. Compute values
5. Calculate total investment
6. Ask budget confirmation
7. Ask monthly expenses
8. Apply crash assumptions
9. Run risk engine
10. Pass output to AI advisor
```

Core equation:

```text
value = quantity * price
allocation = value / total * 100
```

---

## Engineering Principles

- Separation of concerns
- API resilience with retries and logging
- Deterministic risk calculations
- LLM output structuring
- CLI-first design

---

## Demo Checklist

The final 3-5 minute walkthrough should include:

- Code walkthrough
- Task explanation
- CLI demo
- AI explanation output

---

## Final Summary

```text
Task 1 -> Quantitative Risk Engine
Task 2 -> Real-time Data Layer
Task 3 -> AI Explanation Layer
Combined -> Full AI Fintech System
```

## Why This Stands Out

- Not just coding: system thinking
- Not just AI: controlled AI output
- Not just data: meaningful insights
