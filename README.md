# Timecell Intern Technical Test 2025

Engineering Intern - AI & Fintech submission.

This system answers:

- What happens to my portfolio in a crash?
- Can I survive financially?
- What should I change?
- Explain it like a human advisor.

This repository implements all four tasks from the Timecell technical
assessment:

1. Portfolio Risk Calculator
2. Live Market Data Fetch
3. AI-Powered Portfolio Explainer
4. Crash Scenario Story Generator

The project is built as a terminal-first Python application. The main design
principle is:

```text
Financial math is computed deterministically in Python.
AI is used only for explanation, critique, or scenario generation.
```

## Why This Matters

Most portfolio tools show returns.

This system answers survival.

It focuses on:

- downside risk
- stress scenarios
- financial runway
- portfolio vulnerabilities
- investor-facing decisions

## System Architecture

```text
User Portfolio
      |
      v
Market Data (Task 2)
      |
      v
Risk Engine (Task 1)
      |
      v
Scenario Generator (Task 4 - AI)
      |
      v
Crash Engine (Python)
      |
      v
Decision Insight
      |
      v
AI Explanation (Task 3)
```

## Core Innovation: Crash Scenario Story Generator

Task 4 is the main product-level feature.

Instead of showing abstract percentages, the system generates real-world macro
scenarios and computes their impact on the portfolio. It turns a portfolio into
a survival question:

```text
If this story happens in the market, does the investor still survive?
```

The important boundary is strict:

- ChatGPT generates scenario stories and asset shock percentages.
- Python computes portfolio value, losses, runway, verdicts, ranking, and
  decision insight.

This keeps the product useful while keeping the financial math auditable.

## Start Here

Recommended first command:

```bash
python task4_crash_story.py --dry-run
```

This demonstrates the full crash-scenario system without requiring API keys,
network access, or OpenAI billing. It uses local JSON scenarios from `data/`.

## Quick Start

Requires Python 3.10+.

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Run the full test suite:

```bash
pytest -q
```

At the time of submission, the suite passes locally:

```text
91 passed
```

For AI tasks, create a `.env` file:

```text
OPENAI_API_KEY=your_key_here
```

Do not commit `.env`.

Task 2 requires internet access for live market data. If an API fails, the CLI
logs the error and continues with the remaining assets.

Task 3 and Task 4 live AI modes require `OPENAI_API_KEY`. Task 4 `--dry-run`
works without an API key and does not call OpenAI.

## Run Commands

```bash
python task1_risk.py
python task1_risk.py --moderate

python task2_market.py
python task2_market.py --interactive
python task2_market.py --no-cache
python task2_market.py --verbose
python task2_market.py --retries 5

python task3_advisor.py
python task3_advisor.py --tone experienced
python task3_advisor.py --critique
python task3_advisor.py --portfolio data/sample_portfolio.json
python task3_advisor.py --model gpt-4o
python task3_advisor.py --verbose

python task4_crash_story.py
python task4_crash_story.py --input
python task4_crash_story.py --dry-run
python task4_crash_story.py --verbose

python main.py
python main.py --crash-story
```

`--dry-run` for Task 4 does not call OpenAI. It uses local JSON scenarios.

## Main Entry

```bash
python main.py
```

Prints the available task commands.

```bash
python main.py --crash-story
```

Runs Task 4 through the combined entry point. This is useful when a reviewer
wants a single top-level command but the task implementations still remain
separate and testable.

## Assessment Mapping

- Task 1: `compute_risk_metrics()` is implemented in `core/risk_calculator.py`.
- Task 2: live stock/index plus crypto fetch is implemented in `task2_market.py`.
- Task 3: AI advisor with raw plus parsed output is implemented in
  `task3_advisor.py`.
- Task 4: open-problem crash scenario generator is implemented in
  `task4_crash_story.py`.

## Project Structure

