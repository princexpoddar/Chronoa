"""
CHRONOS Harmonic Embedding Field Fitter.

Coordinates the fitting of the temporal model over the embedding time series.
Applies the robust IRLS ridge regression and Sherman-Morrison recursive updates.
"""

from typing import List, Tuple
import numpy as np

from chronos.core.types import ObservationRecord, HarmonicCoefficients
from chronos.core.harmonics import (
    fit_harmonic_field,
    update_recursive,
    design_matrix,
    fractional_years
)

class FieldFitter:
    def __init__(
        self,
        base_lambda_reg: float = 0.1,
        irls_max_iter: int = 10,
        irls_tol: float = 1e-4,
        huber_c: float = 1.345
    ):
        self.base_lambda = base_lambda_reg
        
    def fit_batch(
        self,
        records: List[ObservationRecord],
        embeddings: np.ndarray
    ) -> Tuple[HarmonicCoefficients, HarmonicCoefficients]: # returns (coeffs, state) which are the same thing here
        """
        Perform a full batch fit (Stage 4) using IRLS.
        """
        timestamps = [rec.timestamp for rec in records]
        q_weights = np.array([rec.quality_weight for rec in records])
        
        coeffs = fit_harmonic_field(
            timestamps=timestamps,
            embeddings=embeddings,
            quality_weights=q_weights,
            ridge_lambda=self.base_lambda,
            q_min=0.2
        )
        return coeffs, coeffs

    def update_online(
        self,
        state: HarmonicCoefficients,
        new_record: ObservationRecord,
        new_embedding: np.ndarray,
        q_min: float = 0.2
    ) -> HarmonicCoefficients:
        """
        Perform a recursive O(d^2) Sherman-Morrison update (Stage 5b).
        """
        return update_recursive(
            coeffs=state,
            new_timestamp=new_record.timestamp,
            new_embedding=new_embedding,
            quality_weight=new_record.quality_weight,
            q_min=q_min
        )
