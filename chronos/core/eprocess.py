"""
CHRONOS Anytime-Valid Conformal Test Martingale (E-Process).

Implements the sequential testing framework that allows CHRONOS to accumulate
evidence for change over an unbounded stream of new observations without
ever needing to rebuild or re-test.

Core construction:
    E_i(t) = Π_{t' ≤ t, q_i(t') ≥ q_min}  ς_{t'}(p_i(t'))

where ς_κ(p) = κ · p^{κ−1} is a predictable betting function from the
power family, and κ ∈ (0, 1) is estimated online per stratum.

Stopping rule (Ville's inequality):
    Confirmed change when E_i(t) ≥ 1/α

Key guarantee:
    Under H₀ (no change): P(sup_t E_i(t) ≥ 1/α) ≤ α
    — valid at ANY stopping time, no correction for multiple looks needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_ALPHA = 0.05          # Significance level (E ≥ 20 to reject)
DEFAULT_KAPPA = 0.5           # Initial betting parameter κ
KAPPA_MIN = 0.05              # Minimum κ (prevents degenerate betting)
KAPPA_MAX = 0.95              # Maximum κ
LOG_EVIDENCE_CAP = 50.0       # Cap log-evidence to prevent overflow


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class EProcessState:
    """
    Running state of the e-process martingale for a single tile.
    """
    tile_id: str
    log_evidence: float = 0.0      # log(E_i(t))
    n_updates: int = 0              # Number of observations processed
    kappa: float = DEFAULT_KAPPA    # Current betting parameter
    is_confirmed: bool = False      # Whether Ville's boundary is exceeded
    confirmation_step: Optional[int] = None  # Step at which confirmation occurred
    pvalue_history: list[float] = field(default_factory=list)

    @property
    def evidence(self) -> float:
        """Current evidence value E_i(t) = exp(log_evidence)."""
        return np.exp(min(self.log_evidence, LOG_EVIDENCE_CAP))

    def threshold(self, alpha: float = DEFAULT_ALPHA) -> float:
        """Ville's inequality threshold: 1/α."""
        return 1.0 / alpha


# ---------------------------------------------------------------------------
# Betting functions
# ---------------------------------------------------------------------------

def power_betting(p: float, kappa: float) -> float:
    """
    Power-family betting function:

        ς_κ(p) = κ · p^{κ−1}

    This maps a p-value to a multiplicative evidence factor.
    Under H₀ where p ~ Uniform(0,1):  E[ς_κ(p)] = 1  (martingale property).
    Under H₁ where p tends to be small: ς_κ(p) > 1    (evidence accumulates).

    Parameters
    ----------
    p : float
        Conformal p-value ∈ (0, 1].
    kappa : float
        Betting parameter κ ∈ (0, 1).

    Returns
    -------
    float
        Multiplicative evidence factor.
    """
    p = max(p, 1e-10)  # Prevent log(0)
    kappa = np.clip(kappa, KAPPA_MIN, KAPPA_MAX)
    return kappa * (p ** (kappa - 1))


def log_power_betting(p: float, kappa: float) -> float:
    """Log-space version for numerical stability: log(ς_κ(p))."""
    p = max(p, 1e-10)
    kappa = np.clip(kappa, KAPPA_MIN, KAPPA_MAX)
    return np.log(kappa) + (kappa - 1) * np.log(p)


# ---------------------------------------------------------------------------
# Online κ estimation
# ---------------------------------------------------------------------------

def estimate_kappa_online(
    pvalue_history: list[float],
    method: str = "regret_minimizing",
) -> float:
    """
    Estimate the optimal betting parameter κ from observed p-value history.

    Uses the regret-minimising approach: choose κ that would have maximised
    accumulated log-evidence on past observations (hindsight-optimal, then
    apply prospectively).

    Parameters
    ----------
    pvalue_history : list[float]
        History of conformal p-values for this tile.
    method : str
        Estimation method. Currently supports "regret_minimizing".

    Returns
    -------
    float
        Estimated optimal κ.
    """
    if len(pvalue_history) < 3:
        return DEFAULT_KAPPA

    pvals = np.array(pvalue_history, dtype=np.float64)
    pvals = np.clip(pvals, 1e-10, 1.0)

    # Grid search over κ values
    kappa_grid = np.linspace(KAPPA_MIN, KAPPA_MAX, 50)
    log_evidences = np.zeros(len(kappa_grid))

    for i, kappa in enumerate(kappa_grid):
        log_evidences[i] = np.sum(
            np.log(kappa) + (kappa - 1) * np.log(pvals)
        )

    best_idx = np.argmax(log_evidences)
    return float(kappa_grid[best_idx])


# ---------------------------------------------------------------------------
# E-process update
# ---------------------------------------------------------------------------

