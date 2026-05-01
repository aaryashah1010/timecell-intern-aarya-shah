"""Render crash-scenario analysis reports to the terminal."""

from __future__ import annotations

RUNWAY_THRESHOLD_MONTHS: float = 12.0
LINE_WIDTH: int = 68
WRAP_WIDTH: int = 64


def fmt_inr(amount: float) -> str:
    """Format a number as Indian rupee currency text."""
    negative = amount < 0
    amount = abs(amount)
    integer_part = int(round(amount))
    digits = str(integer_part)

    if len(digits) > 3:
        last = digits[-3:]
        rest = digits[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        digits = ",".join(reversed(groups)) + "," + last

    prefix = "-₹" if negative else "₹"
    return f"{prefix}{digits}"


def print_header(portfolio: dict) -> None:
    """Print the top-level report header."""
    total = portfolio["total_value_inr"]
    expenses = portfolio["monthly_expenses_inr"]
    print()
    print(_divider())
    print("  TIMECELL - CRASH SCENARIO ANALYSIS")
    print(f"  Portfolio: {fmt_inr(total)}  |  Monthly Burn: {fmt_inr(expenses)}")
    print(_divider())
    print()


def print_breakpoint(bp: dict) -> None:
    """Print the portfolio break point section."""
    print("PORTFOLIO BREAK POINT")
    print(_divider("-"))
    print(f"  {bp['interpretation']}")
    if not bp["already_failing"]:
        print(
            f"  At check point:  {fmt_inr(bp['break_value_inr'])}"
            f"  |  Runway: {bp['break_runway']} months"
        )
    if bp.get("implications"):
        print("  This implies:")
        for implication in bp["implications"]:
            print(f"  - {implication}")
    print()


def print_critical_insight(baseline_runway: float) -> None:
    """Print structural-risk warning when the portfolio fails before shocks."""
    if baseline_runway >= RUNWAY_THRESHOLD_MONTHS:
        return

    print(_divider())
    print("  CRITICAL INSIGHT")
    print(_divider())
    print()
    print(
        "  This portfolio fails the 12-month survival threshold even "
        "without any market stress."
    )
    print()
    print("  This means:")
    print("  - the problem is structural (capital vs expenses)")
    print("  - not market-related")
    print()
    print("  No allocation change alone can fix this.")
    print()


def print_scenario(
    scenario: dict,
    metrics: dict,
    why: dict,
    index: int,
    total: int,
    portfolio: dict | None = None,
    baseline_runway: float | None = None,
) -> None:
    """Print one complete crash-scenario report block."""
    verdict = "PASS" if metrics["ruin_test"] == "PASS" else "FAIL"
    severity = scenario.get("severity", "-")
    likelihood = scenario.get("likelihood", "-")

    print(_divider())
    print(
        f"  SCENARIO {index} of {total}"
        f"  |  [{severity} SEVERITY]"
        f"  |  [{likelihood} LIKELIHOOD]"
    )
    print(f"  {scenario['name']}")
    print(_divider())

    print("\nNARRATIVE:")
    for line in _wrap(scenario.get("narrative", ""), WRAP_WIDTH):
        print(f"  {line}")

    print("\nASSUMPTIONS  (ChatGPT-generated; all math computed by engine):")
    for name, pct in scenario.get("shock_map", {}).items():
        sign = "+" if float(pct) > 0 else ""
        print(f"  {name:<18}->  {sign}{pct}%")

    print("\nIMPACT:")
    if "pre_crash_value" in metrics:
        print(f"  Pre-crash value:      {fmt_inr(metrics['pre_crash_value'])}")
    print(f"  Post-crash value:     {fmt_inr(metrics['post_crash_value'])}")
    print(
        f"  Total loss:           {fmt_inr(why['total_loss_inr'])}"
        f"  ({why['total_loss_pct']:.1f}%)"
    )
    print(f"  Runway:               {metrics['runway_months']:.1f} months")

    print(f"\nVERDICT:  {verdict}  (threshold: > {RUNWAY_THRESHOLD_MONTHS:.0f} months)")

    section_title = "WHY THIS BREAKS" if metrics["ruin_test"] == "FAIL" else "WHY THIS HOLDS"
    print(f"\n{section_title}:")
    largest = why["loss_breakdown"][0] if why["loss_breakdown"] else {}
    largest_asset = why["largest_loss_asset"]
    largest_loss = largest.get("loss_inr", 0.0)
    largest_pct = why["largest_loss_pct_of_total"]
    largest_alloc = largest.get("allocation_pct", 0.0)
    largest_shock = largest.get("shock_pct", 0.0)
    structural_failure = (
        metrics["ruin_test"] == "FAIL"
        and baseline_runway is not None
        and baseline_runway < RUNWAY_THRESHOLD_MONTHS
    )

    if largest_loss > 0:
        print(f"  {largest_asset} drives risk due to:")
        print(f"  - allocation exposure ({largest_alloc}% of portfolio)")
        print(f"  - scenario crash magnitude ({largest_shock:+.0f}%)")
        print(f"  - contributes {largest_pct:.0f}% of gross downside")
        print(
            f"  Asset-level loss from {largest_asset}: {fmt_inr(largest_loss)}"
        )
    else:
        print("  No asset-level downside is modeled in this scenario.")
        print(
            "  The failure comes from runway math rather than market "
            "loss contribution."
        )
    if why["concentration_culprit"] and largest_loss > 0:
        print(
            "  Concentration above the risk threshold amplifies this "
            "scenario's damage"
        )
    if structural_failure:
        print(
            f"  Baseline runway is only {baseline_runway:.1f} months before "
            "any market stress"
        )
        print("  Increase capital or reduce expenses before allocation changes")
    elif metrics["ruin_test"] == "FAIL":
        print(
            f"  Reducing {largest_asset} allocation is the primary lever "
            "to pass this scenario"
        )
    else:
        print(
            "  Portfolio holds because post-shock runway remains above "
            "the survival threshold"
        )

    if portfolio is not None:
        notes = _correlation_notes(portfolio, scenario.get("shock_map", {}))
        if notes:
            print("\nCORRELATION EFFECT:")
            for note in notes:
                for line in _wrap(note, WRAP_WIDTH):
                    print(f"  {line}")

    print("\nTAKEAWAY:")
    for line in _wrap(scenario.get("takeaway", ""), WRAP_WIDTH):
        print(f"  {line}")
    print()


def print_ranking(ranked: list[dict]) -> None:
    """Print the scenario ranking table sorted from worst to best."""
    print(_divider())
    print("  SCENARIO RANKING  (Worst -> Best)")
    print(_divider())
    print(f"  {'RANK':<5}  {'SCENARIO':<35}  {'RUNWAY':>8}  {'LOSS':>7}  VERDICT")
    print(f"  {'----':<5}  {'-' * 35:<35}  {'------':>8}  {'----':>7}  -------")

    fail_count = 0
    worst_assets: list[str] = []

    for rank, item in enumerate(ranked, 1):
        verdict = item["verdict"]
        if verdict == "FAIL":
            fail_count += 1
            culprit = item.get("primary_culprit")
            if culprit and culprit not in worst_assets:
                worst_assets.append(culprit)
        name_short = item["name"][:35]
        loss_pct = item.get("loss_pct", 0.0)
        print(
            f"  {rank:<5}  {name_short:<35}  {item['runway']:>6.1f} mo"
            f"  {loss_pct:>6.1f}%  {verdict}"
        )

    print()
    print(f"  Scenarios that FAIL:      {fail_count} of {len(ranked)}")
    if worst_assets:
        print(f"  Primary vulnerability:    {', '.join(worst_assets)}")
    print()


def print_decision_insight(insight: dict) -> None:
    """Print the final portfolio decision insight block."""
    print(_divider())
    print("  DECISION INSIGHT")
    print(_divider())
    print()
    print(
        f"  Your portfolio is {insight['status_text']} under modeled scenarios."
    )
    print()
    print("  Reason:")
    for reason in insight.get("reasons", []):
        print(f"  - {reason}")
    if insight.get("strengths"):
        print()
        print("  Supporting factors:")
        for strength in insight["strengths"]:
            print(f"  - {strength}")
    if insight.get("vulnerabilities"):
        print()
        print("  Key vulnerability:")
        for vulnerability in insight["vulnerabilities"]:
            print(f"  - {vulnerability}")
    print()
    print("  Recommendation:")
    for recommendation in insight.get("recommendations", []):
        print(f"  - {recommendation}")
    print()


def print_fixability(insight: dict) -> None:
    """Print whether allocation changes can fix the portfolio."""
    print(_divider())
    print("  FIXABILITY")
    print(_divider())
    print(f"  {insight['fixability']}")
    print()


def print_final_decision_summary(insight: dict, ranked: list[dict]) -> None:
    """Print the final decision summary at the end of the report."""
    worst = ranked[0]

    print(_divider())
    print("  FINAL DECISION SUMMARY")
    print(_divider())
    print(f"  Portfolio Status: {insight['status_label']}")
    print(f"  Primary Issue: {insight['primary_issue']}")
    print(f"  Secondary Risk: {insight['secondary_risk']}")
    print()
    print("  Key Insight:")
    for line in _wrap(insight["key_insight"], WRAP_WIDTH):
        print(f"  {line}")
    print()
    print("  Action Priority:")
    for index, action in enumerate(insight.get("action_priority", []), 1):
        print(f"  {index}. {action}")
    print()
    print(f"  Highest risk scenario: {worst['name'][:45]}")
    print(f"  Worst-case runway:     {worst['runway']:.1f} months")
    print(_divider())
    print()


def _divider(char: str = "=") -> str:
    """Return a report divider."""
    return char * LINE_WIDTH


def _wrap(text: str, width: int = WRAP_WIDTH) -> list[str]:
    """Word-wrap text to the given width."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _correlation_notes(portfolio: dict, shock_map: dict) -> list[str]:
    """Return category-level correlation notes for affected asset groups."""
    grouped: dict[str, list[str]] = {}
    normalised_shocks = {
        str(name).lower().strip(): float(value)
        for name, value in shock_map.items()
        if isinstance(value, (int, float))
    }

    for asset in portfolio.get("assets", []):
        name = asset.get("name", "")
        category = _asset_category(name)
        if category is None:
            continue
        shock = normalised_shocks.get(str(name).lower().strip(), 0.0)
        if shock == 0:
            continue
        grouped.setdefault(category, []).append(name)

    notes = []
    for category, names in grouped.items():
        if len(names) < 2:
            continue
        names_display = " and ".join(names[:2])
        if len(names) > 2:
            names_display = f"{', '.join(names[:-1])}, and {names[-1]}"
        notes.append(
            f"{names_display} all belong to {category}. This creates "
            "correlated downside risk when that category is stressed."
        )
    return notes


def _asset_category(name: str) -> str | None:
    """Classify common portfolio assets into correlation groups."""
    lower = name.lower().strip()
    if any(token in lower for token in ("btc", "bitcoin", "eth", "ethereum", "doge", "crypto")):
        return "crypto"
    if any(
        token in lower
        for token in (
            "nifty",
            "sensex",
            "reliance",
            "zomato",
            "tata",
            "hdfc",
            "icici",
            "infosys",
            "tcs",
            "indian equity",
        )
    ):
        return "Indian equities"
    if any(
        token in lower
        for token in (
            "tesla",
            "apple",
            "amazon",
            "microsoft",
            "nvidia",
            "meta",
            "google",
            "alphabet",
            "netflix",
        )
    ):
        return "global tech"
    if any(token in lower for token in ("cash", "fd", "savings", "gold", "bond", "gilt")):
        return "defensive assets"
    return None
