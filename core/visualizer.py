"""ASCII rendering for a RiskReport using Windows-safe plain characters."""

from __future__ import annotations

from math import isfinite

from .risk_calculator import RiskReport

REPORT_WIDTH = 64
BAR_WIDTH = 24


def fmt_inr(value: float) -> str:
    """Format an integer rupee amount with Indian-style grouping (e.g. 12,34,567)."""
    sign = "-" if value < 0 else ""
    n = abs(int(round(value)))
    s = str(n)
    if len(s) <= 3:
        return f"INR {sign}{s}"
    last3, rest = s[-3:], s[:-3]
    groups: list[str] = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return f"INR {sign}{','.join(groups)},{last3}"


def bar(value: float, max_value: float, width: int = BAR_WIDTH) -> str:
    if max_value <= 0:
        return "." * width
    ratio = max(0.0, min(1.0, value / max_value))
    filled = int(round(width * ratio))
    return "#" * filled + "." * (width - filled)


def render_report(report: RiskReport) -> str:
    out: list[str] = []
    title = " RISK REPORT (moderate scenario) " if report.moderate else " RISK REPORT (severe scenario) "
    out.append("=" * REPORT_WIDTH)
    out.append(title.center(REPORT_WIDTH, "="))
    out.append("=" * REPORT_WIDTH)
    out.append("")

    out.append(f"Portfolio total : {fmt_inr(report.total_value)}")
    out.append(f"Monthly expense : {fmt_inr(report.monthly_expenses)}")
    out.append("")

    name_w = max((len(r.name) for r in report.assets), default=8)
    name_w = max(name_w, 8)

    out.append("ALLOCATION")
    for r in report.assets:
        out.append(
            f"  {r.name.ljust(name_w)}  [{bar(r.allocation_pct, 100)}] {r.allocation_pct:6.2f}%"
        )
    out.append("")

    out.append("CRASH IMPACT (per asset)")
    for r in report.assets:
        loss = r.value - r.value_after_crash
        out.append(
            f"  {r.name.ljust(name_w)}  {fmt_inr(r.value)} -> {fmt_inr(r.value_after_crash)}"
            f"   crash {r.crash_pct:+5.1f}%   loss {fmt_inr(loss)}"
        )
    out.append("")

    out.append("PORTFOLIO POST-CRASH")
    out.append(f"  Pre-crash value  : {fmt_inr(report.pre_crash_value)}")
    out.append(f"  Post-crash value : {fmt_inr(report.post_crash_value)}")
    out.append(f"  Absolute loss    : {fmt_inr(report.absolute_loss)}")
    out.append(f"  Loss percentage  : {report.loss_pct:6.2f}%")
    out.append("")

    out.append("RUNWAY")
    if not isfinite(report.runway_months):
        out.append("  Months survived  : infinite (no monthly expenses)")
    else:
        out.append(f"  Months survived  : {report.runway_months:6.1f}")
    verdict = "PASS" if report.survives_one_year else "FAIL"
    out.append(f"  Ruin test (>12)  : [{verdict}]")
    out.append("")

    out.append("RISK FLAGS")
    if report.largest_risk_asset:
        riskiest = next(r for r in report.assets if r.name == report.largest_risk_asset)
        out.append(
            f"  Largest risk     : {riskiest.name} "
            f"(alloc {riskiest.allocation_pct:.1f}% x crash {abs(riskiest.crash_pct):.1f}% "
            f"= score {riskiest.risk_score:.0f})"
        )
    else:
        out.append("  Largest risk     : none (no crash exposure)")

    if report.concentration_warning:
        names = ", ".join(report.concentrated_assets)
        out.append(f"  Concentration    : WARN -- over 40% in: {names}")
    else:
        out.append("  Concentration    : OK (no asset over 40%)")

    out.append("")
    out.append("=" * REPORT_WIDTH)
    return "\n".join(out)
