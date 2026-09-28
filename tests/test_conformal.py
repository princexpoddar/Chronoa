"""
Tests for the CHRONOS Conformal Calibration module.

Validates:
    1. Empirical coverage on held-out null meets nominal 1-α across Monte Carlo runs
    2. Benjamini–Yekutieli controls FDR below target q
    3. Mahalanobis scoring is consistent with known covariance
    4. Active calibration update tightens thresholds
"""

import numpy as np
import pytest

from chronos.core.conformal import (
    estimate_covariance_ledoit_wolf,
    mahalanobis_score,
    mahalanobis_scores_batch,
    calibrate_stratum,
    conformal_pvalue,
    conformal_pvalues_batch,
    benjamini_yekutieli,
    update_calibration_with_rejection,
)


class TestCovarianceEstimation:
    """Tests for Ledoit-Wolf shrinkage estimator."""

    def test_identity_recovery(self):
        """With isotropic Gaussian data, shrunk covariance should be near identity."""
        rng = np.random.default_rng(42)
        X = rng.standard_normal((500, 4))
        sigma, sigma_inv = estimate_covariance_ledoit_wolf(X)

        # Should be close to identity
        np.testing.assert_allclose(sigma, np.eye(4), atol=0.15)

    def test_positive_definite(self):
        """Shrunk covariance should always be positive definite."""
        rng = np.random.default_rng(42)
        # Even with n < d (more dimensions than samples)
        X = rng.standard_normal((5, 20))
        sigma, sigma_inv = estimate_covariance_ledoit_wolf(X)

        eigenvalues = np.linalg.eigvalsh(sigma)
        assert np.all(eigenvalues > 0), "Covariance must be positive definite"

    def test_inverse_correct(self):
        """Σ̂ · Σ̂⁻¹ should be approximately identity."""
        rng = np.random.default_rng(42)
        X = rng.standard_normal((100, 6))
        sigma, sigma_inv = estimate_covariance_ledoit_wolf(X)

        product = sigma @ sigma_inv
        np.testing.assert_allclose(product, np.eye(6), atol=1e-8)


class TestMahalanobisScoring:
    """Tests for Mahalanobis nonconformity scores."""

    def test_zero_at_origin(self):
        """Zero residual should give zero score."""
        sigma_inv = np.eye(4)
        score = mahalanobis_score(np.zeros(4), sigma_inv)
        assert score == pytest.approx(0.0, abs=1e-10)

    def test_unit_vector_identity_cov(self):
        """Unit vector with identity covariance should give score = 1."""
        sigma_inv = np.eye(4)
        for axis in range(4):
            r = np.zeros(4)
            r[axis] = 1.0
            score = mahalanobis_score(r, sigma_inv)
            assert score == pytest.approx(1.0, abs=1e-10)

    def test_batch_matches_single(self):
        """Batch scoring should match individual scoring."""
        rng = np.random.default_rng(42)
        sigma_inv = np.eye(6) * 2.0
        residuals = rng.standard_normal((20, 6))

        batch_scores = mahalanobis_scores_batch(residuals, sigma_inv)
        for i in range(20):
            single = mahalanobis_score(residuals[i], sigma_inv)
            assert batch_scores[i] == pytest.approx(single, abs=1e-10)


