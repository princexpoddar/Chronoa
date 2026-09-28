"""
CHRONOS Tier-1 Physical Features.

Fast, pure-numpy computation of domain-standard spectral indices and
SAR backscatter properties. These features are computationally cheap and
act as a highly effective screening layer before invoking expensive
Tier-2 foundation models.
"""

import numpy as np
from numpy.typing import NDArray


def extract_optical_indices(
    raster: NDArray[np.float64],
    band_mapping: dict[str, int]
) -> dict[str, NDArray[np.float64]]:
    """
    Extract common physical indices from optical multispectral data.
    
    Parameters
    ----------
    raster : np.ndarray, shape (bands, height, width)
        Surface reflectance scaled to [0, 1].
    band_mapping : dict
        Mapping of band names (e.g. 'B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2')
        to channel indices.
        
    Returns
    -------
    dict
        Dictionary of extracted 2D index arrays.
    """
    # Safe division helper
    def safe_divide(num, den, fill=0.0):
        with np.errstate(divide='ignore', invalid='ignore'):
            res = np.where(den != 0, num / den, fill)
        return np.clip(res, -1.0, 1.0)

    indices = {}
    
    b_G = raster[band_mapping.get('G', 1)]
    b_R = raster[band_mapping.get('R', 2)]
    b_NIR = raster[band_mapping.get('NIR', 3)]
    
    if 'SWIR1' in band_mapping:
        b_SWIR1 = raster[band_mapping['SWIR1']]
        indices['NDBI'] = safe_divide(b_SWIR1 - b_NIR, b_SWIR1 + b_NIR)
        indices['MNDWI'] = safe_divide(b_G - b_SWIR1, b_G + b_SWIR1)
    
    if 'SWIR2' in band_mapping:
        b_SWIR2 = raster[band_mapping['SWIR2']]
        indices['NBR'] = safe_divide(b_NIR - b_SWIR2, b_NIR + b_SWIR2)

    indices['NDVI'] = safe_divide(b_NIR - b_R, b_NIR + b_R)
    indices['NDWI'] = safe_divide(b_G - b_NIR, b_G + b_NIR)
    
    # Bare Soil Index (BSI)
    if 'B' in band_mapping and 'SWIR1' in band_mapping:
        b_B = raster[band_mapping['B']]
        num = (b_SWIR1 + b_R) - (b_NIR + b_B)
        den = (b_SWIR1 + b_R) + (b_NIR + b_B)
        indices['BSI'] = safe_divide(num, den)

    return indices


def extract_sar_features(
    raster: NDArray[np.float64],
    band_mapping: dict[str, int]
) -> dict[str, NDArray[np.float64]]:
    """
    Extract physical features from SAR (Sentinel-1 GRD) backscatter.
    """
    def safe_divide(num, den, fill=0.0):
        with np.errstate(divide='ignore', invalid='ignore'):
            res = np.where(den != 0, num / den, fill)
        return res

    features = {}
    
    if 'VV' in band_mapping:
        vv = raster[band_mapping['VV']]
        features['SIGMA0_VV'] = vv
        
        if 'VH' in band_mapping:
            vh = raster[band_mapping['VH']]
            features['SIGMA0_VH'] = vh
            features['CROSS_RATIO'] = safe_divide(vh, vv)
            
    return features


def compute_tier1_embedding(
    optical_indices: dict[str, NDArray[np.float64]],
    sar_features: dict[str, NDArray[np.float64]],
) -> NDArray[np.float64]:
    """
    Pool patch-level or tile-level arrays into a single vector representation
    for fast Tier-1 harmonic screening.
    """
    means = []
    
    # Combine values
    for val in optical_indices.values():
        means.append(float(np.nanmean(val)))
        
    for val in sar_features.values():
        means.append(float(np.nanmean(val)))
        
    if not means:
        return np.zeros(1)
        
    return np.array(means, dtype=np.float64)
