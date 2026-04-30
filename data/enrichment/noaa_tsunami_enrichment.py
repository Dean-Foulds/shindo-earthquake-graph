import json
from dotenv import load_dotenv
from neo4j import GraphDatabase
import os

load_dotenv(dotenv_path="../../.env")

NEO4J_URI  = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD")

NOAA_FILE  = "events.json"

# ── Load NOAA data ────────────────────────────────────────
def load_noaa(filepath: str) -> list[dict]:
    with open(filepath) as f:
        data = json.load(f)
    events = data["items"]
    print(f"Loaded {len(events)} NOAA tsunami events")
    return events

# ── Build tsunami properties from NOAA event ─────────────
def build_tsunami_props(event: dict) -> dict:
    props = {
        "noaaId":       int(event["id"]),
        "dataSource":   "NOAA_HISTORICAL",
        "locationName": event.get("locationName", ""),
    }

    field_map = {
        "maxWaterHeight":      ("waveHeightAtShoreM",      float),
        "eqMagnitude":         ("sourceMagnitude",         float),
        "eqDepth":             ("sourceDepthKm",           float),
        "tsIntensity":         ("tsunamiIntensity",        float),
        "tsMtIi":              ("iidaMagnitude",           float),
        "deaths":              ("tsunamiFatalities",       int),
        "deathsTotal":         ("tsunamiFatalitiesTotal",  int),
        "injuriesTotal":       ("tsunamiInjuriesTotal",    int),
        "housesDestroyedTotal":("buildingsWashedAway",     int),
        "numRunups":           ("numberOfRunups",          int),
        "oceanicTsunami":      ("oceanicTsunami",         bool),
    }

    for noaa_key, (our_key, cast) in field_map.items():
        val = event.get(noaa_key)
        if val is not None:
            props[our_key] = cast(val)

    return props

# ── Neo4j ─────────────────────────────────────────────────
class TsunamiBuilder:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(
            uri, auth=(user, password)
        )

    def process_event(self, event: dict) -> str:
        """
        Returns: 'enriched' | 'created_linked' | 'created_standalone'
        """
        year = event.get("year")
        lat  = event.get("latitude")
        lon  = event.get("longitude")

        if not all([year, lat, lon]):
            return "skipped"

        tsunami_id = f"ts_noaa_{event['id']}"
        props      = build_tsunami_props(event)

        with self.driver.session() as session:

            # ── Step 1: Does a Tsunami node already exist?
            existing = session.run("""
                MATCH (e:Earthquake)-[:TRIGGERED]->(t:Tsunami)
                WHERE e.year = $year
                  AND abs(e.epicentreLat - $lat) < 1.0
                  AND abs(e.epicentreLon - $lon) < 1.0
                RETURN t.id AS tid
                ORDER BY abs(e.epicentreLat - $lat)
                       + abs(e.epicentreLon - $lon)
                LIMIT 1
            """, year=year, lat=lat, lon=lon).single()

            if existing:
                # Enrich existing node
                session.run("""
                    MATCH (t:Tsunami {id: $id})
                    SET t += $props
                """, id=existing["tid"], props=props)
                return "enriched"

            # ── Step 2: Find closest Earthquake node without a Tsunami
            eq = session.run("""
                MATCH (e:Earthquake)
                WHERE e.year = $year
                  AND abs(e.epicentreLat - $lat) < 1.5
                  AND abs(e.epicentreLon - $lon) < 1.5
                  AND NOT (e)-[:TRIGGERED]->(:Tsunami)
                RETURN e.id AS eid,
                       e.epicentreLat AS elat,
                       e.epicentreLon AS elon
                ORDER BY abs(e.epicentreLat - $lat)
                       + abs(e.epicentreLon - $lon)
                LIMIT 1
            """, year=year, lat=lat, lon=lon).single()

            if eq:
                # Create Tsunami node linked to existing Earthquake
                props["id"] = tsunami_id
                session.run("""
                    MATCH (e:Earthquake {id: $eid})
                    CREATE (t:Tsunami $props)
                    CREATE (e)-[:TRIGGERED]->(t)
                """, eid=eq["eid"], props=props)
                return "created_linked"

            # ── Step 3: Create standalone Earthquake + Tsunami
            # Build datetime from NOAA date fields
            year_  = event.get("year",   1900)
            month_ = event.get("month",  1)
            day_   = event.get("day",    1)
            hour_  = event.get("hour",   0)
            min_   = event.get("minute", 0)
            sec_   = event.get("second", 0) or 0

            dt = (f"{year_:04d}-{month_:02d}-{day_:02d}"
                  f"T{hour_:02d}:{min_:02d}:{int(sec_):02d}")

            eq_id  = f"noaa_eq_{event['id']}"
            eq_props = {
                "id":                  eq_id,
                "occurrenceDateTime":  dt,
                "year":                year_,
                "epicentreLat":        float(lat),
                "epicentreLon":        float(lon),
                "momentMagnitude":     float(event.get("eqMagnitude") or 0),
                "hypocentralDepthKm":  float(event.get("eqDepth") or 0),
                "dataSource":          "NOAA_HISTORICAL",
            }

            props["id"] = tsunami_id
            session.run("""
                CREATE (e:Earthquake $eqProps)
                CREATE (t:Tsunami $tProps)
                CREATE (e)-[:TRIGGERED]->(t)
            """, eqProps=eq_props, tProps=props)
            return "created_standalone"

    def close(self):
        self.driver.close()


# ── Main ──────────────────────────────────────────────────
def run():
    events  = load_noaa(NOAA_FILE)
    builder = TsunamiBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASS)

    counts = {
        "enriched":           0,
        "created_linked":     0,
        "created_standalone": 0,
        "skipped":            0,
    }

    for event in events:
        outcome = builder.process_event(event)
        counts[outcome] += 1

        loc = event.get("locationName", "unknown")
        wh  = event.get("maxWaterHeight", "?")
        yr  = event.get("year")

        symbols = {
            "enriched":           "✅",
            "created_linked":     "🔗",
            "created_standalone": "🆕",
            "skipped":            "⏭️ ",
        }
        print(f"  {symbols[outcome]} {yr} | {loc} | wave: {wh}m | {outcome}")

    builder.close()

    print()
    print("── Summary ───────────────────────────────────")
    print(f"  ✅ Enriched existing nodes:      {counts['enriched']}")
    print(f"  🔗 Created + linked to eq node:  {counts['created_linked']}")
    print(f"  🆕 Created standalone pair:      {counts['created_standalone']}")
    print(f"  ⏭️  Skipped (missing data):       {counts['skipped']}")
    print(f"  Total processed: {sum(counts.values())}")


if __name__ == "__main__":
    run()