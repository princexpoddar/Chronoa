"""
CHRONOS Harmonic Embedding Field Fitter.

Implements Algorithm 1 from the CHRONOS architecture: K=2 Fourier harmonic
regression with robust Iteratively Reweighted Least Squares (IRLS) using
Huber ψ-function, quality-weighted observations, quadratic penalty regularisation,
and Sherman–Morrison closed-form recursive online updates.

The harmonic model for each tile i:
    e_i(t) = h(t)^T · Θ_i + ε_i(t)

where the design row is:
    h(t) = [1, t̄, cos(ωt), sin(ωt), cos(2ωt), sin(2ωt)]  ∈ ℝ^6  (K=2)

with ω = 2π / T_year, t̄ = (t - t_ref) / T_year (centred fractional year).

Key outputs per tile:
    v^sem_i  = α̂_i + β̂_i · t̄_mid           (season-invariant semantic vector)
    v^phen_i = [A₁, φ₁, A₂, φ₂]              (phenological fingerprint)
    r_i(t)   = e_i(t) - h(t)^T · Θ̂_i         (residual for conformal scoring)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from chronos.core.types import HarmonicCoefficients


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OMEGA = 2.0 * np.pi          # Annual angular frequency (ω = 2π / 1 year)
K_HARMONICS = 2              # Number of Fourier harmonics
M_DESIGN = 2 * K_HARMONICS + 2  # = 6 columns: [1, t̄, cos ω, sin ω, cos 2ω, sin 2ω]

# Quadratic penalty matrix Λ = diag(0, 0, 1, 1, 4, 4)
# Zero penalty on intercept & trend; k² penalty on k-th harmonic pair
LAMBDA_DIAG = np.array([0.0, 0.0, 1.0, 1.0, 4.0, 4.0], dtype=np.float64)

# IRLS parameters
HUBER_C = 1.345              # Huber ψ tuning constant (95% asymptotic efficiency)
MAX_IRLS_ITER = 20           # Maximum IRLS iterations
IRLS_TOL = 1e-4              # Relative change convergence tolerance

# Reference epoch for centring (arbitrary — set to J2020.0)
T_REF = datetime(2020, 1, 1)


# ---------------------------------------------------------------------------
# Design matrix construction
# ---------------------------------------------------------------------------

def _datetime_to_fractional_year(t: datetime) -> float:
    """Convert a datetime to a centred fractional year relative to T_REF."""
    delta = (t - T_REF).total_seconds()
    return delta / (365.25 * 86400.0)


def fractional_years(timestamps: list[datetime]) -> NDArray[np.float64]:
    """Convert a list of datetimes to centred fractional years."""
    return np.array([_datetime_to_fractional_year(t) for t in timestamps],
                    dtype=np.float64)


def design_row(t_bar: float) -> NDArray[np.float64]:
    """
    Build a single design row h(t̄) ∈ ℝ^m for a centred fractional year t̄.

    h(t̄) = [1, t̄, cos(ωt̄), sin(ωt̄), cos(2ωt̄), sin(2ωt̄)]
    """
    row = np.empty(M_DESIGN, dtype=np.float64)
    row[0] = 1.0
    row[1] = t_bar
    for k in range(1, K_HARMONICS + 1):
        angle = k * OMEGA * t_bar
        row[2 * k] = np.cos(angle)
        row[2 * k + 1] = np.sin(angle)
    return row


def design_matrix(t_bars: NDArray[np.float64]) -> NDArray[np.float64]:
    """
    Build the full design matrix H ∈ ℝ^(n × m) for n centred fractional years.
    """
    n = len(t_bars)
    H = np.empty((n, M_DESIGN), dtype=np.float64)
    H[:, 0] = 1.0
    H[:, 1] = t_bars
    for k in range(1, K_HARMONICS + 1):
        angles = k * OMEGA * t_bars
        H[:, 2 * k] = np.cos(angles)
        H[:, 2 * k + 1] = np.sin(angles)
    return H


# ---------------------------------------------------------------------------
# Robust Huber IRLS weighting
# ---------------------------------------------------------------------------

def _huber_weights(residuals: NDArray[np.float64],
                   scale: float) -> NDArray[np.float64]:
    """
    Compute Huber robustness weights w_j = ψ(u_j) / u_j where u_j = r_j / σ̂.

    Returns array of weights ∈ (0, 1] with shape matching residuals.
    """
    if scale < 1e-12:
        return np.ones_like(residuals)
    u = np.abs(residuals) / scale
    weights = np.ones_like(u)
    mask = u > HUBER_C
    weights[mask] = HUBER_C / u[mask]
    return weights


def _mad_scale(residuals: NDArray[np.float64]) -> float:
    """
    Median Absolute Deviation scale estimate:  σ̂ = 1.4826 · median(|r - median(r)|).
    """
    med = np.median(residuals, axis=0)
    # For multi-dimensional residuals, compute per-column then take mean
    if residuals.ndim == 2:
        mad_per_dim = np.median(np.abs(residuals - med), axis=0)
        return float(np.mean(1.4826 * mad_per_dim))
    else:
        return float(1.4826 * np.median(np.abs(residuals - med)))


# ---------------------------------------------------------------------------
# Batch harmonic field fitting (Algorithm 1)
# ---------------------------------------------------------------------------

def fit_harmonic_field(
    timestamps: list[datetime],
    embeddings: NDArray[np.float64],
    quality_weights: NDArray[np.float64],
    ridge_lambda: float = 1.0,
    q_min: float = 0.2,
) -> HarmonicCoefficients:
    """
    Fit a robust harmonic embedding field to a tile's time series.

    Parameters
    ----------
    timestamps : list[datetime]
        Acquisition timestamps, length n.
    embeddings : np.ndarray, shape (n, d)
        Embedding vectors e_i(t) for each observation.
    quality_weights : np.ndarray, shape (n,)
        Composite quality weights q_i(t) ∈ [0, 1] from the masking pipeline.
    ridge_lambda : float
        Global ridge regularisation strength (λ_ridge).
    q_min : float
        Minimum quality weight threshold; observations below this are excluded.

    Returns
    -------
    HarmonicCoefficients
        Fitted parameters including Θ̂, v^sem, v^phen, P, and MAD scale.
    """
    # Validate inputs
    embeddings = np.asarray(embeddings, dtype=np.float64)
    quality_weights = np.asarray(quality_weights, dtype=np.float64)

    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(-1, 1)

    n, d = embeddings.shape
    assert len(timestamps) == n, f"timestamps ({len(timestamps)}) != embeddings ({n})"
    assert quality_weights.shape == (n,), f"quality_weights shape mismatch"

    # Filter usable observations
    usable_mask = quality_weights >= q_min
    if usable_mask.sum() < M_DESIGN:
        # Insufficient observations — return a zero-centred fallback
        return _fallback_coefficients(embeddings, d, timestamps)

    t_bars = fractional_years(timestamps)
    t_usable = t_bars[usable_mask]
    e_usable = embeddings[usable_mask]
    q_usable = quality_weights[usable_mask]
    n_usable = int(usable_mask.sum())

    # Build design matrix for usable observations
    H = design_matrix(t_usable)  # (n_usable, m)

    # Penalty matrix: Λ = λ_ridge · diag(LAMBDA_DIAG)
    Lambda = ridge_lambda * np.diag(LAMBDA_DIAG)  # (m, m)

    # --- IRLS loop ---
    # Initial weights = quality weights only
    w = q_usable.copy()

    theta = np.zeros((M_DESIGN, d), dtype=np.float64)
    mad = 1.0

    for irls_iter in range(MAX_IRLS_ITER):
        theta_prev = theta.copy()

        # Weighted design: W = diag(w)
        W_sqrt = np.sqrt(w)  # (n_usable,)

        # Weighted normal equations:  (H^T W H + Λ) Θ = H^T W E
        HtW = H.T * w[np.newaxis, :]  # (m, n_usable) — broadcasting H.T * w
        A = HtW @ H + Lambda          # (m, m)
        B = HtW @ e_usable            # (m, d)

        # Solve via Cholesky (A is positive definite due to ridge)
        try:
            L = np.linalg.cholesky(A)
            theta = np.linalg.solve(L.T, np.linalg.solve(L, B))
        except np.linalg.LinAlgError:
            # Fall back to pseudo-inverse if Cholesky fails
            theta = np.linalg.lstsq(A, B, rcond=None)[0]

        # Residuals
        residuals = e_usable - H @ theta  # (n_usable, d)

        # MAD scale estimate
        mad = _mad_scale(residuals)

        # Huber weights (per-observation, using L2 norm of residual vector)
        res_norms = np.linalg.norm(residuals, axis=1)  # (n_usable,)
        huber_w = _huber_weights(res_norms, mad)

        # Combined weights: quality × robustness
        w = q_usable * huber_w

        # Convergence check
        if irls_iter > 0:
            rel_change = np.linalg.norm(theta - theta_prev) / (
                np.linalg.norm(theta) + 1e-12
            )
            if rel_change < IRLS_TOL:
                break

    # --- Extract semantic and phenological vectors ---
    t_mid = 0.5 * (t_usable.min() + t_usable.max())
    v_sem = theta[0, :] + theta[1, :] * t_mid  # α̂ + β̂ · t̄_mid

    # Phenological fingerprint: A_k = sqrt(a_k² + b_k²), φ_k = atan2(b_k, a_k)
    v_phen = np.empty(4, dtype=np.float64)
    for k in range(1, K_HARMONICS + 1):
        a_k = np.linalg.norm(theta[2 * k, :])       # cos coefficient magnitude
        b_k = np.linalg.norm(theta[2 * k + 1, :])   # sin coefficient magnitude
        A_k = np.sqrt(a_k ** 2 + b_k ** 2)
        phi_k = np.arctan2(b_k, a_k)
        v_phen[2 * (k - 1)] = A_k
        v_phen[2 * (k - 1) + 1] = phi_k

    # --- Covariance matrix P = (H^T W H + Λ)^{-1} for recursive updates ---
    P = np.linalg.inv(A)

    return HarmonicCoefficients(
        theta=theta,
        v_sem=v_sem,
        v_phen=v_phen,
        P=P,
        mad_scale=mad,
        n_obs=n_usable,
        last_updated=max(timestamps),
    )


def _fallback_coefficients(embeddings: NDArray[np.float64], d: int,
                           timestamps: list[datetime]) -> HarmonicCoefficients:
    """Produce a zero-harmonic fallback when insufficient observations exist."""
    theta = np.zeros((M_DESIGN, d), dtype=np.float64)
    theta[0, :] = np.mean(embeddings, axis=0)  # intercept = mean embedding
    return HarmonicCoefficients(
        theta=theta,
        v_sem=theta[0, :].copy(),
        v_phen=np.zeros(4, dtype=np.float64),
        P=np.eye(M_DESIGN, dtype=np.float64),
        mad_scale=1.0,
        n_obs=len(timestamps),
        last_updated=max(timestamps) if timestamps else datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Prediction and residual computation
# ---------------------------------------------------------------------------

def predict(coeffs: HarmonicCoefficients,
            timestamps: list[datetime]) -> NDArray[np.float64]:
    """
    Predict embeddings ê_i(t) = h(t)^T · Θ̂_i for given timestamps.

    Returns shape (n, d).
    """
    t_bars = fractional_years(timestamps)
    H = design_matrix(t_bars)
    return H @ coeffs.theta


def residuals(coeffs: HarmonicCoefficients,
              timestamps: list[datetime],
              embeddings: NDArray[np.float64]) -> NDArray[np.float64]:
    """
    Compute residuals r_i(t) = e_i(t) − h(t)^T · Θ̂_i.

    Returns shape (n, d).
    """
    return np.asarray(embeddings, dtype=np.float64) - predict(coeffs, timestamps)


# ---------------------------------------------------------------------------
# Sherman–Morrison recursive online update (Eq. 28)
# ---------------------------------------------------------------------------

def update_recursive(
    coeffs: HarmonicCoefficients,
    new_timestamp: datetime,
    new_embedding: NDArray[np.float64],
    quality_weight: float,
    q_min: float = 0.2,
) -> HarmonicCoefficients:
    """
    Incrementally update the harmonic field with a single new observation
    using the Sherman–Morrison rank-1 update in O(m² + md) time.

    Update equations:
        P ← P − (P h h^T P) / (1/w + h^T P h)
        Θ ← Θ + P h (e_new − h^T Θ)^T · w

    Parameters
    ----------
    coeffs : HarmonicCoefficients
        Current fitted coefficients (modified in-place conceptually; returns new).
    new_timestamp : datetime
        Timestamp of the new observation.
    new_embedding : np.ndarray, shape (d,)
        Embedding vector of the new observation.
    quality_weight : float
        Quality weight q ∈ [0, 1] of the new observation.
    q_min : float
        Minimum quality threshold.

    Returns
    -------
    HarmonicCoefficients
        Updated coefficients with the new observation incorporated.
    """
    new_embedding = np.asarray(new_embedding, dtype=np.float64)

    if quality_weight < q_min:
        # Below quality threshold — skip update
        return coeffs

    w = quality_weight
    t_bar = _datetime_to_fractional_year(new_timestamp)
    h = design_row(t_bar)  # (m,)

    # Retrieve current state
    P = coeffs.P.copy()        # (m, m)
    theta = coeffs.theta.copy()  # (m, d)

    # Sherman–Morrison update of P
    Ph = P @ h                               # (m,)
    denom = (1.0 / w) + h @ Ph               # scalar
    P_new = P - np.outer(Ph, Ph) / denom     # (m, m)

    # Coefficient update
    innovation = new_embedding - h @ theta    # (d,)
    theta_new = theta + np.outer(Ph, innovation) * (w / denom)  # (m, d)

    # Recompute derived vectors
    t_mid = t_bar  # Approximation: use new observation as midpoint update
    v_sem_new = theta_new[0, :] + theta_new[1, :] * t_mid

    v_phen_new = np.empty(4, dtype=np.float64)
    for k in range(1, K_HARMONICS + 1):
        a_k = np.linalg.norm(theta_new[2 * k, :])
        b_k = np.linalg.norm(theta_new[2 * k + 1, :])
        A_k = np.sqrt(a_k ** 2 + b_k ** 2)
        phi_k = np.arctan2(b_k, a_k)
        v_phen_new[2 * (k - 1)] = A_k
        v_phen_new[2 * (k - 1) + 1] = phi_k

    return HarmonicCoefficients(
        theta=theta_new,
        v_sem=v_sem_new,
        v_phen=v_phen_new,
        P=P_new,
        mad_scale=coeffs.mad_scale,  # MAD not updated online (periodic batch refresh)
        n_obs=coeffs.n_obs + 1,
        last_updated=new_timestamp,
    )
