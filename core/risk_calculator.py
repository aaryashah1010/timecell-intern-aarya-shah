"""Pure risk-calculation primitives, report builder, and spec-compliant entry point."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

CONCENTRATION_THRESHOLD_PCT: float = 40.0
RUIN_TEST_THRESHOLD_MONTHS: float = 12.0
MODERATE_CRASH_MULTIPLIER: float = 0.5
MIN_CRASH_PCT: float = -100.0


@dataclass(frozen=True)
class Asset:
    name: str
    allocation_pct: float
    expected_crash_pct: float  # signed: -70.0 means a 70% drop


@dataclass(frozen=True)
class AssetResult:
    name: str
    allocation_pct: float
    crash_pct: float
    value: float
    value_after_crash: float
    risk_score: float


@dataclass(frozen=True)
class RiskReport:
    total_value: float
    monthly_expenses: float
    assets: tuple[AssetResult, ...]
    pre_crash_value: float
    post_crash_value: float
    absolute_loss: float
    loss_pct: float
    runway_months: float
    survives_one_year: bool
    largest_risk_asset: str | None
    concentration_warning: bool
    concentrated_assets: tuple[str, ...]
    moderate: bool


def asset_value(total_value: float, allocation_pct: float) -> float:
    return total_value * allocation_pct / 100.0


def asset_value_after_crash(value: float, crash_pct: float) -> float:
    return value * (1.0 + crash_pct / 100.0)


def risk_score(allocation_pct: float, crash_pct: float) -> float:
    return allocation_pct * abs(crash_pct)


def build_report(
    total_value: float,
    monthly_expenses: float,
    assets: Iterable[Asset],
    *,
    moderate: bool = False,
) -> RiskReport:
    assets_t = tuple(assets)
    multiplier = MODERATE_CRASH_MULTIPLIER if moderate else 1.0

    results: list[AssetResult] = []
    for asset in assets_t:
        crash = asset.expected_crash_pct * multiplier
        value = asset_value(total_value, asset.allocation_pct)
        results.append(
            AssetResult(
                name=asset.name,
                allocation_pct=asset.allocation_pct,
                crash_pct=crash,
                value=value,
                value_after_crash=asset_value_after_crash(value, crash),
                risk_score=risk_score(asset.allocation_pct, crash),
            )
        )

    pre_crash_value = sum(r.value for r in results)
    post_crash_value = sum(r.value_after_crash for r in results)
    absolute_loss = pre_crash_value - post_crash_value
    loss_pct = (absolute_loss / pre_crash_value * 100.0) if pre_crash_value > 0 else 0.0

    # monthly_expenses == 0 should be rejected at the CLI, but keep the math
    # safe so build_report stays usable from tests / future call sites.
    if monthly_expenses > 0:
        runway = post_crash_value / monthly_expenses
    else:
        runway = float("inf")

    if not isfinite(runway):
        survives = True
    else:
        survives = runway > RUIN_TEST_THRESHOLD_MONTHS

    risky = [r for r in results if r.risk_score > 0]
    riskiest = max(risky, key=lambda r: r.risk_score, default=None)
    largest_risk_asset = riskiest.name if riskiest else None

    concentrated = tuple(
        r.name for r in results if r.allocation_pct > CONCENTRATION_THRESHOLD_PCT
    )

    return RiskReport(
        total_value=total_value,
        monthly_expenses=monthly_expenses,
        assets=tuple(results),
        pre_crash_value=pre_crash_value,
        post_crash_value=post_crash_value,
        absolute_loss=absolute_loss,
        loss_pct=loss_pct,
        runway_months=runway,
        survives_one_year=survives,
        largest_risk_asset=largest_risk_asset,
        concentration_warning=bool(concentrated),
        concentrated_assets=concentrated,
        moderate=moderate,
    )


def _require_number(value: object, field: str) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    return float(value)


def _assets_from_portfolio(portfolio: dict) -> list[Asset]:
    if not isinstance(portfolio, dict):
        raise ValueError("portfolio must be a dictionary")

    assets_raw = portfolio.get("assets")
    if not isinstance(assets_raw, list) or not assets_raw:
        raise ValueError("portfolio['assets'] must be a non-empty list")

    assets: list[Asset] = []
    for i, raw in enumerate(assets_raw):
        if not isinstance(raw, dict):
            raise ValueError(f"asset {i} must be a dictionary")

        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"asset {i} name must be a non-empty string")

        allocation_pct = _require_number(raw.get("allocation_pct"), f"asset {i} allocation_pct")
        expected_crash_pct = _require_number(
            raw.get("expected_crash_pct"), f"asset {i} expected_crash_pct"
        )

        if allocation_pct < 0:
            raise ValueError(f"asset {i} allocation_pct cannot be negative")
        if expected_crash_pct < MIN_CRASH_PCT:
            raise ValueError(f"asset {i} expected_crash_pct cannot be below -100")

        assets.append(
            Asset(
                name=name.strip(),
                allocation_pct=allocation_pct,
                expected_crash_pct=expected_crash_pct,
            )
        )
    return assets


def compute_risk_metrics(portfolio: dict, *, moderate: bool = False) -> dict:
    """Return the five Task 01 risk metrics for a portfolio dictionary."""
    if not isinstance(portfolio, dict):
        raise ValueError("portfolio must be a dictionary")

    total_value = _require_number(portfolio.get("total_value_inr"), "total_value_inr")
    monthly_expenses = _require_number(
        portfolio.get("monthly_expenses_inr"), "monthly_expenses_inr"
    )
    if total_value < 0:
        raise ValueError("total_value_inr cannot be negative")
    if monthly_expenses < 0:
        raise ValueError("monthly_expenses_inr cannot be negative")

    assets = _assets_from_portfolio(portfolio)
    report = build_report(
        total_value=total_value,
        monthly_expenses=monthly_expenses,
        assets=assets,
        moderate=moderate,
    )
    return {
        "post_crash_value": report.post_crash_value,
        "runway_months": report.runway_months,
        "ruin_test": "PASS" if report.survives_one_year else "FAIL",
        "largest_risk_asset": report.largest_risk_asset,
        "concentration_warning": report.concentration_warning,
    }
