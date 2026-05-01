"""Deterministic math engine for crash-scenario computation.

Task 4 relies entirely on ChatGPT's scenario-specific ``shock_map`` values.
This module does not import ``config.crash_assumptions``. If ChatGPT misses an
asset, the engine assumes a 0% move and prints a warning.
"""

from __future__ import annotations

import copy

from core.risk_calculator import compute_risk_metrics

MISSING_ASSET_ASSUMPTION_PCT: float = 0.0
CONCENTRATION_THRESHOLD_PCT: float = 35.0


def apply_scenario_shocks(portfolio: dict, shock_map: dict) -> dict:
    """Return a deep-copied portfolio with scenario shocks applied per asset."""
    modified = copy.deepcopy(portfolio)
    normalised_shocks = _normalise_shock_map(shock_map)

    for asset in modified["assets"]:
        name_lower = asset["name"].lower().strip()
        if name_lower in normalised_shocks:
            asset["expected_crash_pct"] = float(normalised_shocks[name_lower])
        else:
            print(
                f"  [WARNING] '{asset['name']}' not found in shock_map. "
                f"Assuming {MISSING_ASSET_ASSUMPTION_PCT}% (unaffected)."
            )
            asset["expected_crash_pct"] = MISSING_ASSET_ASSUMPTION_PCT

    return modified


def compute_scenario_result(portfolio: dict, shock_map: dict) -> dict:
    """Apply a scenario shock map and return Task 1 risk metrics."""
    modified = apply_scenario_shocks(portfolio, shock_map)
    return compute_risk_metrics(modified)


def compute_why_this_breaks(
    portfolio: dict,
    shock_map: dict,
    metrics: dict,
) -> dict:
    """Identify the largest asset-level loss contribution for the report."""
    total_value = portfolio["total_value_inr"]
    pre_crash_value = metrics.get("pre_crash_value", total_value)
    post_crash_value = metrics["post_crash_value"]
    normalised_shocks = _normalise_shock_map(shock_map)

    breakdown = []
    for asset in portfolio["assets"]:
        name = asset["name"]
        allocation_pct = asset["allocation_pct"]
        shock_pct = float(
            normalised_shocks.get(name.lower().strip(), MISSING_ASSET_ASSUMPTION_PCT)
        )
        asset_value = total_value * (allocation_pct / 100.0)
        impact_inr = asset_value * (shock_pct / 100.0)
        loss_inr = max(-impact_inr, 0.0)

        breakdown.append(
            {
                "name": name,
                "allocation_pct": allocation_pct,
                "shock_pct": shock_pct,
                "asset_value_inr": asset_value,
                "impact_inr": impact_inr,
                "loss_inr": loss_inr,
            }
        )

    gross_loss_inr = sum(item["loss_inr"] for item in breakdown)
    total_loss_inr = pre_crash_value - post_crash_value
    total_loss_pct = (
        (total_loss_inr / pre_crash_value * 100.0) if pre_crash_value else 0.0
    )

    for item in breakdown:
        item["pct_of_total_loss"] = (
            (item["loss_inr"] / gross_loss_inr * 100.0) if gross_loss_inr > 0 else 0.0
        )

    breakdown_sorted = sorted(breakdown, key=lambda item: item["loss_inr"], reverse=True)
    largest = breakdown_sorted[0] if breakdown_sorted else {}

    return {
        "largest_loss_asset": largest.get("name", "None"),
        "largest_loss_pct_of_total": largest.get("pct_of_total_loss", 0.0),
        "concentration_culprit": (
            largest.get("allocation_pct", 0.0) > CONCENTRATION_THRESHOLD_PCT
        ),
        "total_loss_inr": total_loss_inr,
        "total_loss_pct": total_loss_pct,
        "gross_loss_inr": gross_loss_inr,
        "loss_breakdown": breakdown_sorted,
    }


def _normalise_shock_map(shock_map: dict) -> dict[str, float]:
    """Normalise shock-map keys for case-insensitive asset matching."""
    return {str(key).lower().strip(): value for key, value in shock_map.items()}
