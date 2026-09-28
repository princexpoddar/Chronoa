"""
CHRONOS Quality Masking Engine.

Handles Stage 2 quality assessment:
    1. Base cloud/shadow masks (SCL / QA_PIXEL / OmniCloudMask)
    2. Haze opacity estimation
    3. Layover/Shadow masks for SAR from CartoDEM

Calculates the composite quality weight q_i(t) ∈ [0, 1] that propagates
into the harmonic fitter and conformal e-process.
"""

import numpy as np
from numpy.typing import NDArray

from chronos.core.types import Sensor


def calculate_quality_weight(
    cloud_fraction: float,
    shadow_fraction: float,
    haze_opacity: float,
    registration_shift_px: float,
    layover_fraction: float = 0.0,
    sensor: Sensor = Sensor.SENTINEL2_L2A,
    haze_scale: float = 0.2,
    shift_scale: float = 2.0,
) -> float:
    """
    Calculate the composite quality weight q_i(t) for an observation.

    q = (1 - cloud) * (1 - shadow) * exp(-haze / h_0) * exp(-shift / s_0) * (1 - layover)

    Parameters
    ----------
    cloud_fraction : float
        Fraction of the tile covered by clouds (0.0 to 1.0).
    shadow_fraction : float
        Fraction covered by cloud shadows (0.0 to 1.0).
    haze_opacity : float
        Estimated haze opacity (AOT / aerosol optical thickness surrogate).
    registration_shift_px : float
        Co-registration residual error in pixels.
    layover_fraction : float
        For SAR: fraction of tile affected by layover or radar shadow.
    sensor : Sensor
        Sensor type. If SAR, layover is applied.
    haze_scale : float
        Decay constant h_0 for haze.
    shift_scale : float
        Decay constant s_0 for registration shift.

    Returns
    -------
    float
        Quality weight ∈ [0, 1].
    """
    cloud_fraction = np.clip(cloud_fraction, 0.0, 1.0)
    shadow_fraction = np.clip(shadow_fraction, 0.0, 1.0)
    layover_fraction = np.clip(layover_fraction, 0.0, 1.0)

    # Base optical/SAR common terms
    q = (1.0 - cloud_fraction) * (1.0 - shadow_fraction)

    # Haze penalty
    q *= np.exp(-max(haze_opacity, 0.0) / haze_scale)

    # Registration shift penalty
    q *= np.exp(-max(registration_shift_px, 0.0) / shift_scale)

    # SAR specific penalty
    if sensor == Sensor.SENTINEL1_GRD:
        q *= (1.0 - layover_fraction)

    return float(np.clip(q, 0.0, 1.0))


def mock_omnicloudmask(
    multi_spectral_raster: NDArray[np.float64],
) -> tuple[float, float, float]:
    """
    Mock implementation of OmniCloudMask (sensor-agnostic U-Net).
    In a real deployment, this loads the PyTorch ONNX model.
    For this scaffold, it returns heuristic cloud/shadow/haze fractions
    based on simple brightness/contrast thresholds.

    Parameters
    ----------
    multi_spectral_raster : np.ndarray, shape (bands, height, width)

    Returns
    -------
    cloud_fraction : float
    shadow_fraction : float
    haze_opacity : float
    """
    # Extremely simplified mock: assume band 1 is Blue, band 3 is NIR
    # Bright in Blue/NIR -> Cloud
    # Dark in NIR -> Shadow
    
    if multi_spectral_raster.shape[0] < 4:
        return 0.0, 0.0, 0.0
        
    blue = multi_spectral_raster[1]  # roughly B2 in S2
    nir = multi_spectral_raster[3]   # roughly B8 in S2
    
    cloud_mask = (blue > 0.15) & (nir > 0.15)
    shadow_mask = (blue < 0.05) & (nir < 0.05)
    
    cloud_frac = float(np.mean(cloud_mask))
    shadow_frac = float(np.mean(shadow_mask))
    haze = float(np.clip(np.mean(blue) - 0.05, 0.0, 0.5))
    
    return cloud_frac, shadow_frac, haze
