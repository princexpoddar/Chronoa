"""
CHRONOS STAC (SpatioTemporal Asset Catalog) Integration.

Handles reading and writing STAC Items for ingestion and export, ensuring
that provenance, georeferencing, and acquisition metadata are preserved end-to-end
as required by R6.4.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pystac
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.view import ViewExtension
from pystac.extensions.sat import SatExtension

from chronos.core.types import Sensor


def create_stac_item(
    item_id: str,
    geometry: dict[str, Any],
    bbox: list[float],
    datetime_utc: datetime,
    sensor: Sensor,
    asset_href: str,
    cloud_cover: float = 0.0,
    sun_elevation: Optional[float] = None,
    sun_azimuth: Optional[float] = None,
    view_angle: Optional[float] = None,
    epsg: Optional[int] = None,
) -> pystac.Item:
    """
    Create a STAC Item representing a single satellite acquisition.
    
    Parameters
    ----------
    item_id : str
        Unique identifier for the item (e.g., scene ID).
    geometry : dict
        GeoJSON geometry polygon.
    bbox : list[float]
        Bounding box [minx, miny, maxx, maxy].
    datetime_utc : datetime
        Acquisition timestamp.
    sensor : Sensor
        Sensor platform enum.
    asset_href : str
        Path or URI to the COG/GeoTIFF raster data.
    cloud_cover : float
        Percentage of cloud cover (0-100).
    sun_elevation : float, optional
        Solar elevation angle.
    sun_azimuth : float, optional
        Solar azimuth angle.
    view_angle : float, optional
        Off-nadir viewing angle.
    epsg : int, optional
        EPSG code for the projection.
        
    Returns
    -------
    pystac.Item
        Constructed STAC item with extensions applied.
    """
    item = pystac.Item(
        id=item_id,
        geometry=geometry,
        bbox=bbox,
        datetime=datetime_utc,
        properties={}
    )

    # Core metadata
    item.common_metadata.platform = sensor.name.split("_")[0]
    item.common_metadata.instruments = [sensor.value]

    # EO Extension (Cloud Cover)
    eo_ext = EOExtension.ext(item, add_if_missing=True)
    eo_ext.cloud_cover = cloud_cover

    # View Extension (Sun/Sensor Geometry)
    if sun_elevation is not None or sun_azimuth is not None or view_angle is not None:
        view_ext = ViewExtension.ext(item, add_if_missing=True)
        if sun_elevation is not None:
            view_ext.sun_elevation = sun_elevation
        if sun_azimuth is not None:
            view_ext.sun_azimuth = sun_azimuth
        if view_angle is not None:
            view_ext.off_nadir = view_angle

    # Projection Extension
    if epsg is not None:
        proj_ext = ProjectionExtension.ext(item, add_if_missing=True)
        proj_ext.epsg = epsg

    # Add the primary data asset
    asset = pystac.Asset(
        href=asset_href,
        media_type=pystac.MediaType.COG,
        roles=["data"]
    )
    item.add_asset("data", asset)

    return item


def save_stac_item(item: pystac.Item, out_path: str | Path) -> None:
    """Save a STAC Item to disk as JSON."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(item.to_dict(), f, indent=2)


def load_stac_item(in_path: str | Path) -> pystac.Item:
    """Load a STAC Item from disk."""
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pystac.Item.from_dict(data)
