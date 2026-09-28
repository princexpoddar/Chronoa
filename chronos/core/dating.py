"""
CHRONOS Observability-Bounded Change Dating.

Estimates the change date interval (t⁻, t⁺, G) for confirmed changes:

    t⁻ = max { t < t† : q_i(t) ≥ q_min  ∧  p_i(t) > α_loose }
        — last clean null observation before change

    t⁺ = min { t ≤ t† : q_i(t) ≥ q_min  ∧  p_i(t) ≤ α_loose }
        — first usable confirmation observation

    G  = { t ∈ (t⁻, t⁺) : q_i(t) < q_min }
        — gap: unusable observations (cloud, haze, sensor dropout)

The interval [t⁻, t⁺] honestly bounds how precisely the system can date
the change given observability constraints. SAR (Sentinel-1) observations
are cloud-immune and can narrow the interval when optical observations are
blocked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_ALPHA_LOOSE = 0.20    # Loose p-value threshold for dating
DEFAULT_Q_MIN = 0.2           # Minimum quality weight


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DatingObservation:
    """A single observation record relevant for change dating."""
    timestamp: datetime
    quality_weight: float
    pvalue: float
    is_sar: bool = False       # Whether this is a SAR (cloud-immune) observation
    sensor: str = "unknown"


@dataclass
class ChangeDateResult:
    """
    Observability-bounded change date estimate.
    """
    tile_id: str
    t_minus: Optional[datetime] = None
    t_plus: Optional[datetime] = None
    gap_timestamps: list[datetime] = field(default_factory=list)
    gap_days: float = 0.0
    interval_days: float = 0.0
    sar_narrowed: bool = False
    n_usable_before: int = 0
    n_usable_after: int = 0
    n_gap: int = 0
    confidence_note: str = ""


# ---------------------------------------------------------------------------
# Change dating algorithm
# ---------------------------------------------------------------------------

def estimate_change_date(
    tile_id: str,
    observations: list[DatingObservation],
    confirmation_step: Optional[int] = None,
    alpha_loose: float = DEFAULT_ALPHA_LOOSE,
    q_min: float = DEFAULT_Q_MIN,
) -> ChangeDateResult:
    """
    Estimate the observability-bounded change date interval.

    Parameters
    ----------
    tile_id : str
        Tile identifier.
    observations : list[DatingObservation]
        Time-ordered observations with quality weights and p-values.
    confirmation_step : int, optional
        Index of the observation at which the e-process confirmed change.
        If None, uses the first observation with p ≤ α_loose.
    alpha_loose : float
        Loose p-value threshold for identifying significant departures.
    q_min : float
        Minimum quality weight for an observation to be considered usable.

    Returns
    -------
    ChangeDateResult
        The (t⁻, t⁺, G) estimate with metadata.
    """
    if not observations:
        return ChangeDateResult(tile_id=tile_id, confidence_note="No observations")

    # Sort by timestamp
    obs_sorted = sorted(observations, key=lambda o: o.timestamp)
    n = len(obs_sorted)

    # Determine confirmation point t†
    if confirmation_step is not None and 0 <= confirmation_step < n:
        t_dagger_idx = confirmation_step
    else:
        # Find first observation with p ≤ α_loose and sufficient quality
        t_dagger_idx = None
        for i, obs in enumerate(obs_sorted):
            if obs.quality_weight >= q_min and obs.pvalue <= alpha_loose:
                t_dagger_idx = i
                break
        if t_dagger_idx is None:
            return ChangeDateResult(
                tile_id=tile_id,
                confidence_note="No observation below α_loose threshold"
            )

    # --- Find t⁺: first usable confirmation at or before t† ---
    t_plus = None
    t_plus_idx = None
    for i in range(t_dagger_idx, -1, -1):
        obs = obs_sorted[i]
        if obs.quality_weight >= q_min and obs.pvalue <= alpha_loose:
            t_plus = obs.timestamp
            t_plus_idx = i
            break

    # If we didn't find it scanning backwards, take the confirmation point itself
    if t_plus is None:
        t_plus = obs_sorted[t_dagger_idx].timestamp
        t_plus_idx = t_dagger_idx

    # Also check forward from t_dagger for the earliest confirmation
    for i in range(0, n):
        obs = obs_sorted[i]
        if obs.quality_weight >= q_min and obs.pvalue <= alpha_loose:
            if t_plus is None or obs.timestamp < t_plus:
                t_plus = obs.timestamp
                t_plus_idx = i
            break

    # --- Find t⁻: last clean null observation before t⁺ ---
    t_minus = None
    t_minus_idx = None
    if t_plus_idx is not None:
        for i in range(t_plus_idx - 1, -1, -1):
            obs = obs_sorted[i]
            if obs.quality_weight >= q_min and obs.pvalue > alpha_loose:
                t_minus = obs.timestamp
                t_minus_idx = i
                break

    # --- Enumerate gap G ---
    gap_timestamps = []
    if t_minus_idx is not None and t_plus_idx is not None:
        for i in range(t_minus_idx + 1, t_plus_idx):
            obs = obs_sorted[i]
            if obs.quality_weight < q_min:
                gap_timestamps.append(obs.timestamp)

    # --- Compute interval metrics ---
    interval_days = 0.0
    gap_days = 0.0
    if t_minus is not None and t_plus is not None:
        interval_days = (t_plus - t_minus).total_seconds() / 86400.0

    if len(gap_timestamps) >= 2:
        gap_days = (max(gap_timestamps) - min(gap_timestamps)).total_seconds() / 86400.0
    elif len(gap_timestamps) == 1 and t_minus is not None and t_plus is not None:
        gap_days = interval_days  # Single gap observation, full interval is gap

    # --- Count usable observations ---
    n_usable_before = 0
    n_usable_after = 0
    if t_plus_idx is not None:
        for i in range(t_plus_idx):
            if obs_sorted[i].quality_weight >= q_min:
                n_usable_before += 1
        for i in range(t_plus_idx, n):
            if obs_sorted[i].quality_weight >= q_min:
                n_usable_after += 1

    # --- SAR narrowing check ---
    sar_narrowed = False
    if t_minus is not None and t_plus is not None:
        # Check if any SAR observations in (t⁻, t⁺) could narrow the interval
        sar_in_gap = [
            obs for obs in obs_sorted
            if obs.is_sar
            and obs.quality_weight >= q_min
            and t_minus < obs.timestamp < t_plus
        ]
        if sar_in_gap:
            # SAR can refine: check if any SAR shows null or change
            for sar_obs in sar_in_gap:
                if sar_obs.pvalue > alpha_loose:
                    # SAR shows null — push t⁻ forward
                    if t_minus is None or sar_obs.timestamp > t_minus:
                        t_minus = sar_obs.timestamp
                        sar_narrowed = True
                elif sar_obs.pvalue <= alpha_loose:
                    # SAR shows change — pull t⁺ back
                    if t_plus is None or sar_obs.timestamp < t_plus:
                        t_plus = sar_obs.timestamp
                        sar_narrowed = True

            if sar_narrowed and t_minus is not None and t_plus is not None:
                interval_days = (t_plus - t_minus).total_seconds() / 86400.0

    # --- Confidence note ---
    confidence_note = _build_confidence_note(
        interval_days, n_usable_before, n_usable_after, len(gap_timestamps), sar_narrowed
    )

    return ChangeDateResult(
        tile_id=tile_id,
        t_minus=t_minus,
        t_plus=t_plus,
        gap_timestamps=gap_timestamps,
        gap_days=gap_days,
        interval_days=interval_days,
        sar_narrowed=sar_narrowed,
        n_usable_before=n_usable_before,
        n_usable_after=n_usable_after,
        n_gap=len(gap_timestamps),
        confidence_note=confidence_note,
    )


def _build_confidence_note(
    interval_days: float,
    n_before: int,
    n_after: int,
    n_gap: int,
    sar_narrowed: bool,
) -> str:
    """Build a human-readable confidence note for the dating estimate."""
    parts = []

    if interval_days <= 5:
        parts.append("High temporal precision (≤5 days)")
    elif interval_days <= 30:
        parts.append(f"Moderate precision ({interval_days:.0f} day interval)")
    elif interval_days <= 90:
        parts.append(f"Low precision ({interval_days:.0f} day interval)")
    else:
        parts.append(f"Very low precision ({interval_days:.0f} day interval)")

    if n_before == 0:
        parts.append("WARNING: No clean null observation found before change")

    if n_gap > 0:
        parts.append(f"{n_gap} unusable observation(s) in gap")

    if sar_narrowed:
        parts.append("SAR observations narrowed the interval")

    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Batch dating for multiple tiles
# ---------------------------------------------------------------------------

def estimate_change_dates_batch(
    tile_ids: list[str],
    all_observations: dict[str, list[DatingObservation]],
    confirmation_steps: Optional[dict[str, int]] = None,
    alpha_loose: float = DEFAULT_ALPHA_LOOSE,
    q_min: float = DEFAULT_Q_MIN,
) -> dict[str, ChangeDateResult]:
    """
    Batch estimate change dates for multiple tiles.

    Parameters
    ----------
    tile_ids : list[str]
        Tiles to date.
    all_observations : dict[str, list[DatingObservation]]
        Observations keyed by tile_id.
    confirmation_steps : dict[str, int], optional
        E-process confirmation step for each tile.
    alpha_loose : float
        Loose p-value threshold.
    q_min : float
        Minimum quality threshold.

    Returns
    -------
    dict[str, ChangeDateResult]
        Dating results keyed by tile_id.
    """
    if confirmation_steps is None:
        confirmation_steps = {}

    results = {}
    for tid in tile_ids:
        obs = all_observations.get(tid, [])
        step = confirmation_steps.get(tid)
        results[tid] = estimate_change_date(
            tile_id=tid,
            observations=obs,
            confirmation_step=step,
            alpha_loose=alpha_loose,
            q_min=q_min,
        )

    return results
