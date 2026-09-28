"""
CHRONOS Mondrian Split-Conformal Calibration.

Implements label-free conformal inference with:
    1. Mahalanobis nonconformity scoring against DiD residuals
    2. Mondrian stratification (per-stratum calibration)
    3. Smoothed conformal p-values
    4. Benjamini–Yekutieli (BY) False Discovery Rate control over the review queue

Key guarantee: Under exchangeability of null residuals within each stratum,
    P(flag tile i | H₀) ≤ α    (marginal coverage)
    E[FDP] ≤ q                  (queue-level FDR control)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class StratumCalibration:
    """
    Calibration data for a single Mondrian stratum κ.

    Stores the null distribution of nonconformity scores harvested from
    the longest stable segments and cross-year same-phase pairs.
    """
    stratum_key: str
    null_scores: NDArray[np.float64]    # Sorted nonconformity scores from null set
    sigma_hat: NDArray[np.float64]      # Shrunk covariance Σ̂_κ, shape (d, d)
    sigma_inv: NDArray[np.float64]      # Σ̂_κ^{-1}, shape (d, d)
    n_null: int                          # Number of null calibration samples

    def quantile(self, level: float) -> float:
        """Return the level-th quantile of the null score distribution."""
        if self.n_null == 0:
            return float("inf")
        return float(np.quantile(self.null_scores, level))


@dataclass
class ConformalScoreResult:
    """Nonconformity score and p-value for a single tile-epoch."""
    tile_id: str
    stratum_key: str
    score: float                 # Mahalanobis nonconformity score s_i(t)
    pvalue: float                # Smoothed conformal p-value p_i(t)
    rank_in_null: int            # Position among null scores
    n_null: int                  # Size of calibration null set


@dataclass
class FDRResult:
    """Result of Benjamini–Yekutieli FDR control over a batch of candidates."""
    target_fdr: float
    n_candidates: int
    k_star: int                  # Largest k satisfying BY criterion
    threshold_pvalue: float      # p_{(k*)} threshold
    flagged_indices: list[int]   # Indices of flagged candidates
    adjusted_qvalues: NDArray[np.float64]  # BY-adjusted q-values


# ---------------------------------------------------------------------------
# Covariance estimation with Ledoit-Wolf shrinkage
# ---------------------------------------------------------------------------

def estimate_covariance_ledoit_wolf(
    residuals: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Estimate the residual covariance matrix with Ledoit-Wolf linear shrinkage.

    Σ̂ = (1 − δ) · S + δ · (tr(S)/d) · I

    where δ is the optimal shrinkage intensity and S is the sample covariance.

    Parameters
    ----------
    residuals : np.ndarray, shape (n, d)
        DiD residual vectors from the null calibration set.

    Returns
    -------
    sigma_hat : np.ndarray, shape (d, d)
        Shrunk covariance matrix.
    sigma_inv : np.ndarray, shape (d, d)
        Inverse of the shrunk covariance matrix.
    """
    residuals = np.asarray(residuals, dtype=np.float64)
    n, d = residuals.shape

    if n < 2:
        return np.eye(d), np.eye(d)

    # Centre the residuals
    mean = residuals.mean(axis=0)
    X = residuals - mean  # (n, d)

    # Sample covariance
    S = (X.T @ X) / (n - 1)  # (d, d)

    # Target: scaled identity
    mu = np.trace(S) / d
    F = mu * np.eye(d)

    # Optimal shrinkage intensity (Ledoit-Wolf 2004)
    # δ* = min(sum_ij var(s_ij) / sum_ij (s_ij - f_ij)^2, 1)
    X2 = X ** 2
    S2 = (X2.T @ X2) / (n - 1)  # element-wise fourth moment proxy

    # Numerator: sum of estimated variances of sample covariance entries
    numerator = np.sum(S2 - S ** 2) / (n - 1)

    # Denominator: sum of squared deviations from target
    denominator = np.sum((S - F) ** 2)

    if denominator < 1e-12:
        delta = 1.0
    else:
        delta = min(max(numerator / denominator, 0.0), 1.0)

    sigma_hat = (1.0 - delta) * S + delta * F

    # Invert (regularised, so always invertible)
    try:
        sigma_inv = np.linalg.inv(sigma_hat)
    except np.linalg.LinAlgError:
        sigma_inv = np.linalg.pinv(sigma_hat)

    return sigma_hat, sigma_inv


