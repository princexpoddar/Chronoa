"""
CHRONOS Synthetic Data Generator.

Generates realistic mock time-series data for testing and local development
without requiring multi-gigabyte foundation model downloads or actual satellite
imagery access.

Simulates:
    - Phenological cycles (double-cropping signatures).
    - Atmospheric noise (haze, sporadic cloud cover).
    - Abrupt change events (construction, clearance) inserted at known times.
"""

from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from chronos.core.types import ObservationRecord, Sensor, ReliefClass
from chronos.core.harmonics import design_matrix, fractional_years


def generate_synthetic_tile_history(
    tile_id: str,
    start_date: datetime,
    end_date: datetime,
    revisit_days: int = 5,
    embedding_dim: int = 256,
    base_cloud_prob: float = 0.2,
    change_date: Optional[datetime] = None,
    change_magnitude: float = 5.0,
    phenology_amplitude: float = 1.5,
    sensor: Sensor = Sensor.SENTINEL2_L2A,
    seed: int = 42,
) -> tuple[list[ObservationRecord], NDArray[np.float64], NDArray[np.float64]]:
    """
    Generate a full synthetic history for a single tile.

    Parameters
    ----------
    tile_id : str
        ID of the tile.
    start_date : datetime
        Start of the time series.
    end_date : datetime
        End of the time series.
    revisit_days : int
        Days between acquisitions.
    embedding_dim : int
        Dimensionality of the synthetic embeddings (e.g. 256 for Matryoshka-truncated).
    base_cloud_prob : float
        Probability of severe cloud cover per observation.
    change_date : datetime, optional
        Date at which an abrupt physical change occurs.
    change_magnitude : float
        L2 magnitude of the change vector injected into the embeddings.
    phenology_amplitude : float
        Amplitude of the simulated seasonal cycle.
    sensor : Sensor
        Sensor platform string.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    records : list[ObservationRecord]
        List of metadata records including quality weights.
    embeddings : np.ndarray, shape (T, d)
        Synthetic embedding vectors.
    true_change_vector : np.ndarray, shape (d,)
        The injected change vector (zeros if change_date is None).
    """
    rng = np.random.default_rng(seed)

    # 1. Generate timestamps
    timestamps = []
    current = start_date
    while current <= end_date:
        timestamps.append(current)
        current += timedelta(days=revisit_days)
    
    T = len(timestamps)
    
    # 2. Base Harmonic Profile
    # [intercept, trend, cos(w), sin(w), cos(2w), sin(2w)]
    true_theta = rng.standard_normal((6, embedding_dim)) * 0.1
    true_theta[0, :] = rng.uniform(-1, 1, embedding_dim)  # Baseline identity
    true_theta[1, :] = 0.0  # Zero trend
    # Significant seasonal variation
    true_theta[2:6, :] *= phenology_amplitude

    t_bars = fractional_years(timestamps)
    H = design_matrix(t_bars)
    
    embeddings = H @ true_theta  # (T, d)

    # 3. Add sensor noise
    embeddings += rng.normal(0, 0.2, (T, embedding_dim))

    # 4. Inject structural change
    change_vector = np.zeros(embedding_dim)
    if change_date is not None:
        direction = rng.standard_normal(embedding_dim)
        direction /= np.linalg.norm(direction)
        change_vector = direction * change_magnitude
        
        for i, t in enumerate(timestamps):
            if t >= change_date:
                embeddings[i] += change_vector

    # 5. Generate Observation Records & Quality Weights
    records = []
    
    for i, t in enumerate(timestamps):
        # Simulate cloud/shadow/haze
        is_cloudy = rng.random() < base_cloud_prob
        cloud_frac = rng.uniform(0.6, 1.0) if is_cloudy else rng.uniform(0.0, 0.1)
        haze_opac = rng.uniform(0.0, 0.5)
        
        # Simulated quality equation
        q = (1.0 - cloud_frac) * np.exp(-haze_opac / 0.2)
        q = np.clip(q, 0.0, 1.0)
        
        if is_cloudy:
            # Degrade the embedding with arbitrary cloud signature
            embeddings[i] += rng.normal(0, 3.0, embedding_dim)

        rec = ObservationRecord(
            tile_id=tile_id,
            timestamp=t,
            sensor=sensor,
            raster_path=f"s3://mock-bucket/scene_{t.strftime('%Y%m%d')}.tif",
            quality_weight=float(q),
            cloud_fraction=float(cloud_frac),
            haze_opacity=float(haze_opac),
            is_usable=bool(q >= 0.2),
        )
        records.append(rec)

    return records, embeddings, change_vector
