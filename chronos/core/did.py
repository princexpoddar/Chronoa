"""
CHRONOS Difference-in-Differences (DiD) Estimator.

Implements the two-stage differencing pipeline that removes common atmospheric
and phenological confounders by contrasting each tile against a phenologically
matched control cohort C(i).

Stage 1: Raw residual — r_i(t) = e_i(t) − h(t)^T Θ̂_i
    (deviation from the tile's own harmonic expectation)

Stage 2: DiD residual — r̃_i(t) = r_i(t) − median_{m ∈ C(i)} r_m(t)
    (deviation relative to phenologically similar neighbours, cancelling
     the time fixed effect τ_κ(t))

Control cohort C(i) is constructed as the k-nearest neighbours in phenological
fingerprint space v^phen, constrained to:
    - Same acquisition (same timestamp / STAC scene)
    - Elevation band:  |z_m − z_i| < ε_z
    - Terrain aspect:  |θ_m − θ_i| < ε_θ
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_K_NEIGHBOURS = 64     # Number of control cohort members
DEFAULT_ELEV_BAND_M = 200.0  # Elevation tolerance (metres)
DEFAULT_ASPECT_BAND_DEG = 45.0  # Aspect tolerance (degrees)
BREAKDOWN_RHO_MIN = 0.5      # Minimum cohort inlier fraction


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CohortResult:
    """Result of control cohort construction for a single tile."""
    tile_id: str
    cohort_ids: list[str]
    cohort_distances: NDArray[np.float64]
    inlier_fraction: float
    is_regional_event: bool


@dataclass
class DiDResult:
    """Result of the Difference-in-Differences estimation for one tile-epoch."""
    tile_id: str
    timestamp_idx: int
    raw_residual: NDArray[np.float64]         # r_i(t), shape (d,)
    cohort_median_residual: NDArray[np.float64]  # median_{C(i)} r_m(t), shape (d,)
    did_residual: NDArray[np.float64]         # r̃_i(t) = r_i - median_C, shape (d,)
    cohort: CohortResult


# ---------------------------------------------------------------------------
# Cohort construction
# ---------------------------------------------------------------------------

def build_control_cohort(
    target_tile_id: str,
    target_v_phen: NDArray[np.float64],
    target_elevation: float,
    target_aspect: float,
    all_tile_ids: list[str],
    all_v_phen: NDArray[np.float64],
    all_elevations: NDArray[np.float64],
    all_aspects: NDArray[np.float64],
    k: int = DEFAULT_K_NEIGHBOURS,
    elev_band: float = DEFAULT_ELEV_BAND_M,
    aspect_band: float = DEFAULT_ASPECT_BAND_DEG,
) -> CohortResult:
    """
    Construct the phenologically matched control cohort C(i) for a target tile.

    Parameters
    ----------
    target_tile_id : str
        ID of the tile under analysis.
    target_v_phen : np.ndarray, shape (4,)
        Phenological fingerprint [A₁, φ₁, A₂, φ₂] of the target tile.
    target_elevation : float
        Elevation of the target tile (metres).
    target_aspect : float
        Terrain aspect of the target tile (degrees, 0–360).
    all_tile_ids : list[str]
        IDs of all candidate tiles in the same acquisition.
    all_v_phen : np.ndarray, shape (N, 4)
        Phenological fingerprints of all candidate tiles.
    all_elevations : np.ndarray, shape (N,)
        Elevations of all candidate tiles.
    all_aspects : np.ndarray, shape (N,)
        Aspects of all candidate tiles.
    k : int
        Number of cohort members to select.
    elev_band : float
        Maximum elevation difference tolerance (metres).
    aspect_band : float
        Maximum aspect difference tolerance (degrees).

    Returns
    -------
    CohortResult
        Selected cohort with distances and breakdown diagnostic.
    """
    target_v_phen = np.asarray(target_v_phen, dtype=np.float64)
    all_v_phen = np.asarray(all_v_phen, dtype=np.float64)
    all_elevations = np.asarray(all_elevations, dtype=np.float64)
    all_aspects = np.asarray(all_aspects, dtype=np.float64)
    N = len(all_tile_ids)

    # --- Apply terrain constraints ---
    elev_ok = np.abs(all_elevations - target_elevation) < elev_band
    # Aspect difference with wraparound (0° ↔ 360°)
    aspect_diff = np.abs(all_aspects - target_aspect)
    aspect_diff = np.minimum(aspect_diff, 360.0 - aspect_diff)
    aspect_ok = aspect_diff < aspect_band

    # Exclude self
    self_mask = np.array([tid != target_tile_id for tid in all_tile_ids])

    eligible = self_mask & elev_ok & aspect_ok
    eligible_indices = np.where(eligible)[0]

    if len(eligible_indices) == 0:
        # No eligible neighbours — regional event or isolated tile
        return CohortResult(
            tile_id=target_tile_id,
            cohort_ids=[],
            cohort_distances=np.array([], dtype=np.float64),
            inlier_fraction=0.0,
            is_regional_event=True,
        )

    # --- Compute phenological distances ---
    eligible_phen = all_v_phen[eligible_indices]  # (n_eligible, 4)
    # Circular-aware phase distance: wrap φ differences to [−π, π]
    distances = _phenological_distance(target_v_phen, eligible_phen)

    # Select k nearest
    k_actual = min(k, len(eligible_indices))
    if k_actual == len(eligible_indices):
        nearest_local = np.arange(len(eligible_indices))
    else:
        nearest_local = np.argpartition(distances, k_actual)[:k_actual]
    nearest_sorted = nearest_local[np.argsort(distances[nearest_local])]

    cohort_global_indices = eligible_indices[nearest_sorted]
    cohort_ids = [all_tile_ids[i] for i in cohort_global_indices]
    cohort_dists = distances[nearest_sorted]

    # --- Breakdown diagnostic ---
    # Inlier fraction: proportion of cohort members whose residual distance
    # is below the median distance (robust centrality check)
    median_dist = np.median(cohort_dists)
    inlier_count = np.sum(cohort_dists <= 2.0 * median_dist)
    inlier_fraction = float(inlier_count / k_actual)

    return CohortResult(
        tile_id=target_tile_id,
        cohort_ids=cohort_ids,
        cohort_distances=cohort_dists,
        inlier_fraction=inlier_fraction,
        is_regional_event=(inlier_fraction < BREAKDOWN_RHO_MIN),
    )


def _phenological_distance(
    target: NDArray[np.float64],
    candidates: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Compute phenological distance between a target and candidate tiles,
    with circular-aware phase difference handling.

    target: shape (4,) — [A₁, φ₁, A₂, φ₂]
    candidates: shape (N, 4)

    Distance = sqrt( (A₁−A₁')² + A₁·A₁'·(1−cos(φ₁−φ₁'))
                    + (A₂−A₂')² + A₂·A₂'·(1−cos(φ₂−φ₂')) )

    This gives amplitude-weighted angular distance that correctly handles
    phase wraparound and is zero-dominant when amplitudes are small.
    """
    N = candidates.shape[0]
    dist_sq = np.zeros(N, dtype=np.float64)

    for k_idx in range(2):
        A_target = target[2 * k_idx]
        phi_target = target[2 * k_idx + 1]
        A_cand = candidates[:, 2 * k_idx]
        phi_cand = candidates[:, 2 * k_idx + 1]

        # Amplitude difference squared
        dist_sq += (A_target - A_cand) ** 2

        # Amplitude-weighted angular distance
        phase_diff = phi_target - phi_cand
        dist_sq += A_target * A_cand * (1.0 - np.cos(phase_diff))

    return np.sqrt(np.maximum(dist_sq, 0.0))


