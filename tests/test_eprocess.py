"""
Tests for the CHRONOS E-Process (Anytime-Valid Conformal Test Martingale).

Validates:
    1. Under H₀, sup_t E(t) ≥ 1/α occurs with probability ≤ α
    2. Under H₁ (persistent low p-values), evidence accumulates and triggers
    3. Betting function satisfies the martingale property E[ς(p)] = 1 under H₀
    4. Low-quality observations are correctly skipped
"""

import numpy as np
import pytest

from chronos.core.eprocess import (
    power_betting,
    log_power_betting,
    create_eprocess,
    update_eprocess,
    run_eprocess_sequence,
    DEFAULT_ALPHA,
)


class TestBettingFunction:
    """Tests for the power-family betting function."""

    def test_martingale_property(self):
        """
        Under H₀ where p ~ Uniform(0,1), E[ς_κ(p)] should equal 1.
        This is the fundamental martingale property.
        """
        rng = np.random.default_rng(42)
        n = 200_000

        # Note: kappas <= 0.5 have infinite variance for p^(kappa-1), making sample
        # mean convergence extremely slow. We test kappa > 0.5 where variance is finite.
        for kappa in [0.6, 0.7, 0.8, 0.9]:
            pvals = rng.uniform(0, 1, n)
            evidence_factors = np.array([power_betting(p, kappa) for p in pvals])
            mean_factor = np.mean(evidence_factors)
            assert mean_factor == pytest.approx(1.0, abs=0.05), (
                f"E[ς_{kappa}(p)] = {mean_factor:.3f}, expected ≈ 1.0"
            )

    def test_positive_values(self):
        """Betting function should always return positive values."""
        for kappa in [0.1, 0.5, 0.9]:
            for p in [0.001, 0.01, 0.1, 0.5, 0.99]:
                val = power_betting(p, kappa)
                assert val > 0

    def test_small_p_large_evidence(self):
        """Small p-values should produce large evidence factors."""
        kappa = 0.5
        val_small = power_betting(0.001, kappa)
        val_large = power_betting(0.9, kappa)
        assert val_small > val_large

    def test_log_consistency(self):
        """Log betting should be consistent with regular betting."""
        for kappa in [0.2, 0.5, 0.8]:
            for p in [0.01, 0.1, 0.5]:
                regular = power_betting(p, kappa)
                log_val = log_power_betting(p, kappa)
                assert np.log(regular) == pytest.approx(log_val, abs=1e-10)


class TestEProcessUnderNull:
    """Tests for e-process behaviour under the null hypothesis."""

    def test_type1_error_control(self):
        """
        Under H₀ (p-values are uniform), the probability of ever exceeding
        1/α should be ≤ α. This is Ville's inequality.
        """
        rng = np.random.default_rng(42)
        alpha = 0.05
        T = 100       # Time steps per sequence
        n_sims = 2000  # Monte Carlo simulations

        n_false_alarms = 0
        for _ in range(n_sims):
            pvals = rng.uniform(0, 1, T)
            qweights = np.ones(T)

            state = run_eprocess_sequence(
                tile_id="test",
                pvalues=pvals,
                quality_weights=qweights,
                alpha=alpha,
            )

            if state.is_confirmed:
                n_false_alarms += 1

        false_alarm_rate = n_false_alarms / n_sims
        # Ville guarantees P(false alarm) ≤ α = 0.05
        # Allow a small margin for Monte Carlo variance
        assert false_alarm_rate <= alpha + 0.02, (
            f"False alarm rate {false_alarm_rate:.3f} exceeds α={alpha}"
        )


class TestEProcessUnderAlternative:
    """Tests for e-process behaviour under the alternative (real change)."""

    def test_detects_persistent_change(self):
        """
        With persistently small p-values (real change), the e-process should
        eventually confirm change.
        """
        rng = np.random.default_rng(42)
        T = 50
        alpha = 0.05

        # Generate p-values: first 20 null (uniform), then 30 signal (Beta(0.5, 5))
        null_pvals = rng.uniform(0, 1, 20)
        signal_pvals = rng.beta(0.5, 5, 30)  # Concentrated near 0
        pvals = np.concatenate([null_pvals, signal_pvals])
        qweights = np.ones(T)

        state = run_eprocess_sequence(
            tile_id="test",
            pvalues=pvals,
            quality_weights=qweights,
            alpha=alpha,
        )

        assert state.is_confirmed, "Should detect persistent change signal"
        assert state.confirmation_step is not None
        assert state.confirmation_step > 15  # Should not trigger during null period


class TestEProcessMechanics:
    """Tests for e-process update mechanics."""

    def test_skip_low_quality(self):
        """Low quality observations should be skipped."""
        state = create_eprocess("test_tile")

        # Update with low quality — should not change evidence
        state_new = update_eprocess(
            state, new_pvalue=0.01, quality_weight=0.1, q_min=0.2
        )
        assert state_new.log_evidence == 0.0
        assert state_new.n_updates == 0

    def test_evidence_increases_with_low_pvalue(self):
        """A low p-value should increase the log-evidence."""
        state = create_eprocess("test_tile")
        state_new = update_eprocess(
            state, new_pvalue=0.01, quality_weight=0.9, adapt_kappa=False
        )
        assert state_new.log_evidence > 0.0

    def test_evidence_decreases_with_high_pvalue(self):
        """A high p-value should decrease the log-evidence (or increase slowly)."""
        state = create_eprocess("test_tile")
        state_new = update_eprocess(
            state, new_pvalue=0.99, quality_weight=0.9, adapt_kappa=False
        )
        assert state_new.log_evidence < 0.0

    def test_confirmed_state_persists(self):
        """Once confirmed, the state should remain confirmed."""
        state = create_eprocess("test_tile")
        state.is_confirmed = True
        state.confirmation_step = 5

        state_new = update_eprocess(
            state, new_pvalue=0.99, quality_weight=0.9
        )
        assert state_new.is_confirmed
        assert state_new.confirmation_step == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