```text
Timecell/
|-- cli/
|   |-- __init__.py
|   `-- portfolio_input.py
|-- config/
|   |-- __init__.py
|   |-- asset_categories.py
|   |-- crash_assumptions.py
|   |-- market_assets.py
|   |-- market_catalog.py
|   |-- prompts.py
|   `-- thresholds.py
|-- core/
|   |-- __init__.py
|   |-- ai_explainer.py
|   |-- breakpoint_detector.py
|   |-- crash_engine.py
|   |-- decision_insight.py
|   |-- market_fetcher.py
|   |-- report_formatter.py
|   |-- risk_calculator.py
|   |-- scenario_generator.py
|   `-- visualizer.py
|-- data/
|   |-- crash_story_default_portfolio.json
|   |-- crash_story_dry_run_scenarios.json
|   `-- sample_portfolio.json
|-- tests/
|   |-- test_ai_explainer.py
|   |-- test_market_fetcher.py
|   |-- test_risk_calculator.py
|   |-- test_task2_market_cli.py
|   |-- test_task3_advisor_cli.py
|   `-- test_task4_crash_story.py
|-- task1_risk.py
|-- task2_market.py
|-- task3_advisor.py
|-- task4_crash_story.py
|-- main.py
|-- requirements.txt
|-- README_TASK1.md
|-- README_TASK2.md
|-- README_TASK3.md
`-- README_TASK4.md
```

## Task 1 - Portfolio Risk Calculator

TL;DR:

- Task 1 computes portfolio crash risk mathematically.
- It is the deterministic foundation reused by later tasks.
- It answers whether the investor passes a 12-month survival threshold.

### Requirement

Implement:

```python
compute_risk_metrics(portfolio)
```

It must return:

- `post_crash_value`
- `runway_months`
- `ruin_test`
- `largest_risk_asset`
- `concentration_warning`

### Implementation

Main files:

```text
core/risk_calculator.py
core/visualizer.py
config/crash_assumptions.py
cli/portfolio_input.py
task1_risk.py
tests/test_risk_calculator.py
```

### Features

- Pure deterministic math engine.
- Interactive CLI.
- Unknown assets use fallback crash assumption.
- Unallocated remainder becomes Cash.
- Allocation above 100% is prevented.
- Moderate crash bonus via `--moderate`.
- CLI visualizer for allocation and risk metrics.
- Edge cases covered:
  - zero allocation
  - 100% cash
  - monthly expenses = 0
  - runway exactly 12 months
  - concentration exactly 40%
  - invalid portfolio shape

### CLI Options Explained

```bash
python task1_risk.py
```

Runs the standard severe-crash portfolio risk calculator. It asks for portfolio
value, monthly expenses, and asset allocations, then prints deterministic risk
metrics.

```bash
python task1_risk.py --moderate
```

Uses 50% of the severe crash assumptions. This simulates a less severe market
stress while keeping the same deterministic math engine.

### Core Formula

```text
asset_value = total_value * allocation_pct / 100
post_crash_asset_value = asset_value * (1 + crash_pct / 100)
post_crash_value = sum(post_crash_asset_value)
runway_months = post_crash_value / monthly_expenses
ruin_test = PASS if runway_months > 12 else FAIL
risk_score = allocation_pct * abs(expected_crash_pct)
```

## Task 2 - Live Market Data Fetch

TL;DR:

- Task 2 fetches live prices for stocks, indices, and crypto.
- It handles provider failures per asset instead of crashing the whole CLI.
- It can use cached prices as a fallback when providers fail.

### Requirement

Fetch current prices for at least three assets, including:

- at least one stock or index
- at least one crypto asset

Print a clean terminal table and handle API failures gracefully.

### Implementation

Main files:

```text
task2_market.py
core/market_fetcher.py
config/market_assets.py
config/market_catalog.py
tests/test_market_fetcher.py
tests/test_task2_market_cli.py
```

### Features

- Fetches Indian indices/stocks using `yfinance`.
- Fetches crypto prices using CoinGecko.
- Default assets include NIFTY50, SENSEX, RELIANCE, BTC, and ETH.
- Interactive asset selection.
- Per-asset error isolation.
- Retry logic with exponential backoff and jitter.
- HTTP timeout handling.
- CoinGecko rate-limit handling.
- Optional stale-cache fallback.
- Logs failures to `logs/app.log`.
- Prints a clean ASCII table with price, currency, and source.

### CLI Options Explained

```bash
python task2_market.py
```

Fetches the default asset list once and prints a terminal table. Cache fallback
is enabled by default, so the CLI can still show the last successful price if a
provider is temporarily unavailable.

```bash
python task2_market.py --interactive
```

Lets the user choose assets manually from the configured market catalog instead
of using the default list.

```bash
python task2_market.py --no-cache
```

Disables fallback cached prices. This forces live provider calls only; failed
providers show as failed instead of using stale cache data.

