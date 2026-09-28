"""
CHRONOS Main Change Engine Pipeline.

Ties together:
1. Embedding generation (Tier 1/2)
2. Harmonic modelling (FieldFitter)
3. Conformal p-values and DiD residuals
4. Martingale e-processes for sequential testing
"""

from typing import List, Tuple
import numpy as np

from chronos.core.types import ObservationRecord, EProcessState
from chronos.core.harmonics import design_matrix, fractional_years
from chronos.core.conformal import mahalanobis_scores_batch, conformal_pvalue, StratumCalibration
from chronos.core.eprocess import update_eprocess, create_eprocess
from chronos.engine.field_fitter import FieldFitter


class ChronosEngine:
    def __init__(self, fitter: FieldFitter):
        self.fitter = fitter
        
    def evaluate_bi_temporal(
        self,
        pre_records: List[ObservationRecord],
        pre_embeddings: np.ndarray,
        post_record: ObservationRecord,
        post_embedding: np.ndarray
    ) -> Tuple[float, float]:
        """
        Evaluate Mode C: Rapid Bi-Temporal 2-Epoch Change Detection.
        Fits harmonic model on 'pre' data, evaluates 'post' data via conformal p-value.
        
        Returns
        -------
        score : float
            Non-conformity score (Mahalanobis distance).
        p_value : float
            Conformal p-value for the post_embedding.
        """
        _, state = self.fitter.fit_batch(pre_records, pre_embeddings)
        
        t_bar_post = fractional_years([post_record.timestamp])[0]
        h_post = design_matrix(np.array([t_bar_post]))[0]
        
        y_hat_post = state.theta.T @ h_post
        residual_post = post_embedding - y_hat_post
        
        # Compute calibration residuals
        t_bars_cal = fractional_years([r.timestamp for r in pre_records])
        H_cal = design_matrix(t_bars_cal)
        Y_hat_cal = H_cal @ state.theta
        cal_residuals = pre_embeddings - Y_hat_cal
        
        cov = np.cov(cal_residuals, rowvar=False) + np.eye(pre_embeddings.shape[1]) * 1e-4
        
        # Score the test point
        score = mahalanobis_scores_batch(
            np.expand_dims(residual_post, 0), cov
        )[0]
        
        # Score the calibration set
        cal_scores = mahalanobis_scores_batch(cal_residuals, cov)
        
        # Conformal p-value
        p_val = conformal_pvalue(score, StratumCalibration(
            stratum_key="mode_c",
            null_scores=cal_scores,
            sigma_hat=cov,
            sigma_inv=cov, # Mock for testing
            n_null=len(cal_scores)
        ))
        return float(score), float(p_val)
        
    def evaluate_sequential(
        self,
        historical_records: List[ObservationRecord],
        historical_embeddings: np.ndarray,
        streaming_records: List[ObservationRecord],
        streaming_embeddings: np.ndarray,
        alpha: float = 0.05
    ) -> Tuple[EProcessState, int]:
        """
        Evaluate Mode A: Full Time-Series Sequential Testing.
        Tracks the Ville's inequality e-process boundary.
        
        Returns
        -------
        final_state : EProcessState
        change_idx : int
            Index in the streaming sequence where change was declared (-1 if no change).
        """
        _, state = self.fitter.fit_batch(historical_records, historical_embeddings)
        
        t_bars_cal = fractional_years([r.timestamp for r in historical_records])
        H_cal = design_matrix(t_bars_cal)
        Y_hat_cal = H_cal @ state.theta
        cal_residuals = historical_embeddings - Y_hat_cal
        cov = np.cov(cal_residuals, rowvar=False) + np.eye(historical_embeddings.shape[1]) * 1e-4
        cal_scores = mahalanobis_scores_batch(cal_residuals, cov)
        calibration = StratumCalibration(
            stratum_key="mode_a",
            null_scores=cal_scores,
            sigma_hat=cov,
            sigma_inv=cov, # Mock for testing
            n_null=len(cal_scores)
        )
        
        # Initialize e-process
        tile_id = historical_records[0].tile_id if historical_records else "unknown"
        ep_state = create_eprocess(tile_id)
        change_idx = -1
        
        for i, (rec, emb) in enumerate(zip(streaming_records, streaming_embeddings)):
            t_bar = fractional_years([rec.timestamp])[0]
            h = design_matrix(np.array([t_bar]))[0]
            y_hat = state.theta.T @ h
            residual = emb - y_hat
            
            score = mahalanobis_scores_batch(np.expand_dims(residual, 0), cov)[0]
            p_val = conformal_pvalue(score, calibration)
            
            ep_state = update_eprocess(ep_state, p_val, rec.quality_weight, alpha=alpha)
            
            if ep_state.is_confirmed and change_idx == -1:
                change_idx = i
                
            # Online update of the model
            state = self.fitter.update_online(state, rec, emb)
            
        return ep_state, change_idx
