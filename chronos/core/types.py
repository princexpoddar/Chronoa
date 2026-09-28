"""
CHRONOS Core Type Definitions.

Pydantic models and data classes for tiles, observations, harmonic coefficients,
change candidates, strata, and conformal results. These are the foundational
data structures shared across every CHRONOS subsystem.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Sensor(str, enum.Enum):
    """Supported satellite sensor platforms."""
    SENTINEL2_L2A = "S2_L2A"
    SENTINEL1_GRD = "S1_GRD"
    LANDSAT8_C2 = "L8_C2"
    LANDSAT9_C2 = "L9_C2"
    HLS_S30 = "HLS_S30"
    HLS_L30 = "HLS_L30"
    BHUVAN = "BHUVAN"


class ChangeType(str, enum.Enum):
    """Supported change type labels for conformal prediction sets."""
    CONSTRUCTION = "construction"
    CLEARANCE = "clearance"
    WATER_EXTENT = "water_extent"
    ROAD_DEVELOPMENT = "road_development"
    VEGETATION_LOSS = "vegetation_loss"
    VEGETATION_GAIN = "vegetation_gain"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    APPEARANCE = "appearance"
    DISAPPEARANCE = "disappearance"
    UNKNOWN = "unknown"


class ChangeMode(str, enum.Enum):
    """Operating mode selected automatically based on observation density."""
    MODE_A = "harmonic_timeseries"    # ≥18 usable observations, ≥1.5 yr span
    MODE_B = "short_timeseries"       # 3–17 observations or <1.5 yr
    MODE_C = "bitemporal"             # 2 epochs only


class ReliefClass(str, enum.Enum):
    """Terrain relief classification from CartoDEM."""
    FLAT = "flat"             # slope < 5°
    MODERATE = "moderate"     # 5° ≤ slope < 15°
    STEEP = "steep"           # 15° ≤ slope < 30°
    RUGGED = "rugged"         # slope ≥ 30°


# ---------------------------------------------------------------------------
# Numpy-backed value objects (not Pydantic — these carry array payloads)
# ---------------------------------------------------------------------------

class NumpyArrayMixin:
    """Mixin providing shape and dtype introspection for array-backed objects."""

    def _validate_array(self, arr: np.ndarray, name: str,
                        expected_ndim: Optional[int] = None,
                        expected_shape: Optional[tuple] = None) -> np.ndarray:
        arr = np.asarray(arr, dtype=np.float64)
        if expected_ndim is not None and arr.ndim != expected_ndim:
            raise ValueError(
                f"{name}: expected ndim={expected_ndim}, got {arr.ndim}"
            )
        if expected_shape is not None and arr.shape != expected_shape:
            raise ValueError(
                f"{name}: expected shape={expected_shape}, got {arr.shape}"
            )
        return arr


class HarmonicCoefficients(NumpyArrayMixin):
    """
    Fitted harmonic embedding field parameters for a single tile.

    Attributes
    ----------
    theta : np.ndarray, shape (m, d)
        Coefficient matrix Θ̂_i where m = 2K+2 (design matrix columns) and
        d = embedding dimension. For K=2: m=6 → [intercept, trend, cos ω, sin ω, cos 2ω, sin 2ω].
    v_sem : np.ndarray, shape (d,)
        Season-invariant semantic vector: α̂_i + β̂_i · t̄_mid.
    v_phen : np.ndarray, shape (4,)
        Phenological fingerprint: [A₁, φ₁, A₂, φ₂] (amplitudes and phases of K=2 harmonics).
    P : np.ndarray, shape (m, m)
        Recursive covariance matrix for Sherman–Morrison online updates.
    mad_scale : float
        Median Absolute Deviation scale estimate σ̂ from IRLS.
    n_obs : int
        Number of usable observations used in the fit.
    last_updated : datetime
        Timestamp of the most recent update.
    """

    __slots__ = ("theta", "v_sem", "v_phen", "P", "mad_scale", "n_obs", "last_updated")

    def __init__(self, theta: np.ndarray, v_sem: np.ndarray, v_phen: np.ndarray,
                 P: np.ndarray, mad_scale: float, n_obs: int,
                 last_updated: Optional[datetime] = None):
        self.theta = self._validate_array(theta, "theta", expected_ndim=2)
        m = self.theta.shape[0]
        d = self.theta.shape[1]
        self.v_sem = self._validate_array(v_sem, "v_sem", expected_shape=(d,))
        self.v_phen = self._validate_array(v_phen, "v_phen", expected_shape=(4,))
        self.P = self._validate_array(P, "P", expected_shape=(m, m))
        self.mad_scale = float(mad_scale)
        self.n_obs = int(n_obs)
        self.last_updated = last_updated or datetime.utcnow()

    @property
    def m(self) -> int:
        """Number of harmonic design matrix columns."""
        return self.theta.shape[0]

    @property
    def d(self) -> int:
        """Embedding dimension."""
        return self.theta.shape[1]


# ---------------------------------------------------------------------------
# Pydantic models (serializable, used in API / DB layers)
# ---------------------------------------------------------------------------

class StratumKey(BaseModel):
    """
    Mondrian stratum key κ for conformal calibration.

    Each tile is assigned to a stratum defined by its land-cover class,
    seasonal bucket, sensor, and terrain relief class. Conformal thresholds
    are calibrated independently per stratum.
    """
    model_config = ConfigDict(frozen=True)

    land_cover: str = Field(
        ..., description="Land-cover class label (e.g. 'cropland', 'urban', 'forest')"
    )
    season_bucket: int = Field(
        ..., ge=0, le=11,
        description="Season bucket index: floor(day_of_year / 30)"
    )
    sensor: Sensor = Field(
        ..., description="Acquisition sensor platform"
    )
    relief: ReliefClass = Field(
        ..., description="Terrain relief class from DEM"
    )


class ObservationRecord(BaseModel):
    """
    A single satellite observation of a tile at one point in time.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tile_id: str = Field(..., description="Unique tile identifier (MGRS + grid index)")
    timestamp: datetime = Field(..., description="Acquisition timestamp (UTC)")
    sensor: Sensor = Field(..., description="Source sensor platform")
    raster_path: str = Field(..., description="Path to the source COG raster file")
    quality_weight: float = Field(
        ..., ge=0.0, le=1.0,
        description="Composite quality weight q_i(t) ∈ [0, 1]"
    )
    cloud_fraction: float = Field(0.0, ge=0.0, le=1.0)
    shadow_fraction: float = Field(0.0, ge=0.0, le=1.0)
    haze_opacity: float = Field(0.0, ge=0.0)
    coregistration_shift_px: float = Field(0.0, ge=0.0)
    sun_elevation_deg: float = Field(0.0)
    view_angle_deg: float = Field(0.0)
    is_usable: bool = Field(
        True,
        description="Whether q_i(t) ≥ q_min and this observation should be used"
    )
    stac_item_id: Optional[str] = Field(None, description="STAC catalog item ID")


