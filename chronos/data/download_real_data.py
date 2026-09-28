"""
CHRONOS Data Downloader.

Programmatically fetches Sentinel-2 L2A data via STAC API (Earth Search v1)
for the Sutlej River Basin (Punjab), filtering for low cloud cover.
"""

import os
from pathlib import Path
from pystac_client import Client
import requests
from concurrent.futures import ThreadPoolExecutor

# Coordinates for Sutlej River Basin / Punjab Peri-Urban Corridor
BBOX = [75.7, 30.8, 76.3, 31.2]
EARTH_SEARCH_API = "https://earth-search.aws.element84.com/v1"

def download_asset(url: str, dest_path: Path):
    """Download a single asset to disk."""
    if dest_path.exists():
        print(f"Skipping (already downloaded): {dest_path.name}")
        return
        
    print(f"Downloading: {dest_path.name}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            
def fetch_real_data(out_dir: str = "data/raw", limit: int = 5):
    """Query STAC and download RGB/NIR GeoTIFF chips."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Connecting to STAC API: {EARTH_SEARCH_API}")
    catalog = Client.open(EARTH_SEARCH_API)
    
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=BBOX,
        datetime="2023-06-01/2023-12-31",
        query={"eo:cloud_cover": {"lt": 10}}, # Less than 10% cloud cover
        max_items=limit
    )
    
    items = list(search.items())
    print(f"Found {len(items)} scenes with <10% cloud cover.")
    
    assets_to_download = []
    
    for item in items:
        # We need Red (B04), Green (B03), Blue (B02) for visual
        # and NIR (B08) for physical features like NDVI
        for band in ["blue", "green", "red", "nir"]:
            if band in item.assets:
                asset_url = item.assets[band].href
                filename = f"{item.id}_{band}.tif"
                assets_to_download.append((asset_url, out_path / filename))
                
    # Download concurrently
    with ThreadPoolExecutor(max_workers=4) as executor:
        for url, dest in assets_to_download:
            executor.submit(download_asset, url, dest)
            
    print(f"Successfully downloaded {len(assets_to_download)} files to {out_dir}")

if __name__ == "__main__":
    # Ensure requests and pystac_client are installed
    try:
        import pystac_client
    except ImportError:
        print("Please install pystac-client: pip install pystac-client requests")
        exit(1)
        
    fetch_real_data()
