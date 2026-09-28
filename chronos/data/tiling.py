"""
CHRONOS Tiling Grid Generator.

Defines the fixed analysis grid over an Area of Interest (AOI).
Default grid configuration:
    - 224 x 224 pixels at 10m GSD -> 2.24 km x 2.24 km per tile
    - 50% overlap -> 1.12 km stride

This ensures sub-tile objects aren't arbitrarily cut by boundaries and
provides a two-fold coverage for candidate verification.
"""

from dataclasses import dataclass
from typing import Generator

from shapely.geometry import Polygon, box

from chronos.core.types import TileInfo, ReliefClass


@dataclass
class GridConfig:
    """Configuration for the analysis tile grid."""
    pixel_size_m: float = 10.0
    tile_size_px: int = 224
    overlap_fraction: float = 0.5

    @property
    def tile_size_m(self) -> float:
        return self.pixel_size_m * self.tile_size_px

    @property
    def stride_m(self) -> float:
        return self.tile_size_m * (1.0 - self.overlap_fraction)


def generate_tile_grid(
    aoi_bbox_proj: tuple[float, float, float, float],
    mgrs_code: str,
    config: GridConfig = GridConfig(),
) -> Generator[TileInfo, None, None]:
    """
    Generate a grid of overlapping tiles covering a projected bounding box.

    Parameters
    ----------
    aoi_bbox_proj : tuple
        (minx, miny, maxx, maxy) in the projected CRS (e.g., UTM).
    mgrs_code : str
        The MGRS zone/tile identifier (e.g. '43RGN') for provenance tracking.
    config : GridConfig
        Grid configuration parameters.

    Yields
    ------
    TileInfo
        A TileInfo object for each generated tile.
    """
    minx, miny, maxx, maxy = aoi_bbox_proj
    
    stride = config.stride_m
    size = config.tile_size_m

    # Number of steps
    nx = int((maxx - minx - size) / stride) + 2
    ny = int((maxy - miny - size) / stride) + 2

    # In a real implementation with pyproj, we would inverse-transform the
    # projected coordinates to WGS84 (lat/lon) for the TileInfo center_lat/lon.
    # For this mock/scaffold, we store the projected coordinates directly in
    # the lat/lon fields for simplicity.

    tile_idx = 0
    for i in range(nx):
        x0 = minx + i * stride
        x1 = x0 + size
        if x0 >= maxx:
            break

        for j in range(ny):
            y0 = miny + j * stride
            y1 = y0 + size
            if y0 >= maxy:
                break
                
            center_x = (x0 + x1) / 2.0
            center_y = (y0 + y1) / 2.0
            
            # WKT of the bounding box
            tile_box = box(x0, y0, x1, y1)
            
            yield TileInfo(
                tile_id=f"{mgrs_code}_{tile_idx:06d}",
                mgrs_tile=mgrs_code,
                center_lon=center_x,  # Typically projected back to WGS84
                center_lat=center_y,  # Typically projected back to WGS84
                elevation_m=0.0,      # To be populated from DEM
                aspect_deg=0.0,       # To be populated from DEM
                slope_deg=0.0,        # To be populated from DEM
                relief=ReliefClass.FLAT,
                bbox_wkt=tile_box.wkt,
            )
            tile_idx += 1