```bash
python task2_market.py --verbose
```

Prints log lines to the terminal in addition to writing them to `logs/app.log`.
Useful for debugging API failures and retry behavior.

```bash
python task2_market.py --retries 5
```

Sets the number of retry attempts per asset. The default is `3`, and the value
must be at least `1`.

## Task 3 - AI-Powered Portfolio Explainer

TL;DR:

- Task 3 explains deterministic Task 1 risk results in plain English.
- It prints both the raw LLM response and parsed structured output.
- It uses AI for communication, not for portfolio math.

### Requirement

Use an LLM API to explain portfolio risk in plain English.

Output must include:

- 3-4 sentence summary
- one thing the investor is doing well
- one thing the investor should consider changing
- one-line verdict: Aggressive, Balanced, or Conservative
- raw API response and parsed structured output separately

### Implementation

Main files:

```text
task3_advisor.py
core/ai_explainer.py
config/prompts.py
tests/test_ai_explainer.py
tests/test_task3_advisor_cli.py
```

### Features

- OpenAI integration.
- Prompt logic, API call, and parsing are separated.
- Uses deterministic Task 1 metrics as source of truth.
- LLM is not asked to compute risk numbers.
- Raw response is printed separately from parsed output.
- JSON parsing and schema validation.
- Configurable tone:
  - beginner
  - experienced
  - expert
- Bonus second LLM call for critique.
- API failures are caught and shown as clean CLI errors.
- Tests mock OpenAI calls, so they run offline.

### CLI Options Explained

```bash
python task3_advisor.py
```

Starts interactive portfolio input, sends the computed risk context to the AI
advisor, and prints raw plus structured output.

```bash
python task3_advisor.py --portfolio data/sample_portfolio.json
```

Loads a portfolio from a JSON file instead of asking for interactive input.
The file must include `total_value_inr`, `monthly_expenses_inr`, and `assets`.

```bash
python task3_advisor.py --tone beginner
python task3_advisor.py --tone experienced
python task3_advisor.py --tone expert
```

Controls the explanation style:

- `beginner`: simple language with minimal finance jargon.
- `experienced`: moderate finance terms and practical investor language.
- `expert`: concise, technical, and more direct.

```bash
python task3_advisor.py --critique
```

Runs a second LLM call that critiques the first explanation for accuracy,
specificity, and missed points.

```bash
python task3_advisor.py --model gpt-4o
```

Overrides the default OpenAI model used by the advisor.

```bash
python task3_advisor.py --verbose
```

Prints log lines to the terminal in addition to writing them to `logs/app.log`.

### Prompt Design

Task 3 prompts live in `config/prompts.py`:

- `SYSTEM_PROMPT`
- `USER_PROMPT_TEMPLATE`
- `TONE_INSTRUCTIONS`
- `CRITIQUE_SYSTEM_PROMPT`

Important prompt rules:

- Output only JSON.
- Use computed numbers from Python.
- Do not invent portfolio values.
- Mention post-crash value, loss percentage, runway, ruin test,
  largest-risk asset, and concentration warning.
- Verdict must be exactly `Aggressive`, `Balanced`, or `Conservative`.
- Recommendation must name an asset and target action.

## Task 4 - Crash Scenario Story Generator

TL;DR:

- Task 4 simulates real-world crash scenarios for a portfolio.
- AI generates scenario stories and shock maps.
- Python computes every financial number and final decision.
- This is the main product-level feature in the submission.

### Open Problem Choice

For the open problem, I built a Crash Scenario Story Generator.

It is a CLI feature that answers:

```text
What macro stories could break this portfolio, and why?
```

It combines AI scenario generation with deterministic portfolio stress math.

### Implementation

Main files:

```text
task4_crash_story.py
core/scenario_generator.py
core/crash_engine.py
core/breakpoint_detector.py
core/decision_insight.py
core/report_formatter.py
config/asset_categories.py
config/thresholds.py
data/crash_story_default_portfolio.json
data/crash_story_dry_run_scenarios.json
tests/test_task4_crash_story.py
```

### CLI Options Explained

```bash
python task4_crash_story.py
```

Runs Task 4 using the default portfolio and live OpenAI scenario generation.
Requires `OPENAI_API_KEY`.

```bash
python task4_crash_story.py --input
```