# ---------------------------------------------------------------------------
# DiD residual computation
# ---------------------------------------------------------------------------

def compute_did_residuals(
    target_tile_id: str,
    target_raw_residuals: NDArray[np.float64],
    cohort: CohortResult,
    cohort_raw_residuals: NDArray[np.float64],
) -> list[DiDResult]:
    """
    Compute DiD residuals r̃_i(t) = r_i(t) − median_{C(i)} r_m(t) across
    all time steps.

    Parameters
    ----------
    target_tile_id : str
        ID of the tile under analysis.
    target_raw_residuals : np.ndarray, shape (T, d)
        Raw residuals r_i(t) for T time steps.
    cohort : CohortResult
        The control cohort metadata.
    cohort_raw_residuals : np.ndarray, shape (|C|, T, d)
        Raw residuals for each cohort member across all T time steps.

    Returns
    -------
    list[DiDResult]
        DiD result for each time step.
    """
    target_raw_residuals = np.asarray(target_raw_residuals, dtype=np.float64)
    T = target_raw_residuals.shape[0]

    if cohort.is_regional_event or len(cohort.cohort_ids) == 0:
        # No valid cohort — return raw residuals as DiD (no correction)
        results = []
        zero_median = np.zeros_like(target_raw_residuals[0])
        for t_idx in range(T):
            results.append(DiDResult(
                tile_id=target_tile_id,
                timestamp_idx=t_idx,
                raw_residual=target_raw_residuals[t_idx],
                cohort_median_residual=zero_median,
                did_residual=target_raw_residuals[t_idx],
                cohort=cohort,
            ))
        return results

    cohort_raw_residuals = np.asarray(cohort_raw_residuals, dtype=np.float64)

    results = []
    for t_idx in range(T):
        raw_r = target_raw_residuals[t_idx]                    # (d,)
        cohort_r_t = cohort_raw_residuals[:, t_idx, :]         # (|C|, d)
        median_r = np.median(cohort_r_t, axis=0)               # (d,)
        did_r = raw_r - median_r                                # (d,)

        results.append(DiDResult(
            tile_id=target_tile_id,
            timestamp_idx=t_idx,
            raw_residual=raw_r,
            cohort_median_residual=median_r,
            did_residual=did_r,
            cohort=cohort,
        ))

    return results


def compute_did_residuals_batched(
    target_raw_residuals: NDArray[np.float64],
    cohort_raw_residuals: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Vectorised batch DiD computation for performance.

    Parameters
    ----------
    target_raw_residuals : shape (T, d)
    cohort_raw_residuals : shape (|C|, T, d)

    Returns
    -------
    did_residuals : shape (T, d)
        r̃_i(t) = r_i(t) − median_{C(i)} r_m(t)
    """
    median_cohort = np.median(cohort_raw_residuals, axis=0)  # (T, d)
    return target_raw_residuals - median_cohort