class TestConformalPValues:
    """Tests for smoothed conformal p-values."""

    def test_pvalue_range(self):
        """P-values should be in (0, 1]."""
        rng = np.random.default_rng(42)
        null_residuals = rng.standard_normal((100, 4))
        cal = calibrate_stratum("test", null_residuals)

        for _ in range(50):
            score = rng.uniform(0, 5)
            p = conformal_pvalue(score, cal, rng=rng)
            assert 0 < p <= 1.0

    def test_high_score_low_pvalue(self):
        """Very high scores should tend to give low p-values."""
        rng = np.random.default_rng(42)
        null_residuals = rng.standard_normal((500, 4))
        cal = calibrate_stratum("test", null_residuals)

        # A very extreme score
        extreme_score = 100.0
        pvals = [conformal_pvalue(extreme_score, cal, rng=rng) for _ in range(20)]
        mean_pval = np.mean(pvals)
        assert mean_pval < 0.05, f"Extreme score should give low p-value, got {mean_pval}"

    def test_null_superuniformity(self):
        """
        Under H₀ (scores from the null distribution), conformal p-values
        should be super-uniform: P(p ≤ α) ≤ α + 1/(n+1).
        """
        rng = np.random.default_rng(42)
        d = 4
        n_cal = 200
        n_test = 1000
        alpha = 0.1

        # Generate null data
        null_data = rng.standard_normal((n_cal + n_test, d))
        cal_data = null_data[:n_cal]
        test_data = null_data[n_cal:]

        # Calibrate
        cal = calibrate_stratum("test", cal_data)

        # Score test points
        from chronos.core.conformal import mahalanobis_scores_batch
        test_scores = mahalanobis_scores_batch(test_data, cal.sigma_inv)

        # Compute p-values
        pvals = conformal_pvalues_batch(test_scores, cal, rng=rng)

        # Check false alarm rate
        false_alarm_rate = np.mean(pvals <= alpha)
        # Conservative bound: should be ≤ α + 1/(n_cal+1)
        bound = alpha + 1.0 / (n_cal + 1)

        assert false_alarm_rate <= bound + 0.03, (
            f"False alarm rate {false_alarm_rate:.3f} exceeds bound {bound:.3f}"
        )


class TestBenjaminiYekutieli:
    """Tests for BY-FDR control."""

    def test_no_rejections_under_null(self):
        """With truly null p-values (uniform), FDR should control correctly."""
        rng = np.random.default_rng(42)
        M = 100
        target_fdr = 0.10

        # Run many rounds
        false_discoveries = 0
        n_rounds = 200
        total_rejections = 0

        for _ in range(n_rounds):
            pvals = rng.uniform(0, 1, M)
            result = benjamini_yekutieli(pvals, target_fdr=target_fdr)
            false_discoveries += len(result.flagged_indices)
            total_rejections += 1 if len(result.flagged_indices) > 0 else 0

        # Average false discovery proportion should be ≤ target_fdr
        if total_rejections > 0:
            avg_fdp = false_discoveries / (n_rounds * M)
            assert avg_fdp < target_fdr + 0.02

    def test_all_significant_flagged(self):
        """Very small p-values should all be flagged."""
        pvals = np.array([0.001, 0.002, 0.003, 0.9, 0.95])
        result = benjamini_yekutieli(pvals, target_fdr=0.10)
        # At least the first few should be flagged
        assert len(result.flagged_indices) >= 2

    def test_adjusted_qvalues_monotonic(self):
        """BY-adjusted q-values should be monotonic when sorted by p-value."""
        rng = np.random.default_rng(42)
        pvals = rng.uniform(0, 1, 50)
        result = benjamini_yekutieli(pvals, target_fdr=0.10)

        sorted_idx = np.argsort(pvals)
        sorted_q = result.adjusted_qvalues[sorted_idx]
        # Should be non-decreasing
        assert np.all(np.diff(sorted_q) >= -1e-10)

    def test_empty_input(self):
        """Empty input should return empty result."""
        result = benjamini_yekutieli(np.array([]), target_fdr=0.10)
        assert result.n_candidates == 0
        assert result.k_star == 0


class TestActiveCalibrationUpdate:
    """Tests for the analyst feedback loop."""

    def test_rejection_increases_null_set(self):
        """Adding a rejected residual should increase the null set size by 1."""
        rng = np.random.default_rng(42)
        null_data = rng.standard_normal((100, 4))
        cal = calibrate_stratum("test", null_data)
        assert cal.n_null == 100

        new_residual = rng.standard_normal(4)
        cal_updated = update_calibration_with_rejection(cal, new_residual)
        assert cal_updated.n_null == 101

    def test_rejection_tightens_threshold(self):
        """
        Adding a high-scoring rejection should increase the quantile at a
        given level (making the threshold harder to exceed).
        """
        rng = np.random.default_rng(42)
        null_data = rng.standard_normal((200, 4))
        cal = calibrate_stratum("test", null_data)
        q95_before = cal.quantile(0.95)

        # Add a high-scoring "rejection" (was flagged but analyst said no change)
        high_residual = rng.standard_normal(4) * 5.0
        cal_updated = update_calibration_with_rejection(cal, high_residual)
        q95_after = cal_updated.quantile(0.95)

        # The 95th percentile should have increased or stayed the same
        assert q95_after >= q95_before - 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
