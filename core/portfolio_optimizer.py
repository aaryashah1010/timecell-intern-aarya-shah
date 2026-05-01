"""Rule-based portfolio strategy optimizer for Task 4.

Pipeline:
    detect_strategy(portfolio, metrics) -> str
    suggest_portfolio(portfolio, target_strategy) -> dict
    compare_portfolios(current, suggested) -> dict
    generate_impact_summary(current_metrics, suggested_metrics) -> dict

`compute_risk_metrics` from Task 1 is the single source of truth for risk
numbers — this module never recomputes them. AI is *not* involved in
generating allocations; the optional `generate_ai_verdict` only narrates
the rule-based comparison.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass

from core.ai_explainer import DEFAULT_MODEL, call_openai
from core.risk_calculator import compute_risk_metrics

log = logging.getLogger("timecell.optimizer")

STRATEGIES: tuple[str, ...] = ("Conservative", "Balanced", "Aggressive")

# Defensive assets are the only assets that can absorb redistribution from
# capped risky positions.
DEFENSIVE_ASSETS: frozenset[str] = frozenset({"Cash", "Bonds", "Gold"})

# Default crash assumptions used when a defensive asset must be added to a
# portfolio that didn't already include it.
SAFE_ASSET_CRASH_PCT: dict[str, float] = {
    "Cash":  0.0,
    "Bonds": -10.0,
    "Gold":  -15.0,
}


# ---------- canonical asset names ----------

# All keys here are lowercase / case-folded. The lookup canonicalises
# casing AND aliases (`bitcoin` -> `BTC`, `nifty50` -> `Equity`, etc.).
_CANONICAL_NAMES: dict[str, str] = {
    "btc": "BTC", "bitcoin": "BTC",
    "eth": "ETH", "ethereum": "ETH",
    "crypto": "Crypto",
    "nifty": "Equity", "nifty50": "Equity",
    "sensex": "Equity", "stocks": "Equity", "equity": "Equity",
    "mutual fund": "Mutual Funds", "mutual funds": "Mutual Funds", "etf": "Mutual Funds",
    "real estate": "Real Estate", "reit": "Real Estate",
    "silver": "Silver",
    "gold": "Gold",
    "bonds": "Bonds", "bond": "Bonds",
    "cash": "Cash", "fd": "Cash", "savings": "Cash",
}


def normalize_asset_name(name: str) -> str:
    """Map any user-typed asset name (any case, any alias) to its canonical form.

    Examples:
        normalize_asset_name("bonds")     -> "Bonds"
        normalize_asset_name("Bonds")     -> "Bonds"
        normalize_asset_name("ETHEREUM")  -> "ETH"
        normalize_asset_name("nifty50")   -> "Equity"
        normalize_asset_name("Gold ")     -> "Gold"
        normalize_asset_name("Pepsi")     -> "Pepsi"   (unknown — title-cased)
    """
    if not name:
        return ""
    key = " ".join(name.strip().casefold().split())
    if key in _CANONICAL_NAMES:
        return _CANONICAL_NAMES[key]
    # Unknown asset: keep the user's casing if it has any uppercase, otherwise title-case.
    stripped = name.strip()
    return stripped if any(c.isupper() for c in stripped) else stripped.title()


# ---------- strategy rules ----------

@dataclass(frozen=True)
class StrategyRules:
    """Per-strategy caps and redistribution preferences."""

    name: str
    risky_cap: float                # max allocation for any non-defensive asset
    min_defensive_allocation: float  # minimum combined Cash/Bonds/Gold allocation
    redistribute_order: tuple[str, ...]  # defensive assets receive excess in this order
    safe_caps: dict[str, float]     # max allocation per defensive asset


TARGET_RULES: dict[str, StrategyRules] = {
    "Conservative": StrategyRules(
        name="Conservative",
        risky_cap=25.0,
        min_defensive_allocation=60.0,
        redistribute_order=("Cash", "Bonds", "Gold"),
        safe_caps={"Cash": 30.0, "Bonds": 35.0, "Gold": 20.0},
    ),
    "Balanced": StrategyRules(
        name="Balanced",
        risky_cap=35.0,
        min_defensive_allocation=40.0,
        redistribute_order=("Bonds", "Cash", "Gold"),
        safe_caps={"Bonds": 25.0, "Cash": 25.0, "Gold": 15.0},
    ),
    "Aggressive": StrategyRules(
        name="Aggressive",
        risky_cap=50.0,
        min_defensive_allocation=0.0,
        redistribute_order=("Gold", "Cash"),
        safe_caps={"Gold": 15.0, "Cash": 15.0, "Bonds": 30.0},
    ),
}


# ---------- public API ----------

def detect_strategy(portfolio: dict, metrics: dict) -> str:
    """Classify the *current* portfolio into one of STRATEGIES from Task 1 metrics.

    `metrics` is the dict returned by core.risk_calculator.compute_risk_metrics().
    `loss_pct` is derived from post_crash_value because the spec metrics
    dict doesn't surface it directly.
    """
    loss_pct = _loss_pct(portfolio, metrics)
    runway = float(metrics["runway_months"])
    concentrated = bool(metrics["concentration_warning"])

    if loss_pct > 40.0 or runway < 12.0 or concentrated:
        strategy = "Aggressive"
    elif loss_pct < 20.0 and runway >= 24.0 and not concentrated:
        strategy = "Conservative"
    else:
        strategy = "Balanced"

    log.info(
        "detected strategy=%s loss=%.1f%% runway=%.1f concentration=%s",
        strategy, loss_pct, runway, concentrated,
    )
    return strategy


def suggest_portfolio(portfolio: dict, target_strategy: str) -> dict:
    """Return a deterministic suggested portfolio for the requested strategy.

    Steps (all rule-based, no AI):
      1. Canonicalise asset names so duplicates collapse.
      2. Cap each asset to its strategy cap; collect the excess.
      3. Redistribute the excess into defensive assets in priority order.
      4. Drop zero-allocation entries; renormalise to exactly 100%.
    """
    if target_strategy not in TARGET_RULES:
        raise ValueError(
            f"target_strategy must be one of {STRATEGIES}, got {target_strategy!r}"
        )

    if not portfolio.get("assets"):
        raise ValueError("portfolio['assets'] must be a non-empty list")

    suggested = copy.deepcopy(portfolio)
    assets: list[dict] = suggested["assets"]
    rules = TARGET_RULES[target_strategy]

    _canonicalise_and_merge(assets)
    excess = _cap_assets(assets, rules)
    if excess > 1e-9:
        _redistribute_excess(assets, excess, rules)
    defensive_excess = _enforce_min_defensive_allocation(assets, rules)
    if defensive_excess > 1e-9:
        _redistribute_excess(assets, defensive_excess, rules)
    _drop_zero_allocations(assets)
    _normalise_to_100(assets)

    log.info(
        "suggested portfolio target=%s assets=%d", target_strategy, len(assets),
    )
    return suggested


def compare_portfolios(current_portfolio: dict, suggested_portfolio: dict) -> dict:
    """Compute Task 1 metrics for both portfolios and the per-asset deltas."""
    return {
        "current_metrics":   _extended_metrics(current_portfolio),
        "suggested_metrics": _extended_metrics(suggested_portfolio),
        "allocation_changes": build_allocation_changes(
            current_portfolio, suggested_portfolio
        ),
    }


def build_allocation_changes(
    current_portfolio: dict, suggested_portfolio: dict
) -> list[dict]:
    """Per-asset deltas using canonical names so `bonds` and `Bonds` collapse to one row."""
    current_map = _allocation_map(current_portfolio["assets"])
    suggested_map = _allocation_map(suggested_portfolio["assets"])

    # Order: assets in the original portfolio first (preserves user mental model),
    # then any newly added defensive assets.
    seen: list[str] = []
    seen_set: set[str] = set()
    for asset in current_portfolio["assets"]:
        canon = normalize_asset_name(str(asset["name"]))
        if canon and canon not in seen_set:
            seen.append(canon)
            seen_set.add(canon)
    for asset in suggested_portfolio["assets"]:
        canon = normalize_asset_name(str(asset["name"]))
        if canon and canon not in seen_set:
            seen.append(canon)
            seen_set.add(canon)

    changes: list[dict] = []
    for name in seen:
        before = current_map.get(name, 0.0)
        after = suggested_map.get(name, 0.0)
        if abs(before - after) > 1e-6:
            changes.append({
                "name": name,
                "current_allocation_pct": before,
                "suggested_allocation_pct": after,
                "delta_pct": after - before,
            })
    return changes


def generate_impact_summary(current_metrics: dict, suggested_metrics: dict) -> dict:
    """Compare extended metrics dicts and return a structured impact summary.

    Each `current_metrics` / `suggested_metrics` is the result of
    `compute_risk_metrics()` augmented with `loss_pct` (see _extended_metrics).
    """
    cur_loss = float(current_metrics["loss_pct"])
    sug_loss = float(suggested_metrics["loss_pct"])
    cur_runway = float(current_metrics["runway_months"])
    sug_runway = float(suggested_metrics["runway_months"])
    cur_conc = bool(current_metrics["concentration_warning"])
    sug_conc = bool(suggested_metrics["concentration_warning"])
    cur_ruin = str(current_metrics["ruin_test"])
    sug_ruin = str(suggested_metrics["ruin_test"])

    # ------- per-metric labels -------
    if sug_loss < cur_loss - 0.05:
        loss_label = "better"
    elif sug_loss > cur_loss + 0.05:
        loss_label = "worse"
    else:
        loss_label = "no change"

    if sug_runway > cur_runway + 0.05:
        runway_label = "still low" if sug_runway < 12.0 else "improved"
    elif sug_runway < cur_runway - 0.05:
        runway_label = "worse"
    else:
        runway_label = "no change"

    if cur_conc and not sug_conc:
        conc_label = "fixed"
    elif not cur_conc and sug_conc:
        conc_label = "introduced"
    elif cur_conc and sug_conc:
        conc_label = "still present"
    else:
        conc_label = "OK both"

    if cur_ruin == "FAIL" and sug_ruin == "PASS":
        ruin_label = "now safe"
    elif cur_ruin == "PASS" and sug_ruin == "FAIL":
        ruin_label = "regressed"
    elif cur_ruin == "FAIL" and sug_ruin == "FAIL":
        ruin_label = "still unsafe"
    else:
        ruin_label = "still safe"

    # ------- overall verdict -------
    metric_better = (
        sug_loss < cur_loss - 0.05
        or sug_runway > cur_runway + 0.05
        or (cur_conc and not sug_conc)
        or (cur_ruin == "FAIL" and sug_ruin == "PASS")
    )
    metric_worse = (
        sug_loss > cur_loss + 0.05
        or sug_runway < cur_runway - 0.05
        or (not cur_conc and sug_conc)
        or (cur_ruin == "PASS" and sug_ruin == "FAIL")
    )

    if metric_worse and not metric_better:
        result = "Worse / needs review"
    elif not metric_better:
        result = "No meaningful improvement"
    elif sug_ruin == "PASS" and not sug_conc:
        result = "Improved and safer"
    else:
        result = "Improved but still unsafe"

    return {
        "loss_pct":              {"current": cur_loss,    "suggested": sug_loss,    "label": loss_label},
        "runway_months":         {"current": cur_runway,  "suggested": sug_runway,  "label": runway_label},
        "concentration_warning": {"current": cur_conc,    "suggested": sug_conc,    "label": conc_label},
        "ruin_test":             {"current": cur_ruin,    "suggested": sug_ruin,    "label": ruin_label},
        "result":                result,
    }


# ---------- AI verdict (optional, narration only) ----------

_AI_VERDICT_SYSTEM = (
    "You are a financial advisor explaining a rule-based portfolio improvement "
    "to a non-expert investor in India.\n\n"
    "Rules you must follow:\n"
    "- Do not invent allocation numbers.\n"
    "- Do not suggest a new portfolio of your own.\n"
    "- Only explain the comparison already computed.\n"
    "- If the suggested portfolio still fails the ruin test, clearly say it is "
    "improved but not yet safe.\n"
    "- Keep the response to 2-4 sentences. Use INR for money. Be honest about tradeoffs."
)


def build_ai_verdict_prompt(
    *,
    current_strategy: str,
    target_strategy: str,
    comparison: dict,
    impact: dict,
) -> str:
    cur = comparison["current_metrics"]
    sug = comparison["suggested_metrics"]
    changes = comparison["allocation_changes"]
    return "\n".join([
        f"Current strategy: {current_strategy}",
        f"Target strategy:  {target_strategy}",
        "",
        "Current metrics:",
        f"- Post-crash value: INR {cur['post_crash_value']:,.0f}",
        f"- Loss: {cur['loss_pct']:.1f}%",
        f"- Runway: {cur['runway_months']:.1f} months",
        f"- Ruin test: {cur['ruin_test']}",
        f"- Largest risk asset: {cur.get('largest_risk_asset') or 'None'}",
        f"- Concentration warning: {'YES' if cur['concentration_warning'] else 'NO'}",
        "",
        "Suggested metrics:",
        f"- Post-crash value: INR {sug['post_crash_value']:,.0f}",
        f"- Loss: {sug['loss_pct']:.1f}%",
        f"- Runway: {sug['runway_months']:.1f} months",
        f"- Ruin test: {sug['ruin_test']}",
        f"- Largest risk asset: {sug.get('largest_risk_asset') or 'None'}",
        f"- Concentration warning: {'YES' if sug['concentration_warning'] else 'NO'}",
        "",
        "Allocation changes:",
        _format_changes_for_prompt(changes),
        "",
        f"Impact summary result: {impact['result']}",
        "",
        "Write a 2-4 sentence verdict using the numbers above. Explain why the "
        "suggested strategy is better, what tradeoff the user is making, and "
        "whether it is still unsafe.",
    ])


def generate_ai_verdict(
    *,
    current_strategy: str,
    target_strategy: str,
    comparison: dict,
    impact: dict,
    model: str = DEFAULT_MODEL,
) -> str:
    """Ask the LLM to *explain* (not generate) the rule-based comparison."""
    user_prompt = build_ai_verdict_prompt(
        current_strategy=current_strategy,
        target_strategy=target_strategy,
        comparison=comparison,
        impact=impact,
    )
    log.info("task4 ai verdict started model=%s", model)
    verdict = call_openai(
        _AI_VERDICT_SYSTEM,
        user_prompt,
        model=model,
        temperature=0.2,
        json_response=False,
    ).strip()
    log.info("task4 ai verdict completed chars=%d", len(verdict))
    return verdict


# ---------- internals ----------

def _extended_metrics(portfolio: dict) -> dict:
    """Task 1 metrics + derived loss_pct, ready for impact comparison."""
    metrics = compute_risk_metrics(portfolio)
    total = float(portfolio["total_value_inr"])
    metrics["loss_pct"] = (
        (1.0 - float(metrics["post_crash_value"]) / total) * 100.0 if total > 0 else 0.0
    )
    return metrics


def _loss_pct(portfolio: dict, metrics: dict) -> float:
    total = float(portfolio["total_value_inr"])
    if total <= 0:
        return 0.0
    return (1.0 - float(metrics["post_crash_value"]) / total) * 100.0


def _canonicalise_and_merge(assets: list[dict]) -> None:
    """Rewrite each asset's name to its canonical form and collapse duplicates.

    This is what fixes the `bonds`/`Bonds` duplicate row bug — every asset
    downstream sees a single canonical key.
    """
    merged: dict[str, dict] = {}
    order: list[str] = []
    for asset in assets:
        canon = normalize_asset_name(str(asset["name"]))
        if canon not in merged:
            merged[canon] = {
                "name": canon,
                "allocation_pct": float(asset["allocation_pct"]),
                "expected_crash_pct": float(asset["expected_crash_pct"]),
            }
            order.append(canon)
        else:
            merged[canon]["allocation_pct"] += float(asset["allocation_pct"])
    assets[:] = [merged[k] for k in order]


def _cap_for_asset(asset: dict, rules: StrategyRules) -> float:
    """Return the max allocation this asset is allowed under the strategy."""
    canon = normalize_asset_name(str(asset["name"]))
    if canon in rules.safe_caps:
        return rules.safe_caps[canon]
    return rules.risky_cap


def _cap_assets(assets: list[dict], rules: StrategyRules) -> float:
    """Trim each over-cap asset to its cap; return the total trimmed amount."""
    excess = 0.0
    for asset in assets:
        allocation = float(asset["allocation_pct"])
        cap = _cap_for_asset(asset, rules)
        if allocation > cap + 1e-9:
            reduction = allocation - cap
            asset["allocation_pct"] = cap
            excess += reduction
            log.info(
                "capped %s from %.2f%% to %.2f%% (excess=%.2f%%)",
                asset["name"], allocation, cap, reduction,
            )
    return excess


def _enforce_min_defensive_allocation(assets: list[dict], rules: StrategyRules) -> float:
    """Trim non-defensive exposure until the strategy's defensive target is met."""
    if rules.min_defensive_allocation <= 0:
        return 0.0

    defensive_total = sum(
        float(a["allocation_pct"])
        for a in assets
        if normalize_asset_name(str(a["name"])) in DEFENSIVE_ASSETS
    )
    required = rules.min_defensive_allocation - defensive_total
    if required <= 1e-9:
        return 0.0

    risky_assets = [
        a for a in assets
        if normalize_asset_name(str(a["name"])) not in DEFENSIVE_ASSETS
        and float(a["allocation_pct"]) > 0
    ]
    risky_total = sum(float(a["allocation_pct"]) for a in risky_assets)
    if risky_total <= 0:
        return 0.0

    reduction = min(required, risky_total)
    scale = (risky_total - reduction) / risky_total
    excess = 0.0
    for asset in risky_assets:
        before = float(asset["allocation_pct"])
        after = round(before * scale, 6)
        asset["allocation_pct"] = after
        excess += before - after
        log.info(
            "reduced %s from %.2f%% to %.2f%% for defensive target",
            asset["name"], before, after,
        )
    return excess