Allows manual portfolio entry. The user can type any asset name; Task 4 asks
ChatGPT to generate scenario-specific shocks for those exact assets.

```bash
python task4_crash_story.py --dry-run
```

Uses local scenarios from `data/crash_story_dry_run_scenarios.json` instead of
calling OpenAI. No API key, network access, or API cost is required. This is
the recommended demo command.

```bash
python task4_crash_story.py --verbose
```

Prints Task 4 logs to the terminal in addition to writing them to
`logs/app.log`.

### Product Principle

Task 4 follows a strict AI boundary:

```text
ChatGPT generates:
- scenario name
- narrative
- shock_map
- severity
- likelihood
- takeaway

Python computes:
- pre-crash value
- post-crash value
- INR loss
- loss percentage
- runway months
- PASS/FAIL verdict
- ranking
- decision insight
```

This prevents the language model from guessing financial math.

### Task 4 Flow

1. Load default or custom portfolio.
2. Compute baseline runway.
3. Run binary search for the portfolio break point.
4. Generate macro scenarios with OpenAI/ChatGPT.
5. Validate scenario JSON.
6. Apply each scenario's `shock_map` to the portfolio.
7. Reuse `compute_risk_metrics()` from Task 1.
8. Compute why the scenario breaks or holds.
9. Rank scenarios.
10. Print decision insight, fixability, and final decision summary.

### Scenario Validation

Before computing, Task 4 validates:

- scenario is a JSON object
- `name` exists
- `shock_map` exists
- `shock_map` is not empty
- all shock values are numeric
- scenario count is between 4 and 5

Invalid scenarios are skipped and logged.

### Breakpoint Detector

`core/breakpoint_detector.py` finds the minimum uniform crash percentage at
which the portfolio fails the 12-month runway test.

It uses binary search and applies the crash only to non-cash assets.

It also handles:

- already failing portfolio
- never failing portfolio
- normal breakpoint case

### Crash Engine

`core/crash_engine.py` applies OpenAI/ChatGPT's `shock_map` values.

Important behavior:

- It does not import `config/crash_assumptions.py`.
- It does not use generic crash assumptions.
- It deep-copies the portfolio before applying shocks.
- Missing assets default to 0% shock and log a warning.
- Actual math is delegated to `compute_risk_metrics()`.

### Decision Intelligence

`core/decision_insight.py` converts computed scenario outcomes into final
portfolio guidance.

Portfolio status logic:

```text
all scenarios fail       -> NOT RESILIENT
majority fail            -> FRAGILE
some fail                -> MODERATELY RESILIENT
all pass                 -> RESILIENT
```

It separates structural risk from market risk:

- If baseline runway is below 12 months, the problem is capital vs expenses.
- If baseline runway is healthy but scenarios fail, the problem is allocation
  risk.

It also prints:

- strengths
- vulnerabilities
- recommendations
- fixability
- final decision summary

### Correlation Awareness

`config/asset_categories.py` groups assets into categories:

- crypto
- Indian equities
- global tech
- defensive assets

If multiple affected assets belong to the same category, Task 4 prints a
correlation note.

Example:

```text
Reliance and Zomato all belong to Indian equities.
This creates correlated downside risk when that category is stressed.
```

### Task 4 Prompt Engineering

The Task 4 OpenAI/ChatGPT system prompt is `CRASH_STORY_SYSTEM_PROMPT` in
`config/prompts.py`.

It was changed and strengthened to produce better output.

Key prompt improvements:

1. **Strict JSON output**

   The model must return a raw JSON array only. No markdown, no prose, no code
   fences.

2. **Math boundary**

   The prompt forbids the model from generating portfolio values, INR losses,
   runway months, or PASS/FAIL verdicts.

3. **Every asset must be covered**

   The `shock_map` must include every asset in the portfolio, using the exact
   asset name strings from user input.

4. **Scenario diversity**

   The model is asked for diverse scenarios:

   - crypto-specific regulatory or structural risk
   - India macro risk
   - global contagion risk
   - currency or inflation risk
   - tail-risk or black-swan risk

5. **Portfolio-aware scenario generation**

   The prompt ties scenarios to actual holdings:

   - BTC or crypto -> regulation, exchange, custody, liquidity stress
   - Reliance -> oil prices, Indian macro, policy risk
   - Zomato -> consumer demand, startup funding, discretionary spending
   - Tesla or Apple -> US tech sentiment, rates, growth-stock valuation
   - Indian equities -> RBI, FII flows, election, rupee, fiscal policy
   - Gold -> safe-haven flows and currency/inflation protection
   - Cash -> preservation, inflation erosion, or bank-failure risk