# ---------------------------------------------------------------------------
# Nonconformity scoring
# ---------------------------------------------------------------------------

def mahalanobis_score(
    residual: NDArray[np.float64],
    sigma_inv: NDArray[np.float64],
) -> float:
    """
    Compute the Mahalanobis nonconformity score:

        s_i(t) = sqrt(r̃_i(t)^T · Σ̂_κ^{-1} · r̃_i(t))

    Parameters
    ----------
    residual : np.ndarray, shape (d,)
        DiD residual r̃_i(t).
    sigma_inv : np.ndarray, shape (d, d)
        Inverse of the stratum covariance matrix.

    Returns
    -------
    float
        Mahalanobis nonconformity score.
    """
    residual = np.asarray(residual, dtype=np.float64)
    return float(np.sqrt(max(residual @ sigma_inv @ residual, 0.0)))


def mahalanobis_scores_batch(
    residuals: NDArray[np.float64],
    sigma_inv: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Batch Mahalanobis scoring for multiple residuals.

    Parameters
    ----------
    residuals : np.ndarray, shape (n, d)
    sigma_inv : np.ndarray, shape (d, d)

    Returns
    -------
    scores : np.ndarray, shape (n,)
    """
    residuals = np.asarray(residuals, dtype=np.float64)
    # r^T Σ^{-1} r for each row
    transformed = residuals @ sigma_inv  # (n, d)
    scores_sq = np.sum(residuals * transformed, axis=1)  # (n,)
    return np.sqrt(np.maximum(scores_sq, 0.0))


# ---------------------------------------------------------------------------
# Calibration set construction
# ---------------------------------------------------------------------------

def build_null_calibration_set(
    all_residuals: NDArray[np.float64],
    all_pvalues_loose: Optional[NDArray[np.float64]] = None,
    stability_threshold: float = 0.3,
) -> NDArray[np.float64]:
    """
    Harvest null (no-change) residuals for conformal calibration.

    Strategy (from CHRONOS Lemma 11):
        1. Use residuals from the longest stable segments per tile
           (consecutive residuals with L2 norm below the stability_threshold
           percentile of the tile's own history).
        2. Optionally include cross-year same-phase pairs.

    Parameters
    ----------
    all_residuals : np.ndarray, shape (N, d)
        All available DiD residuals across tiles and time steps.
    all_pvalues_loose : np.ndarray, shape (N,), optional
        Pre-computed loose p-values for conservative filtering.
        If provided, only residuals with p > stability_threshold are included.
    stability_threshold : float
        Loose p-value threshold for null inclusion (higher = more conservative).

    Returns
    -------
    null_residuals : np.ndarray, shape (n_null, d)
        Residuals believed to be from the null (no-change) distribution.
    """
    all_residuals = np.asarray(all_residuals, dtype=np.float64)

    if all_pvalues_loose is not None:
        # Filter by loose p-value (conservative: include only clearly null)
        mask = all_pvalues_loose > stability_threshold
        return all_residuals[mask]

    # Fallback: use residuals with L2 norm below the 80th percentile
    norms = np.linalg.norm(all_residuals, axis=1)
    threshold = np.percentile(norms, 80)
    mask = norms <= threshold
    return all_residuals[mask]


def calibrate_stratum(
    stratum_key: str,
    null_residuals: NDArray[np.float64],
) -> StratumCalibration:
    """
    Build a StratumCalibration from null residuals for a single Mondrian stratum.

    Parameters
    ----------
    stratum_key : str
        String identifier for the stratum.
    null_residuals : np.ndarray, shape (n_null, d)
        Null DiD residuals for this stratum.

    Returns
    -------
    StratumCalibration
        Calibrated stratum with covariance and sorted null scores.
    """
    null_residuals = np.asarray(null_residuals, dtype=np.float64)
    n_null = null_residuals.shape[0]

    if n_null < 2:
        d = null_residuals.shape[1] if null_residuals.ndim == 2 else 1
        return StratumCalibration(
            stratum_key=stratum_key,
            null_scores=np.array([], dtype=np.float64),
            sigma_hat=np.eye(d),
            sigma_inv=np.eye(d),
            n_null=0,
        )

    sigma_hat, sigma_inv = estimate_covariance_ledoit_wolf(null_residuals)
    null_scores = mahalanobis_scores_batch(null_residuals, sigma_inv)
    null_scores.sort()

    return StratumCalibration(
        stratum_key=stratum_key,
        null_scores=null_scores,
        sigma_hat=sigma_hat,
        sigma_inv=sigma_inv,
        n_null=n_null,
    )


# ---------------------------------------------------------------------------
# Smoothed conformal p-values
# ---------------------------------------------------------------------------

def conformal_pvalue(
    score: float,
    calibration: StratumCalibration,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """
    Compute the smoothed conformal p-value:

        p_i(t) = (|{j : s_j > s_i}| + τ |{j : s_j = s_i}| + τ) / (n + 1)

    where τ ~ U(0, 1) ensures super-uniformity under H₀.

    Parameters
    ----------
    score : float
        Nonconformity score s_i(t) of the test point.
    calibration : StratumCalibration
        Calibrated null distribution for the stratum.
    rng : np.random.Generator, optional
        Random generator for the smoothing variable τ.

    Returns
    -------
    float
        Conformal p-value ∈ (0, 1].
    """
    if rng is None:
        rng = np.random.default_rng()

    tau = rng.uniform(0.0, 1.0)
    n = calibration.n_null

    if n == 0:
        return tau  # No calibration data — uniform p-value

    null_scores = calibration.null_scores

    # Count strictly greater and equal
    n_greater = int(np.searchsorted(null_scores, score, side="right"))
    n_greater = n - n_greater  # scores > s_i

    n_equal = int(np.searchsorted(null_scores, score, side="right") -
                  np.searchsorted(null_scores, score, side="left"))

    pvalue = (n_greater + tau * n_equal + tau) / (n + 1)
    return float(np.clip(pvalue, 0.0, 1.0))


def conformal_pvalues_batch(
    scores: NDArray[np.float64],
    calibration: StratumCalibration,
    rng: Optional[np.random.Generator] = None,
) -> NDArray[np.float64]:
    """
    Batch conformal p-value computation for multiple test points.

    Parameters
    ----------
    scores : np.ndarray, shape (M,)
    calibration : StratumCalibration
    rng : np.random.Generator, optional

    Returns
    -------
    pvalues : np.ndarray, shape (M,)
    """
    if rng is None:
        rng = np.random.default_rng()

    M = len(scores)
    pvalues = np.empty(M, dtype=np.float64)

    for i in range(M):
        pvalues[i] = conformal_pvalue(scores[i], calibration, rng)

    return pvalues


# ---------------------------------------------------------------------------
# Benjamini–Yekutieli FDR control
# ---------------------------------------------------------------------------

def benjamini_yekutieli(
    pvalues: NDArray[np.float64],
    target_fdr: float = 0.10,
) -> FDRResult:
    """
    Apply the Benjamini–Yekutieli (BY) procedure to control False Discovery Rate
    under arbitrary dependence.

        k* = max { k : p_{(k)} ≤ (k / (M · c(M))) · q }

    where c(M) = Σ_{j=1}^{M} 1/j  (harmonic number, valid under dependence).

    Parameters
    ----------
    pvalues : np.ndarray, shape (M,)
        Conformal p-values for all candidates in the review queue.
    target_fdr : float
        Target FDR level q (e.g. 0.10 for 10% FDR).

    Returns
    -------
    FDRResult
        Flagged indices, adjusted q-values, and threshold.
    """
    pvalues = np.asarray(pvalues, dtype=np.float64)
    M = len(pvalues)

    if M == 0:
        return FDRResult(
            target_fdr=target_fdr,
            n_candidates=0,
            k_star=0,
            threshold_pvalue=0.0,
            flagged_indices=[],
            adjusted_qvalues=np.array([], dtype=np.float64),
        )

    # Harmonic number c(M) = Σ 1/j
    c_M = np.sum(1.0 / np.arange(1, M + 1))

    # Sort p-values
    sorted_indices = np.argsort(pvalues)
    sorted_pvals = pvalues[sorted_indices]

    # BY critical values: (k / (M · c(M))) · q
    ranks = np.arange(1, M + 1, dtype=np.float64)
    critical_values = (ranks / (M * c_M)) * target_fdr

    # Find k*: largest k where p_{(k)} ≤ critical_value_k
    rejections = sorted_pvals <= critical_values
    if not np.any(rejections):
        k_star = 0
        threshold_pvalue = 0.0
        flagged_indices = []
    else:
        k_star = int(np.max(np.where(rejections)[0]) + 1)
        threshold_pvalue = float(critical_values[k_star - 1])
        flagged_indices = sorted_indices[:k_star].tolist()

    # Compute BY-adjusted q-values
    adjusted_q = np.empty(M, dtype=np.float64)
    adjusted_q[sorted_indices[-1]] = min(
        sorted_pvals[-1] * M * c_M / M, 1.0
    )
    for i in range(M - 2, -1, -1):
        raw_q = sorted_pvals[i] * M * c_M / (i + 1)
        adjusted_q[sorted_indices[i]] = min(raw_q, adjusted_q[sorted_indices[i + 1]])

    return FDRResult(
        target_fdr=target_fdr,
        n_candidates=M,
        k_star=k_star,
        threshold_pvalue=threshold_pvalue,
        flagged_indices=flagged_indices,
        adjusted_qvalues=np.clip(adjusted_q, 0.0, 1.0),
    )


# ---------------------------------------------------------------------------
# Active calibration update (analyst feedback loop)
# ---------------------------------------------------------------------------

def update_calibration_with_rejection(
    calibration: StratumCalibration,
    rejected_residual: NDArray[np.float64],
) -> StratumCalibration:
    """
    Append an analyst-rejected candidate's residual to the null calibration set,
    tightening conformal thresholds for this stratum.

    This is the active feedback loop: rejections prove that certain residual
    patterns are false alarms, so they are folded into the null distribution.

    Parameters
    ----------
    calibration : StratumCalibration
        Current stratum calibration.
    rejected_residual : np.ndarray, shape (d,)
        DiD residual of the rejected candidate.

    Returns
    -------
    StratumCalibration
        Updated calibration with the rejection incorporated.
    """
    rejected_residual = np.asarray(rejected_residual, dtype=np.float64).reshape(1, -1)

    # Compute score of the rejected residual under current covariance
    new_score = mahalanobis_score(rejected_residual.ravel(), calibration.sigma_inv)

    # Insert into sorted null scores
    insert_idx = int(np.searchsorted(calibration.null_scores, new_score))
    new_null_scores = np.insert(calibration.null_scores, insert_idx, new_score)

    # Note: We do NOT recompute covariance here for efficiency.
    # Full recomputation happens during periodic batch recalibration.
    return StratumCalibration(
        stratum_key=calibration.stratum_key,
        null_scores=new_null_scores,
        sigma_hat=calibration.sigma_hat,
        sigma_inv=calibration.sigma_inv,
        n_null=calibration.n_null + 1,
    )
