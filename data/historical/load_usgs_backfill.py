"""
USGS Backfill Loader
====================
Loads USGS GeoJSON earthquake data into Neo4j.
Covers the gap from January 2025 to present.

Usage:
    cd japanese_earth_quake_project
    python data/historical/load_usgs_backfill.py
"""

import json
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import os

load_dotenv()

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

USGS_FILE = Path(__file__).parent / "usgs_2025_2026.json"


def load_usgs(filepath: Path) -> list[dict]:
    with open(filepath) as f:
        data = json.load(f)
    features = data["features"]
    print(f"Loaded {len(features)} USGS events")
    return features


def parse_feature(f: dict) -> dict | None:
    props = f.get("properties", {})
    geom  = f.get("geometry", {})
    coords = geom.get("coordinates", [])

    if len(coords) < 3:
        return None

    lon, lat, depth = coords[0], coords[1], abs(coords[2])
    mag  = props.get("mag")
    time = props.get("time")  # milliseconds since epoch
    place = props.get("place", "")
    usgs_id = f.get("id", "")

    if not all([lat, lon, mag, time, usgs_id]):
        return None

    # Convert ms timestamp to ISO datetime
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(time / 1000, tz=timezone.utc)

    # Infer fault type from location and depth
    fault_type = "unknown"
    if depth > 150:
        fault_type = "subduction"
    elif lon > 141.0 and lat > 35.0 and depth < 100:
        fault_type = "subduction"
    elif lon < 136.0 and lat < 34.0:
        fault_type = "subduction"
    elif depth < 20:
        fault_type = "strike-slip"
    elif 20 <= depth <= 60 and 130 <= lon <= 141:
        fault_type = "reverse"
    else:
        fault_type = "subduction"

    return {
        "id"                  : f"usgs_{usgs_id}",
        "occurrenceDateTime"  : dt.isoformat(),
        "epicentreLat"        : lat,
        "epicentreLon"        : lon,
        "hypocentralDepthKm"  : depth,
        "momentMagnitude"     : mag,
        "place"               : place,
        "faultType"           : fault_type,
        "year"                : dt.year,
        "source"              : "USGS_BACKFILL",
    }


def load_to_neo4j(events: list[dict]):
    driver = GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    batch_size = 100
    total = len(events)
    loaded = 0
    skipped = 0

    with driver.session() as session:
        for i in range(0, total, batch_size):
            batch = events[i:i + batch_size]
            session.run("""
                UNWIND $batch AS e
                MERGE (eq:Earthquake {id: e.id})
                SET eq.occurrenceDateTime = e.occurrenceDateTime,
                    eq.epicentreLat       = e.epicentreLat,
                    eq.epicentreLon       = e.epicentreLon,
                    eq.hypocentralDepthKm = e.hypocentralDepthKm,
                    eq.momentMagnitude    = e.momentMagnitude,
                    eq.place              = e.place,
                    eq.faultType          = e.faultType,
                    eq.year               = e.year,
                    eq.source             = e.source
            """, batch=batch)
            loaded += len(batch)
            print(f"  Loaded {min(loaded, total)} / {total}")

    driver.close()
    print(f"\nDone. {loaded} events loaded to Neo4j.")


def run():
    features = load_usgs(USGS_FILE)

    events = []
    for f in features:
        parsed = parse_feature(f)
        if parsed:
            events.append(parsed)
        
    print(f"Parsed {len(events)} valid events")
    print(f"Skipped {len(features) - len(events)} invalid events")
    print()

    load_to_neo4j(events)

    print()
    print("Next steps:")
    print("  1. Run GEBCO enrichment to add seaFloorDepthM")
    print("  2. Restart uvicorn — dots will appear on the map")


if __name__ == "__main__":
    run()
