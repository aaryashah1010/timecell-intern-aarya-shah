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
If this story happens in the market, does the investor still surv ive?
```

The important boundary is strict:

- The AI model generates scenario stories and asset shock percentages.
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
99 passed
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
python task1_risk.py --compare

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
python main.py --task1
python main.py --task1 --moderate
python main.py --task1 --compare
python main.py --task2
python main.py --task2 --interactive
python main.py --task3 --portfolio data/sample_portfolio.json --tone experienced
python main.py --task3 --portfolio data/sample_portfolio.json --tone experienced --critique
python main.py --task4 --dry-run
python main.py --task4 --input
python main.py --crash-story
```

`--dry-run` for Task 4 does not call OpenAI. It uses local JSON scenarios.

## Main Entry

```bash
python main.py
```

Opens an interactive numbered menu:

```text
1. Task 1 - Portfolio Risk Calculator
2. Task 2 - Live Market Data Fetch
3. Task 3 - AI Portfolio Explainer
4. Task 4 - Crash Scenario Story Generator
0. Exit
```

Choose `1`, `2`, `3`, or `4` and the selected task runs immediately.
For direct execution without the menu, use the flags below.

```bash
python main.py --task1
python main.py --task1 --moderate
python main.py --task1 --compare
```

Runs Task 1 through the combined entry point. Task-specific flags are passed
through to `task1_risk.py`.

```bash
python main.py --task2
python main.py --task2 --interactive
python main.py --task2 --no-cache
python main.py --task2 --verbose --retries 5
```

Runs Task 2 through the combined entry point. Market-fetch flags are passed
through to `task2_market.py`.

```bash
python main.py --task3
python main.py --task3 --portfolio data/sample_portfolio.json --tone experienced
python main.py --task3 --portfolio data/sample_portfolio.json --tone experienced --critique
```

Runs Task 3 through the combined entry point. Advisor flags are passed through
to `task3_advisor.py`.

```bash
python main.py --task4
python main.py --task4 --dry-run
python main.py --task4 --input
```

Runs Task 4 through the combined entry point. Crash-story flags are passed
through to `task4_crash_story.py`.

```bash
python main.py --crash-story
```

Backward-compatible alias for `python main.py --task4`. You can also pass Task
4 flags, for example `python main.py --crash-story --dry-run`.

## Assessment Mapping

- Task 1: `compute_risk_metrics()` is implemented in `core/risk_calculator.py`.
- Task 2: live stock/index plus crypto fetch is implemented in `task2_market.py`.
- Task 3: AI advisor with raw plus parsed output is implemented in
  `task3_advisor.py`.
- Task 4: open-problem crash scenario generator is implemented in
  `task4_crash_story.py`.

## PDF Requirement Checklist

This section maps the implementation directly to the uploaded technical test.

Task 1 asks for deterministic portfolio risk metrics:

- `compute_risk_metrics(portfolio)` returns the required five fields.
- The severe crash path uses the full `expected_crash_pct` assumptions.
- The moderate bonus is implemented with `python task1_risk.py --moderate`.
- The side-by-side bonus is implemented with `python task1_risk.py --compare`.
- The CLI includes an ASCII allocation bar chart without plotting libraries.
- Tests cover zero allocation, 100% cash, boundary runway, concentration, and
  invalid inputs.

Task 2 asks for live market data:

- The default fetch includes Indian stock/index assets and crypto assets.
- `yfinance` is used for stocks/indices and CoinGecko is used for crypto.
- Failed assets are isolated, logged, and do not crash the whole command.
- Retry, timeout, rate-limit, cache fallback, and `--no-cache` behavior are
  implemented.

Task 3 asks for AI-powered explanation and prompt documentation:

- The prompt lives in code in `config/prompts.py`.
- The script accepts interactive portfolios or JSON files.
- Raw model output and parsed structured output are printed separately.
- Tone is configurable with `--tone beginner|experienced|expert`.
- The critique bonus is implemented with `--critique`.
- The prompt iteration, what changed, and why are documented below.

Task 4 asks for an open-ended product idea:

- I built a crash scenario story generator for downside-survival decisions.
- It works in live AI mode and deterministic `--dry-run` mode.
- It shows judgment by separating AI-generated scenarios from Python-computed
  portfolio math.