6. **Avoid generic scenarios**

   Each scenario must explicitly affect at least two portfolio assets through
   the shock map and narrative.

7. **Severity discipline**

   Severity labels are constrained:

   ```text
   LOW     -> estimated portfolio loss below 10%
   MEDIUM  -> estimated portfolio loss between 10% and 25%
   HIGH    -> estimated portfolio loss between 25% and 40%
   EXTREME -> estimated portfolio loss above 40%
   ```

8. **At least one strong downside case**

   The prompt asks for at least one scenario that either reduces runway below
   12 months or causes loss above 25%.

9. **Extreme tail-risk scenario**

   The prompt asks for one EXTREME scenario, such as:

   ```text
   BTC -70% to -85%
   equities -30% to -50%
   ```

10. **Better investor takeaway**

    The prompt discourages generic advice like "consider diversification" and
    asks for asset-specific, actionable takeaways.

### Task 4 Dry Run

Test this feature without network access or API keys:

```bash
python task4_crash_story.py --dry-run
```

It loads:

```text
data/crash_story_default_portfolio.json
data/crash_story_dry_run_scenarios.json
```

## Shared Config

### `config/thresholds.py`

Centralizes:

- `RUNWAY_THRESHOLD_MONTHS`
- `CONCENTRATION_THRESHOLD_PCT`
- `CONCENTRATION_ALERT_PCT`

This avoids threshold drift between modules.

### `config/asset_categories.py`

Centralizes asset classification for Task 4:

- cash
- crypto
- gold
- Indian equities
- global tech
- defensive assets

This avoids repeated string matching logic across modules.

### `config/prompts.py`

Stores all LLM prompts:

- Task 3 advisor prompt
- Task 3 user prompt template
- Task 3 tone instructions
- Task 3 critique prompt
- Task 4 crash-story system prompt

## Test Coverage

The test suite is offline and deterministic.

```bash
pytest -q
```

Current coverage areas:

- Task 1 risk math and edge cases
- Task 2 market fetcher with mocked API calls
- Task 2 CLI behavior
- Task 3 prompt building, parsing, invalid model responses, and critique
  parsing
- Task 3 CLI behavior
- Task 4 scenario parsing and validation
- Task 4 shock-map application
- Task 4 largest-loss contributor logic
- Task 4 breakpoint detection
- Task 4 decision insight
- Task 4 formatter correlation notes
- Task 4 dry-run CLI

## Logging

Logs are written to:

```text
logs/app.log
```

Tasks log:

- task start and completion
- API failures
- fetch failures
- cache fallback
- scenario generation issues
- missing shock-map assets

Use `--verbose` where supported to echo logs to the terminal.

## AI Usage

AI tools including Claude, Codex, and ChatGPT were used as engineering
assistants for:

- architecture design discussion
- prompt engineering
- code review and refactoring suggestions
- test case generation
- documentation drafting

However:

- All financial calculations are implemented in Python.
- AI is not used for risk computation.
- AI is not used for portfolio math.
- AI is not used for decision logic.

AI is only used for:

- scenario generation in Task 4
- explanation and critique in Task 3

This ensures the system remains deterministic and auditable.

## Submission Notes

The technical assessment asks for:

- public GitHub repository
- README explaining approach
- 3-5 minute Loom or screen recording
- one paragraph about the hardest part and approach

Suggested Loom structure:

1. Show Task 1 risk calculator and tests.
2. Show Task 2 market fetch with fallback and error handling.
3. Show Task 3 raw LLM response and parsed structured output.
4. Show Task 4 dry-run first, then live scenario generation if API is
   available.
5. Explain the AI/math boundary: LLM writes narratives and shocks; Python
   computes results.

## Limitations

This project is a technical assessment, not investment advice.

Known limitations:

- Market data APIs can rate-limit or fail.
- Task 4 scenarios are plausible simulations, not forecasts.
- Task 4 uses simplified asset-category correlation.
- Tax, liquidity, investor age, income, and real-time holdings are not modeled.
- LLM output quality depends on provider behavior, so validation and dry-run
  mode are included.