def _redistribute_excess(
    assets: list[dict], excess: float, rules: StrategyRules,
) -> None:
    """Push the excess into defensive assets in priority order, up to each cap.

    If safe-asset caps cannot absorb all of the excess, the remainder goes
    to the lowest-crash asset already in the portfolio (last-resort fallback).
    """
    remaining = excess
    for safe_name in rules.redistribute_order:
        if remaining <= 1e-9:
            break
        asset = _get_or_add_asset(assets, safe_name)
        cap = rules.safe_caps.get(safe_name, rules.risky_cap)
        room = max(0.0, cap - float(asset["allocation_pct"]))
        added = min(room, remaining)
        if added > 0:
            asset["allocation_pct"] = float(asset["allocation_pct"]) + added
            remaining -= added
            log.info("redistributed +%.2f%% to %s", added, safe_name)

    if remaining > 1e-6:
        # Caps full — give the rest to the safest existing asset.
        fallback = min(
            assets,
            key=lambda a: (abs(float(a["expected_crash_pct"])), a["name"]),
        )
        fallback["allocation_pct"] = float(fallback["allocation_pct"]) + remaining
        log.info(
            "redistributed fallback +%.2f%% to %s after caps filled",
            remaining, fallback["name"],
        )


def _get_or_add_asset(assets: list[dict], canonical_name: str) -> dict:
    """Find a defensive asset by canonical name; add it (zero allocation) if missing."""
    for asset in assets:
        if normalize_asset_name(str(asset["name"])) == canonical_name:
            asset["name"] = canonical_name  # always carry canonical casing forward
            return asset
    new_asset = {
        "name": canonical_name,
        "allocation_pct": 0.0,
        "expected_crash_pct": SAFE_ASSET_CRASH_PCT.get(canonical_name, 0.0),
    }
    assets.append(new_asset)
    return new_asset