- It is designed as a terminal-first feature, matching the assessment context.

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
|   |-- test_main_cli.py
|   |-- test_risk_calculator.py
|   |-- test_task1_compare.py
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
tests/test_task1_compare.py
```

### Features

- Pure deterministic math engine.
- Interactive CLI.
- Unknown assets use fallback crash assumption.
- Unallocated remainder becomes Cash.
- Allocation above 100% is prevented.
- Moderate crash bonus via `--moderate`.
- Severe plus moderate back-to-back reports via `--compare`.
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

```bash
python task1_risk.py --compare
```

Collects the portfolio once and prints severe and moderate outcomes side by
side using the same report format as the normal and `--moderate` commands.
This is the best Task 1 demo command because it shows both stress levels
without making the user enter the same portfolio twice.

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

### Prompt Iteration

The assessment specifically asks what prompt approach was tried, what worked,
what changed, and why.

Initial Task 3 prompt approach:

- Ask the model to act as a friendly financial advisor.
- Provide the portfolio and computed Task 1 metrics.
- Ask for four fields: summary, doing well, consider changing, and verdict.
- Ask for JSON so the CLI could parse the response.

What worked:

- The model produced readable explanations in plain English.
- The four-field JSON shape made the output easy to parse.
- Passing Python-computed metrics reduced hallucinated portfolio math.

What needed improvement:

- The model sometimes omitted one of the required metrics.
- Recommendations could be too generic, such as "diversify more."
- Verdicts needed stricter rules when runway, loss percentage, and
  concentration pointed in different directions.
- The critique call sometimes returned empty lists, which looked weak in the
  terminal output.

Changes made:

- Added strict metric coverage rules for post-crash value, loss percentage,
  runway, ruin test, largest-risk asset, and concentration warning.
- Added exact verdict rules:
  - `Aggressive` if runway is below 12 months, loss is above 50%, or
    concentration warning is true.
  - `Balanced` only when runway, loss, and concentration all fit the balanced
    range.
  - `Conservative` only when runway is strong, loss is low, and concentration
    warning is false.
- Added tone-specific instructions for `beginner`, `experienced`, and `expert`.
- Strengthened recommendation rules so the answer names an asset and target
  action.
- Added a second critique prompt with source-of-truth metrics, null-metric
  handling, grade calibration, and concrete feedback categories.
- Updated critique rendering so empty sections print useful sentences instead
  of `(none)`.

Why these changes helped:

- The output became more consistent and easier to evaluate.
- The verdict became auditable against deterministic metrics.
- The recommendation became more actionable for an investor.
- The code structure matches the PDF requirement: prompt logic, API call, and
  output parsing are separated.

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
the AI model to generate scenario-specific shocks for those exact assets.

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
AI model generates:
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
4. Generate macro scenarios with OpenAI.
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

`core/crash_engine.py` applies the AI-generated `shock_map` values.

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

The Task 4 OpenAI system prompt is `CRASH_STORY_SYSTEM_PROMPT` in
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

### Task 4 Prompt Iteration

Initial Task 4 prompt approach:

- Ask the AI model to generate five macro crash scenarios.
- Ask for scenario names, narratives, severity, likelihood, and a `shock_map`.
- Keep all portfolio calculations outside the model.

What worked:

- The model was good at producing realistic macro narratives.
- Scenario-specific shocks were more useful than one static crash table.
- The narrative made the risk report easier to explain in a demo.

What needed improvement:

- Some scenarios were too generic.
- Some responses did not stress the actual assets in the portfolio enough.
- Severity labels were sometimes weaker than the modeled shock.
- All scenarios could pass, which made the stress test feel too soft.
- The model needed repeated instruction not to compute portfolio values.

Changes made:

- Added a strict AI/math boundary: the model may generate only scenario
  identity, narrative, shock map, severity, likelihood, and takeaway.
- Forbid the model from generating portfolio value, INR loss, runway, or
  PASS/FAIL verdict.
- Required every portfolio asset to appear in every `shock_map` using the exact
  asset name string.
- Added portfolio-aware rules:
  - crypto holdings trigger regulation, exchange, custody, and liquidity risks
  - Indian equities trigger RBI, FII flow, election, rupee, and fiscal risks
  - global tech triggers rates and growth-stock valuation risks
  - gold triggers safe-haven and inflation/currency behavior
  - cash triggers preservation, inflation erosion, or bank-failure risk
- Required each scenario to affect at least two portfolio assets.
- Required diversity across crypto, India macro, global contagion, currency or
  inflation, and tail-risk scenarios.
- Added severity bands: `LOW`, `MEDIUM`, `HIGH`, and `EXTREME`.
- Required at least one strong downside case and one `HIGH` or `EXTREME`
  scenario.
- Added validation before computation so malformed scenarios are skipped.
- Added dry-run JSON scenarios so reviewers can test Task 4 without API access.

Why these changes helped:

- Task 4 became more product-like instead of just another calculation script.
- The output became portfolio-aware instead of generic.
- The deterministic engine remained responsible for all financial math.
- The open-problem submission demonstrates judgment, originality, and
  execution, which are the PDF scoring dimensions for Task 4.

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

- Main dispatcher routing and task-argument pass-through
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

AI tools including Claude, Codex, and OpenAI models were used as engineering
assistants for:

- architecture design discussion
- prompt engineering
- code review and refactoring suggestions
- test case generation
- documentation drafting

For the live application features, I used the OpenAI API because it was
available to me, supports structured JSON-style outputs reliably, and fits the
assessment rule that any LLM provider may be used. The provider can be swapped
later because prompt construction, API calls, and parsing are separated in
`core/ai_explainer.py` and `core/scenario_generator.py`.

However:

- All financial calculations are implemented in Python.
- AI is not used for risk computation.
- AI is not used for portfolio math.
- AI is not used for decision logic.

AI is only used for:

- scenario generation in Task 4
- explanation and critique in Task 3

This ensures the system remains deterministic and auditable.


## Limitations

This project is a technical assessment, not investment advice.

Known limitations:

- Market data APIs can rate-limit or fail.
- Task 4 scenarios are plausible simulations, not forecasts.
- Task 4 uses simplified asset-category correlation.
- Tax, liquidity, investor age, income, and real-time holdings are not modeled.
- LLM output quality depends on provider behavior, so validation and dry-run
  mode are included.
