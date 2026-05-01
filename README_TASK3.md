# Task 3 - AI-Powered Portfolio Explainer

A CLI-based AI advisor that converts quantitative portfolio risk metrics into
plain-English guidance for a non-expert investor.

This task uses OpenAI and prints both:

1. the raw LLM response
2. the parsed structured output

That directly matches the assessment requirement.

---

## Run

Interactive portfolio input:

```bash
python task3_advisor.py
```

Use a JSON portfolio file instead:

```bash
python task3_advisor.py --portfolio data/sample_portfolio.json
```

Change the explanation tone:

```bash
python task3_advisor.py --tone beginner
python task3_advisor.py --tone experienced
python task3_advisor.py --tone expert
```

Run the bonus critique call:

```bash
python task3_advisor.py --critique
```

Show logs in the terminal:

```bash
python task3_advisor.py --verbose
```

Override the OpenAI model:

```bash
python task3_advisor.py --model gpt-4o-mini
```

---

## Environment

Set your OpenAI key in `.env`:

```text
OPENAI_API_KEY=your_key_here
```

The code loads `.env` automatically via `python-dotenv`.

Never commit `.env`.

---

## Input

By default, Task 3 asks for portfolio details interactively:

```text
Total portfolio value (INR) : 1000000
Monthly expenses (INR)      : 50000
Asset name [100.00% remaining] : BTC
Allocation % for BTC (max 100.00) : 40
Asset name [ 60.00% remaining] : Gold
Allocation % for Gold (max 60.00) : 20
Asset name [ 40.00% remaining] :
```

The remaining allocation is automatically treated as cash:

```text
unallocated 40.00% -> treated as Cash @ 0% crash
```

Crash percentages are looked up from:

```text
config/crash_assumptions.py
```

This means the user does not need to know crash assumptions.

---

## Portfolio JSON Format

You can also pass a portfolio JSON file:

```json
{
  "total_value_inr": 10000000,
  "monthly_expenses_inr": 80000,
  "assets": [
    {"name": "BTC", "allocation_pct": 30, "expected_crash_pct": -80},
    {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
    {"name": "GOLD", "allocation_pct": 20, "expected_crash_pct": -15},
    {"name": "CASH", "allocation_pct": 10, "expected_crash_pct": 0}
  ]
}
```

Run:

```bash
python task3_advisor.py --portfolio data/sample_portfolio.json
```

---

## Prompt Design

Prompt templates are stored in:

```text
config/prompts.py
```

The prompt is split into:

| Prompt part | Purpose |
| ----------- | ------- |
| `SYSTEM_PROMPT` | Defines the advisor persona, JSON schema, and hard rules. |
| `USER_PROMPT_TEMPLATE` | Injects actual portfolio metrics and tone instruction. |
| `CRITIQUE_SYSTEM_PROMPT` | Used by the bonus critique call. |

The final OpenAI request sends:

```python
messages=[
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": filled_user_prompt},
]
```

The user prompt includes:

- total portfolio value
- monthly expenses
- asset allocation
- crash assumptions
- post-crash value
- absolute loss
- loss percentage
- runway months
- ruin-test result
- largest-risk asset
- concentration warning
- tone instruction

---

## Prompt Approach

The prompt was designed to make the model behave like:

```text
A friendly but honest financial advisor speaking to a non-expert investor in India.
```

Important rules in the prompt:

- Output only JSON.
- Do not invent numbers.
- Use the actual risk metrics.
- Keep language simple.
- Give one specific positive observation.
- Give one specific actionable improvement.
- Verdict must be exactly one of:
  - `Aggressive`
  - `Balanced`
  - `Conservative`

What worked:

- Giving the model computed metrics instead of asking it to do math.
- Forcing JSON output with exact field names.
- Passing tone as a separate instruction.
- Parsing and validating the response after the API call.

What changed during development:

- The portfolio input moved from a fixed sample file to interactive input.
- Prompt templates were moved to `config/prompts.py` to keep prompt iteration separate from API code.
- The API response is now parsed and validated before structured output is printed.
- OpenAI API failures are caught and shown as clean CLI errors instead of tracebacks.

---

## Output

The CLI first prints a waiting message:

```text
Sending portfolio to the AI advisor...
Kindly wait for the response. This can take a few seconds.
```

Then it prints the raw response:

```text
RAW LLM RESPONSE
...
```

Then it prints the parsed structured output:

```text
STRUCTURED OUTPUT

Risk Summary
------------
...

Doing Well
----------
...

Consider Changing
-----------------
...

Verdict
-------
Balanced
```

---

## Tone Control

Supported tones:

```text
beginner
experienced
expert
```

The tone changes the audience instruction in the prompt:

- `beginner`: simple words, short sentences, assumes no finance background
- `experienced`: can use common investing terms
- `expert`: terse and direct, assumes portfolio knowledge

---

## Critique Bonus

Run:

```bash
python task3_advisor.py --critique
```

This makes a second LLM call. The second call receives:

1. the original portfolio metrics
2. the first advisor response

It returns:

```json
{
  "accuracy_issues": [],
  "specificity_issues": [],
  "missed_points": [],
  "overall_grade": "A"
}
```

This is a guardrail to check whether the first explanation stayed accurate.

---

## Code Layout

```text
task3_advisor.py          # CLI, dotenv loading, output rendering
core/ai_explainer.py      # prompt fill, OpenAI call, JSON parsing
config/prompts.py         # prompt templates and tone instructions
cli/portfolio_input.py    # shared interactive portfolio input
tests/test_ai_explainer.py
tests/test_task3_advisor_cli.py
```

The separation is deliberate:

- prompt templates live in `config/`
- OpenAI integration and parsing live in `core/`
- CLI concerns live in `task3_advisor.py`
- portfolio input is shared with Task 1

---

## Tests

Run:

```bash
pytest -q
```

The tests mock OpenAI calls, so they run offline and deterministically.

They cover:

- prompt construction
- tone selection
- JSON parsing
- missing fields
- invalid verdicts
- critique parsing
- OpenAI error wrapping
- interactive portfolio input
