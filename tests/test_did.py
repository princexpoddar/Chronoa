"""
Tests for the CHRONOS Difference-in-Differences estimator.

Validates:
    1. Common atmospheric shocks are cancelled by cohort median subtraction
    2. Localised change signals are preserved after DiD
    3. Phenological distance is circular-aware
    4. Terrain constraints correctly filter cohort membership
"""

import numpy as np
import pytest

from chronos.core.did import (
    build_control_cohort,
    compute_did_residuals_batched,
    _phenological_distance,
    DEFAULT_K_NEIGHBOURS,
)


class TestPhenologicalDistance:
    """Tests for the circular-aware phenological distance function."""

    def test_zero_distance_identical(self):
        """Identical fingerprints should have zero distance."""
        target = np.array([1.0, 0.5, 0.3, 1.2])
        candidates = target.reshape(1, -1)
        dist = _phenological_distance(target, candidates)
        assert dist[0] == pytest.approx(0.0, abs=1e-10)

    def test_phase_wraparound(self):
        """Phase difference should wrap correctly (φ=0 ≈ φ=2π)."""
        target = np.array([1.0, 0.01, 0.5, 0.0])
        # Nearly identical but phase wrapped
        candidate = np.array([[1.0, 2 * np.pi - 0.01, 0.5, 0.0]])
        dist = _phenological_distance(target, candidate)
        assert dist[0] < 0.1  # Should be very small

    def test_amplitude_dominates(self):
        """Large amplitude differences should dominate over phase differences."""
        target = np.array([1.0, 0.0, 0.5, 0.0])
        # Same phase, very different amplitude
        candidate = np.array([[5.0, 0.0, 0.5, 0.0]])
        dist = _phenological_distance(target, candidate)
        assert dist[0] > 3.0  # Significant distance


class TestCohortConstruction:
    """Tests for control cohort building."""

    def test_self_excluded(self):
        """Target tile should never appear in its own cohort."""
        target_id = "tile_5"
        all_ids = [f"tile_{i}" for i in range(20)]
        all_phen = np.random.randn(20, 4)
        all_elev = np.ones(20) * 100.0
        all_aspect = np.ones(20) * 180.0

        result = build_control_cohort(
            target_tile_id=target_id,
            target_v_phen=all_phen[5],
            target_elevation=100.0,
            target_aspect=180.0,
            all_tile_ids=all_ids,
            all_v_phen=all_phen,
            all_elevations=all_elev,
            all_aspects=all_aspect,
        )
        assert target_id not in result.cohort_ids

    def test_elevation_constraint(self):
        """Tiles outside elevation band should be excluded."""
        all_ids = [f"tile_{i}" for i in range(10)]
        all_phen = np.zeros((10, 4))  # All identical phenology
        # Elevation: tiles 0-4 at 100m, tiles 5-9 at 5000m
        all_elev = np.array([100] * 5 + [5000] * 5, dtype=float)
        all_aspect = np.ones(10) * 180.0

        result = build_control_cohort(
            target_tile_id="tile_0",
            target_v_phen=np.zeros(4),
            target_elevation=100.0,
            target_aspect=180.0,
            all_tile_ids=all_ids,
            all_v_phen=all_phen,
            all_elevations=all_elev,
            all_aspects=all_aspect,
            elev_band=200.0,
        )

        # Only tiles 1-4 should be eligible (same elevation band, excluding self)
        for cid in result.cohort_ids:
            idx = int(cid.split("_")[1])
            assert idx < 5, f"Tile {cid} should be excluded (wrong elevation band)"

    def test_cohort_size_capped(self):
        """Cohort size should not exceed k."""
        all_ids = [f"tile_{i}" for i in range(200)]
        all_phen = np.random.randn(200, 4) * 0.01
        all_elev = np.ones(200) * 100.0
        all_aspect = np.ones(200) * 180.0

        result = build_control_cohort(
            target_tile_id="tile_0",
            target_v_phen=all_phen[0],
            target_elevation=100.0,
            target_aspect=180.0,
            all_tile_ids=all_ids,
            all_v_phen=all_phen,
            all_elevations=all_elev,
            all_aspects=all_aspect,
            k=32,
        )
        assert len(result.cohort_ids) == 32


class TestDiDResiduals:
    """Tests for DiD residual computation."""

    def test_common_shock_cancelled(self):
        """
        A common atmospheric shock τ(t) injected across all tiles should be
        cancelled by cohort median subtraction, while localised signal c_i(t)
        should be preserved.
        """
        T, d = 20, 4
        n_cohort = 30

        rng = np.random.default_rng(42)

        # Common atmospheric shock (same for all tiles at each timestep)
        atmospheric_shock = rng.standard_normal((T, d)) * 2.0

        # Cohort raw residuals: only atmospheric shock + small noise
        cohort_residuals = np.tile(atmospheric_shock, (n_cohort, 1, 1))  # (30, 20, 4)
        cohort_residuals += rng.normal(0, 0.05, cohort_residuals.shape)

        # Target: atmospheric shock + localised change signal at t=15
        target_residuals = atmospheric_shock.copy()
        change_signal = np.array([3.0, -2.0, 1.5, 0.8])
        target_residuals[15] += change_signal

        # Compute DiD
        did = compute_did_residuals_batched(target_residuals, cohort_residuals)

        # At t=15, the DiD residual should reflect the change signal
        np.testing.assert_allclose(did[15], change_signal, atol=0.3)

        # At other timesteps, DiD residual should be near zero
        for t in [0, 5, 10, 19]:
            assert np.linalg.norm(did[t]) < 0.5, (
                f"DiD residual at t={t} should be near zero, got norm={np.linalg.norm(did[t]):.3f}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
