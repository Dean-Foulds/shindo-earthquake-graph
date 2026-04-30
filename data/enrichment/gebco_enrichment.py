import numpy as np
from scipy.interpolate import RegularGridInterpolator
from netCDF4 import Dataset
from neo4j import GraphDatabase

from dotenv import load_dotenv
import os

load_dotenv()  # reads your .env file automatically

GEBCO_FILE  = "gebco_2026_n50.0_s20.0_w120.0_e150.0.nc"
NEO4J_URI   = os.getenv("NEO4J_URI")
NEO4J_USER  = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS  = os.getenv("NEO4J_PASSWORD")

# ── Load GEBCO NetCDF ─────────────────────────────────────
def load_gebco(filepath: str):
    """
    Loads the GEBCO NetCDF file and returns
    an interpolator function.
    Negative values = below sea level (ocean floor)
    Positive values = above sea level (land)
    """
    print("Loading GEBCO data...")
    ds         = Dataset(filepath)
    lats       = ds.variables["lat"][:]
    lons       = ds.variables["lon"][:]
    elevations = ds.variables["elevation"][:].astype(float)

    print(f"Grid size: {elevations.shape}")

    interpolator = RegularGridInterpolator(
        (lats, lons),
        elevations,
        method       = "nearest",
        bounds_error = False,
        fill_value   = None
    )

    print("GEBCO loaded ✅")
    return interpolator


# ── Neo4j ─────────────────────────────────────────────────
class AuraEnricher:

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(
            uri, auth=(user, password)
        )

    def get_all_earthquakes(self) -> list[dict]:
        """Fetch all earthquake nodes that need enriching."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Earthquake)
                WHERE e.seaFloorDepthM IS NULL
                RETURN e.id           AS id,
                       e.epicentreLat AS lat,
                       e.epicentreLon AS lon
            """)
            return [dict(r) for r in result]

    def write_depths_batch(self, updates: list[dict]):
        """
        Writes all depths to Aura in one batch transaction.
        Each update is {id, depth}
        """
        with self.driver.session() as session:
            session.run("""
                UNWIND $updates AS u
                MATCH (e:Earthquake {id: u.id})
                SET e.seaFloorDepthM = u.depth
            """, updates=updates)

    def close(self):
        self.driver.close()


# ── Main ──────────────────────────────────────────────────
def run():
    # Load GEBCO
    interpolator = load_gebco(GEBCO_FILE)

    # Connect to Aura
    print("Connecting to Aura...")
    enricher = AuraEnricher(NEO4J_URI, NEO4J_USER, NEO4J_PASS)

    # Fetch all earthquake nodes
    print("Fetching earthquake nodes...")
    earthquakes = enricher.get_all_earthquakes()
    total       = len(earthquakes)
    print(f"Found {total} nodes to enrich")

    if total == 0:
        print("Nothing to enrich — all nodes already have seaFloorDepthM")
        enricher.close()
        return

    # Look up all depths at once using numpy (very fast)
    print("Looking up depths from GEBCO...")
    coords = np.array([[e["lat"], e["lon"]] for e in earthquakes])
    depths = interpolator(coords)

    # Build update list
    updates = [
        {"id": eq["id"], "depth": float(depth)}
        for eq, depth in zip(earthquakes, depths)
    ]

    # Write to Aura in batches of 1000
    print("Writing to Aura...")
    batch_size = 1000
    for i in range(0, len(updates), batch_size):
        batch = updates[i : i + batch_size]
        enricher.write_depths_batch(batch)
        print(f"  Written {min(i + batch_size, total)} / {total}")

    enricher.close()
    print()
    print(f"Done — {total} nodes enriched with sea floor depth ✅")


if __name__ == "__main__":
    run()