"""Shared numeric thresholds used across Task 4 modules.

Centralised so a change to the survival rule or the concentration cutoff
takes effect everywhere instead of drifting between files.
"""

from __future__ import annotations

RUNWAY_THRESHOLD_MONTHS: float = 12.0

CONCENTRATION_THRESHOLD_PCT: float = 35.0

CONCENTRATION_ALERT_PCT: float = 35.0
