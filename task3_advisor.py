"""Task 3 entry point: AI-Powered Portfolio Explainer.

Collects a portfolio (interactively or from a JSON file), sends it to the
LLM advisor, and prints both the raw API response and the parsed structured
output, per the spec.

Run:
    python task3_advisor.py                                  # interactive portfolio input
    python task3_advisor.py --portfolio path/to/p.json       # load from JSON instead
    python task3_advisor.py --tone experienced               # beginner | experienced | expert
    python task3_advisor.py --critique                       # bonus: second LLM call critiques the first
    python task3_advisor.py --model gpt-4o                   # override model
    python task3_advisor.py --verbose                        # echo log lines to stderr

Set OPENAI_API_KEY in your environment or in a .env file at the project root.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from cli.portfolio_input import collect_portfolio_dict
from core.ai_explainer import (
    DEFAULT_MODEL,
    Critique,
    Explanation,
    critique_explanation,
    explain_portfolio,
)

log = logging.getLogger("task3")

WIDTH: int = 64


# ---------- runtime setup ----------

def setup_logging(log_dir: Path, *, verbose: bool) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    ]
    handlers[0].setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    if verbose:
        stderr = logging.StreamHandler(sys.stderr)
        stderr.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
        handlers.append(stderr)
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


def load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _ensure_utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass


# ---------- portfolio loading (CLI boundary validation) ----------

def load_portfolio_from_file(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"portfolio file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"portfolio file {path} is not valid JSON: {exc}")
    _validate_portfolio_shape(data, str(path))
    return data


def _validate_portfolio_shape(data: object, source: str) -> None:
    if not isinstance(data, dict):
        raise SystemExit(f"{source}: top-level must be a JSON object")
    for key in ("total_value_inr", "monthly_expenses_inr", "assets"):
        if key not in data:
            raise SystemExit(f"{source}: missing required key {key!r}")
    if not isinstance(data["assets"], list) or not data["assets"]:
        raise SystemExit(f"{source}: 'assets' must be a non-empty list")
    for i, asset in enumerate(data["assets"]):
        for key in ("name", "allocation_pct", "expected_crash_pct"):
            if key not in asset:
                raise SystemExit(f"{source}: assets[{i}] missing key {key!r}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Task 3 - AI Portfolio Explainer")
    p.add_argument(
        "--portfolio",
        type=Path,
        default=None,
        help="optional path to portfolio JSON; omitted means interactive input",
    )
    p.add_argument(
        "--tone",
        choices=("beginner", "experienced", "expert"),
        default="beginner",
        help="audience register for the explanation (default: beginner)",
    )
    p.add_argument(
        "--critique",
        action="store_true",
        help="bonus: run a second LLM call that critiques the first explanation",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use (default: {DEFAULT_MODEL})",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="echo log lines to stderr")
    return p.parse_args()


# ---------- output rendering ----------

def _section(title: str) -> str:
    return f"\n{title}\n{'-' * len(title)}"


def render_raw_response(explanation: Explanation) -> str:
    return "\n".join([
        "=" * WIDTH,
        " RAW LLM RESPONSE ".center(WIDTH, "="),
        "=" * WIDTH,
        f"(model={explanation.model}, tone={explanation.tone})",
        "",
        explanation.raw_response,
    ])


def render_structured_output(explanation: Explanation) -> str:
    return "\n".join([
        "\n" + "=" * WIDTH,
        " STRUCTURED OUTPUT ".center(WIDTH, "="),
        "=" * WIDTH,
        _section("Risk Summary"),
        explanation.summary,
        _section("Doing Well"),
        explanation.doing_well,
        _section("Consider Changing"),
        explanation.consider_changing,
        _section("Verdict"),
        explanation.verdict,
    ])


def render_critique(critique: Critique) -> str:
    def block(label: str, items: tuple[str, ...], fallback: str) -> str:
        if not items:
            return f"\n{label}\n  - {fallback}"
        return "\n" + label + "\n" + "\n".join(f"  - {x}" for x in items)

    return "\n".join([
        "\n" + "=" * WIDTH,
        " CRITIQUE (second LLM call) ".center(WIDTH, "="),
        "=" * WIDTH,
        f"Overall grade: {critique.overall_grade}",
        block(
            "Accuracy issues",
            critique.accuracy_issues,
            "No major accuracy issue found against the source-of-truth metrics.",
        ),
        block(
            "Specificity issues",
            critique.specificity_issues,
            "No major specificity gap found in the explanation.",
        ),
        block(
            "Missed points",
            critique.missed_points,
            "No major missed point identified after reviewing the required metrics.",
        ),
    ])


# ---------- orchestration ----------

def main() -> int:
    args = parse_args()
    _ensure_utf8_stdout()
    setup_logging(Path("logs"), verbose=args.verbose)
    load_dotenv_if_present()

    if args.portfolio is not None:
        portfolio = load_portfolio_from_file(args.portfolio)
    else:
        portfolio = collect_portfolio_dict(banner="AI Portfolio Advisor")
        if not portfolio["assets"]:
            print("\nNo assets entered. Nothing to explain.")
            return 1

    log.info(
        "task3 start portfolio=%s tone=%s model=%s critique=%s",
        args.portfolio or "interactive", args.tone, args.model, args.critique,
    )

    try:
        print()
        print("Sending portfolio to the AI advisor...")
        print("Kindly wait for the response. This can take a few seconds.")
        print()
        explanation = explain_portfolio(portfolio, tone=args.tone, model=args.model)
    except RuntimeError as exc:
        # missing API key, network failure, etc. -- print, don't traceback
        print(f"Error: {exc}", file=sys.stderr)
        log.error("explain_portfolio failed: %s", exc)
        return 1
    except ValueError as exc:
        # malformed LLM response
        print(f"LLM response could not be parsed: {exc}", file=sys.stderr)
        log.error("parse failure: %s", exc)
        return 1

    print(render_raw_response(explanation))
    print(render_structured_output(explanation))

    if args.critique:
        try:
            print()
            print("Running second AI critique call...")
            print("Kindly wait for the critique response.")
            critique = critique_explanation(explanation, portfolio, model=args.model)
        except (RuntimeError, ValueError) as exc:
            print(f"\nCritique step failed: {exc}", file=sys.stderr)
            log.error("critique failed: %s", exc)
            return 0  # primary explanation still succeeded
        print(render_critique(critique))

    log.info("task3 complete verdict=%s", explanation.verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
