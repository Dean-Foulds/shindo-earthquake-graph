import asyncio
import numpy as np
from functools import lru_cache
from pathlib import Path
from scipy.interpolate import RegularGridInterpolator
from netCDF4 import Dataset

GEBCO_PATH = (
    Path(__file__).parents[4]
    / "data/enrichment"
    / "gebco_2026_n50.0_s20.0_w120.0_e150.0.nc"
)

DEFINITION = {
    "name": "get_sea_floor_depth",
    "description": (
        "Looks up the sea floor depth or land elevation at a given "
        "latitude and longitude using GEBCO 2026. "
        "Returns depth in metres — negative means ocean floor, "
        "positive means land above sea level. "
        "Always call this first before any tsunami or damage assessment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "latitude":  {
                "type": "number",
                "description": "Latitude of the point (24 to 50 for Japan)"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude of the point (120 to 150 for Japan)"
            }
        },
        "required": ["latitude", "longitude"]
    }
}

@lru_cache(maxsize=1)
def _load_interpolator():
    ds         = Dataset(str(GEBCO_PATH))
    lats       = ds.variables["lat"][:]
    lons       = ds.variables["lon"][:]
    elevations = ds.variables["elevation"][:].astype(float)
    return RegularGridInterpolator(
        (lats, lons), elevations,
        method="nearest", bounds_error=False, fill_value=None
    )

def _lookup(latitude: float, longitude: float) -> dict:
    interp = _load_interpolator()
    depth  = float(interp([[latitude, longitude]])[0])
    return {
        "latitude"        : latitude,
        "longitude"       : longitude,
        "sea_floor_depth" : round(depth, 1),
        "is_offshore"     : depth < 0,
        "description"     : (
            f"{'Ocean floor' if depth < 0 else 'Land'} at "
            f"{abs(depth):.0f}m "
            f"{'below' if depth < 0 else 'above'} sea level"
        )
    }

async def get_sea_floor_depth(latitude: float, longitude: float) -> dict:
    # Run sync netCDF lookup in thread pool to avoid blocking event loop
    return await asyncio.to_thread(_lookup, latitude, longitude)