def _drop_zero_allocations(assets: list[dict]) -> None:
    assets[:] = [a for a in assets if float(a["allocation_pct"]) > 1e-9]


def _normalise_to_100(assets: list[dict]) -> None:
    total = sum(float(a["allocation_pct"]) for a in assets)
    if total <= 0:
        raise ValueError("portfolio allocation total must be positive after suggestion")
    for asset in assets:
        asset["allocation_pct"] = round(float(asset["allocation_pct"]) * 100.0 / total, 6)
    drift = round(100.0 - sum(float(a["allocation_pct"]) for a in assets), 6)
    if abs(drift) > 0:
        largest = max(assets, key=lambda a: float(a["allocation_pct"]))
        largest["allocation_pct"] = round(float(largest["allocation_pct"]) + drift, 6)


def _allocation_map(assets: list[dict]) -> dict[str, float]:
    """Map canonical name -> total allocation. Collapses duplicate-cased entries."""
    allocations: dict[str, float] = {}
    for asset in assets:
        name = normalize_asset_name(str(asset["name"]))
        if not name:
            continue
        allocations[name] = allocations.get(name, 0.0) + float(asset["allocation_pct"])
    return allocations


def _format_changes_for_prompt(changes: list[dict]) -> str:
    if not changes:
        return "- No allocation changes."
    return "\n".join(
        f"- {c['name']}: {c['current_allocation_pct']:.1f}% -> "
        f"{c['suggested_allocation_pct']:.1f}%"
        for c in changes
    )