def update_eprocess(
    state: EProcessState,
    new_pvalue: float,
    quality_weight: float,
    q_min: float = 0.2,
    alpha: float = DEFAULT_ALPHA,
    adapt_kappa: bool = True,
) -> EProcessState:
    """
    Perform a single multiplicative update of the e-process martingale.

        E_i(t) ← E_i(t-1) · ς_κ(p_i(t))     if q_i(t) ≥ q_min
        E_i(t) ← E_i(t-1)                      otherwise (skip cloudy obs)

    Parameters
    ----------
    state : EProcessState
        Current running state.
    new_pvalue : float
        Conformal p-value p_i(t) for the new observation.
    quality_weight : float
        Quality weight q_i(t).
    q_min : float
        Minimum quality threshold.
    alpha : float
        Significance level for Ville's test.
    adapt_kappa : bool
        Whether to adaptively update κ from history.

    Returns
    -------
    EProcessState
        Updated state (new object, state is immutable).
    """
    # Copy state
    new_state = EProcessState(
        tile_id=state.tile_id,
        log_evidence=state.log_evidence,
        n_updates=state.n_updates,
        kappa=state.kappa,
        is_confirmed=state.is_confirmed,
        confirmation_step=state.confirmation_step,
        pvalue_history=state.pvalue_history.copy(),
    )

    # If already confirmed, no further updates needed
    if new_state.is_confirmed:
        return new_state

    # Skip low-quality observations
    if quality_weight < q_min:
        return new_state

    # Adaptively update κ using strictly past p-values (F_{t-1} measurable)
    if adapt_kappa and len(new_state.pvalue_history) >= 5:
        new_state.kappa = estimate_kappa_online(new_state.pvalue_history)

    # Record new p-value
    new_state.pvalue_history.append(new_pvalue)

    # Multiplicative update in log-space
    log_increment = log_power_betting(new_pvalue, new_state.kappa)
    new_state.log_evidence += log_increment
    new_state.n_updates += 1

    # Cap to prevent overflow
    new_state.log_evidence = min(new_state.log_evidence, LOG_EVIDENCE_CAP)

    # Check Ville's inequality: E_i(t) ≥ 1/α
    log_threshold = -np.log(alpha)
    if new_state.log_evidence >= log_threshold:
        new_state.is_confirmed = True
        new_state.confirmation_step = new_state.n_updates

    return new_state


def create_eprocess(tile_id: str) -> EProcessState:
    """Create a fresh e-process state for a new tile."""
    return EProcessState(tile_id=tile_id)


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def run_eprocess_sequence(
    tile_id: str,
    pvalues: NDArray[np.float64],
    quality_weights: NDArray[np.float64],
    alpha: float = DEFAULT_ALPHA,
    q_min: float = 0.2,
) -> EProcessState:
    """
    Run the e-process over an entire sequence of observations for a tile.

    Parameters
    ----------
    tile_id : str
        Tile identifier.
    pvalues : np.ndarray, shape (T,)
        Conformal p-values for each time step.
    quality_weights : np.ndarray, shape (T,)
        Quality weights for each time step.
    alpha : float
        Significance level.
    q_min : float
        Minimum quality threshold.

    Returns
    -------
    EProcessState
        Final e-process state after processing all observations.
    """
    state = create_eprocess(tile_id)

    for t in range(len(pvalues)):
        state = update_eprocess(
            state=state,
            new_pvalue=float(pvalues[t]),
            quality_weight=float(quality_weights[t]),
            q_min=q_min,
            alpha=alpha,
            adapt_kappa=True,
        )

    return state


# ---------------------------------------------------------------------------
# Verification utilities
# ---------------------------------------------------------------------------

def ljung_box_test(
    residuals: NDArray[np.float64],
    max_lag: int = 10,
) -> tuple[float, float]:
    """
    Ljung–Box test for serial independence of residuals.

    Used to verify that out-of-fold residuals satisfy the independence
    assumption required for valid e-process inference.

    Parameters
    ----------
    residuals : np.ndarray, shape (T,) or (T, d)
        Residual series (if multi-dimensional, uses L2 norms).
    max_lag : int
        Maximum lag to test.

    Returns
    -------
    test_statistic : float
        Ljung-Box Q statistic.
    pvalue : float
        Approximate chi-squared p-value.
    """
    residuals = np.asarray(residuals, dtype=np.float64)
    if residuals.ndim == 2:
        residuals = np.linalg.norm(residuals, axis=1)

    T = len(residuals)
    if T < max_lag + 2:
        return 0.0, 1.0  # Too few observations

    mean = np.mean(residuals)
    centred = residuals - mean
    var = np.sum(centred ** 2)

    if var < 1e-12:
        return 0.0, 1.0

    Q = 0.0
    for lag in range(1, max_lag + 1):
        rho = np.sum(centred[lag:] * centred[:-lag]) / var
        Q += (rho ** 2) / (T - lag)

    Q *= T * (T + 2)

    # Approximate chi-squared p-value with max_lag degrees of freedom
    # Using the survival function approximation
    from scipy.stats import chi2
    pvalue = float(chi2.sf(Q, df=max_lag))

    return float(Q), pvalue
