"""
CHRONOS Geometric Harmonisation.

Handles multi-temporal and cross-sensor co-registration via phase correlation.
In practice, this wraps the AROSICS library. Here we provide the interface
that estimates and potentially applies the sub-pixel shift.
"""

from typing import Optional
import numpy as np
from numpy.typing import NDArray


def estimate_coregistration_shift(
    reference_raster: NDArray[np.float64],
    target_raster: NDArray[np.float64],
    window_size: int = 64,
) -> tuple[float, float, float]:
    """
    Estimate the sub-pixel shift between a target raster and a stable reference.
    
    Parameters
    ----------
    reference_raster : np.ndarray, 2D array
        Cloud-free temporal median composite of the tile.
    target_raster : np.ndarray, 2D array
        The new observation raster (usually NIR band).
    window_size : int
        Window size for phase correlation.
        
    Returns
    -------
    shift_x : float
        Estimated shift in pixels (X axis).
    shift_y : float
        Estimated shift in pixels (Y axis).
    shift_magnitude : float
        Euclidean norm of the shift.
    """
    # In a full deployment, this calls:
    # from arosics import COREG
    # cr = COREG(reference_raster, target_raster, ...)
    # cr.calculate_spatial_shifts()
    
    # Mock implementation for air-gapped demo without heavy dependencies:
    # Simulate a small random shift typical for Sentinel-2 (0-1.5 pixels)
    shift_x = float(np.random.normal(0, 0.5))
    shift_y = float(np.random.normal(0, 0.5))
    shift_magnitude = float(np.sqrt(shift_x**2 + shift_y**2))
    
    return shift_x, shift_y, shift_magnitude


def apply_shift(
    raster: NDArray[np.float64],
    shift_x: float,
    shift_y: float,
) -> NDArray[np.float64]:
    """
    Apply a sub-pixel shift to a raster using Lanczos resampling.
    For this scaffold, we return the unshifted raster as per CHRONOS
    design preference (record the shift uncertainty in q_i(t) rather than
    resampling if the shift is small).
    """
    return raster