class TileInfo(BaseModel):
    """
    Static metadata for a tile in the analysis grid.
    """
    tile_id: str = Field(..., description="Unique tile identifier")
    mgrs_tile: str = Field(..., description="MGRS tile code (e.g. '43RGN')")
    center_lat: float = Field(..., ge=-90, le=90)
    center_lon: float = Field(..., ge=-180, le=180)
    elevation_m: float = Field(0.0, description="Mean elevation from CartoDEM (m)")
    aspect_deg: float = Field(0.0, ge=0, le=360, description="Mean terrain aspect (°)")
    slope_deg: float = Field(0.0, ge=0, le=90, description="Mean terrain slope (°)")
    relief: ReliefClass = Field(ReliefClass.FLAT)
    land_cover: str = Field("unknown", description="Dominant land-cover class")
    bbox_wkt: Optional[str] = Field(None, description="WKT polygon in EPSG:4326")


class ConformalResult(BaseModel):
    """
    Output of the conformal calibration pipeline for a single tile-epoch.
    """
    tile_id: str
    timestamp: datetime
    stratum: StratumKey
    nonconformity_score: float = Field(
        ..., description="Mahalanobis score s_i(t)"
    )
    conformal_pvalue: float = Field(
        ..., ge=0.0, le=1.0,
        description="Smoothed conformal p-value p_i(t)"
    )
    by_adjusted_q: float = Field(
        ..., ge=0.0, le=1.0,
        description="Benjamini–Yekutieli adjusted q-value"
    )
    is_flagged: bool = Field(
        False, description="Whether this exceeds the BY-FDR threshold"
    )


class EProcessState(BaseModel):
    """
    Running state of the anytime-valid conformal test martingale for a tile.
    """
    tile_id: str
    log_evidence: float = Field(
        0.0,
        description="log(E_i(t)) — accumulated log-evidence from the e-process"
    )
    n_updates: int = Field(0, description="Number of multiplicative updates applied")
    is_confirmed_change: bool = Field(
        False,
        description="True if E_i(t) ≥ 1/α (Ville's inequality exceeded)"
    )
    last_update: Optional[datetime] = None


class ChangeDateEstimate(BaseModel):
    """
    Observability-bounded change date triple (t⁻, t⁺, G).
    """
    tile_id: str
    t_minus: Optional[datetime] = Field(
        None, description="Last clean null observation before change"
    )
    t_plus: Optional[datetime] = Field(
        None, description="First usable confirmation observation"
    )
    gap_timestamps: list[datetime] = Field(
        default_factory=list,
        description="Timestamps of unusable observations in (t⁻, t⁺)"
    )
    gap_days: float = Field(
        0.0, description="Total calendar days spanned by the gap"
    )
    sar_narrowed: bool = Field(
        False,
        description="Whether SAR observations narrowed the interval"
    )


class ChangeCandidate(BaseModel):
    """
    A fully assembled change detection candidate ready for the review queue.
    """
    tile_id: str
    mode: ChangeMode
    conformal: ConformalResult
    eprocess: EProcessState
    dating: ChangeDateEstimate
    predicted_types: list[ChangeType] = Field(
        default_factory=list,
        description="Conformal prediction set Ŷ_i with 1-α_cls coverage"
    )
    type_confidence: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Max softmax probability across predicted types"
    )
    polygon_wkt: Optional[str] = Field(
        None, description="Polygonized change footprint in WKT (EPSG:4326)"
    )
    area_m2: float = Field(0.0, ge=0.0, description="Change polygon area in m²")
    rank_score: float = Field(
        0.0, description="Combined ranking score for the review queue"
    )


class AnalystDecision(str, enum.Enum):
    """Analyst review decision on a change candidate."""
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    RECLASSIFIED = "reclassified"
    DEFERRED = "deferred"


class AuditRecord(BaseModel):
    """
    A single entry in the tamper-evident hash-chained audit trail.
    """
    record_id: int
    candidate_id: str
    analyst_id: str
    decision: AnalystDecision
    reclassified_types: Optional[list[ChangeType]] = None
    rationale: str = ""
    timestamp: datetime
    prev_hash: str = Field(
        ..., description="SHA-256 hash of the previous audit record"
    )
    current_hash: str = Field(
        ..., description="SHA-256(canonical_json(this_record) || prev_hash)"
    )
