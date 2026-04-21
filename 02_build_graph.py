"""
SHINDO — Step 2: Build the Neo4j knowledge graph
==================================================
Run this after 01_fetch_usgs.py.

Usage:
    python 02_build_graph.py --uri neo4j+s://<your-id>.databases.neo4j.io \
                             --user neo4j \
                             --password <your-password>

Or set environment variables:
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

What this builds
----------------
Nodes    : Earthquake · FaultZone · Tsunami · Prefecture · NuclearFacility · Decade
Edges    : ORIGINATED_ON · TRIGGERED · STRUCK · INUNDATED · UNDERLIES
           CONTAINS · WITHIN_50KM_OF · BORDERS · IN_DECADE

The graph is idempotent — safe to re-run (uses MERGE throughout).
"""

import json
import math
import argparse
import os
import sys
from neo4j import GraphDatabase
from reference_data import (
    FAULT_ZONES, NUCLEAR_FACILITIES, PREFECTURES,
    NOTABLE_EVENTS, assign_fault_zone,
)


from dotenv import load_dotenv
load_dotenv()
# Setting env variables
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")




# ── helpers ──────────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def nearest_prefecture(lat, lon):
    """Return the id of the geographically closest prefecture centroid."""
    return min(PREFECTURES, key=lambda p: haversine_km(lat, lon, p["lat"], p["lon"]))["id"]


def severity_band(magnitude):
    if magnitude >= 8.0:  return "catastrophic"
    if magnitude >= 7.0:  return "major"
    if magnitude >= 6.0:  return "strong"
    if magnitude >= 5.0:  return "strong"
    if magnitude >= 4.0:  return "moderate"
    return "minor"


# ── graph builder ────────────────────────────────────────────────

class ShindoGraph:

    def __init__(self, uri, user, password):
        self._uri = uri
        self._auth = (user, password)
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def _reconnect(self):
        try:
            self.driver.close()
        except Exception:
            pass
        self.driver = GraphDatabase.driver(self._uri, auth=self._auth)

    def close(self):
        self.driver.close()

    def run(self, query, **params):
        with self.driver.session() as session:
            return session.run(query, **params)

    # ── SCHEMA ──────────────────────────────────────────────────

    def create_constraints(self):
        print("Creating constraints and indexes...")
        constraints = [
            "CREATE CONSTRAINT eq_id IF NOT EXISTS FOR (e:Earthquake) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT fault_id IF NOT EXISTS FOR (f:FaultZone) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT pref_id IF NOT EXISTS FOR (p:Prefecture) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT nuclear_id IF NOT EXISTS FOR (n:NuclearFacility) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT decade_id IF NOT EXISTS FOR (d:Decade) REQUIRE d.year IS UNIQUE",
            "CREATE INDEX eq_mag IF NOT EXISTS FOR (e:Earthquake) ON (e.magnitude)",
            "CREATE INDEX eq_year IF NOT EXISTS FOR (e:Earthquake) ON (e.year)",
            "CREATE INDEX eq_tsunami IF NOT EXISTS FOR (e:Earthquake) ON (e.tsunami)",
        ]
        for c in constraints:
            try:
                self.run(c)
            except Exception:
                pass   # constraint may already exist

    # ── STATIC NODES ────────────────────────────────────────────

    def load_fault_zones(self):
        print("Loading fault zones...")
        for z in FAULT_ZONES:
            self.run("""
                MERGE (f:FaultZone {id: $id})
                SET f.name             = $name,
                    f.type             = $type,
                    f.plates           = $plates,
                    f.predicted_max_mag = $predicted_max_mag,
                    f.last_major_year  = $last_major_year,
                    f.description      = $description
            """, **{k: z.get(k) for k in
                    ["id","name","type","plates","predicted_max_mag","last_major_year","description"]})

    def load_prefectures(self):
        print("Loading prefectures...")
        for p in PREFECTURES:
            self.run("""
                MERGE (pf:Prefecture {id: $id})
                SET pf.name         = $name,
                    pf.region       = $region,
                    pf.lat          = $lat,
                    pf.lon          = $lon,
                    pf.coast        = $coast,
                    pf.population_m = $population_m
            """, **p)

        # Prefecture BORDERS relationships (within same region)
        print("  Building BORDERS relationships...")
        for p in PREFECTURES:
            neighbours = [
                q["id"] for q in PREFECTURES
                if q["id"] != p["id"] and haversine_km(p["lat"], p["lon"], q["lat"], q["lon"]) < 150
            ]
            for nid in neighbours:
                self.run("""
                    MATCH (a:Prefecture {id: $a}), (b:Prefecture {id: $b})
                    MERGE (a)-[:BORDERS]->(b)
                """, a=p["id"], b=nid)

        # FaultZone UNDERLIES Prefecture
        print("  Building UNDERLIES relationships...")
        for z in FAULT_ZONES:
            lmin, lmax, omin, omax, _ = z["bbox"]
            for p in PREFECTURES:
                if lmin <= p["lat"] <= lmax and omin <= p["lon"] <= omax:
                    self.run("""
                        MATCH (f:FaultZone {id: $fid}), (pf:Prefecture {id: $pid})
                        MERGE (f)-[:UNDERLIES]->(pf)
                    """, fid=z["id"], pid=p["id"])

    def load_nuclear_facilities(self):
        print("Loading nuclear facilities...")
        for n in NUCLEAR_FACILITIES:
            self.run("""
                MERGE (nf:NuclearFacility {id: $id})
                SET nf.name       = $name,
                    nf.lat        = $lat,
                    nf.lon        = $lon,
                    nf.reactors   = $reactors,
                    nf.status     = $status,
                    nf.operator   = $operator,
                    nf.note       = $note
            """, **n)

            # CONTAINS link to prefecture
            self.run("""
                MATCH (nf:NuclearFacility {id: $nid}),
                      (pf:Prefecture {id: $pid})
                MERGE (pf)-[:CONTAINS]->(nf)
            """, nid=n["id"], pid=n["prefecture"].lower())

    # ── DYNAMIC NODES (earthquakes) ──────────────────────────────

    def _run_batch(self, rows):
        """Write one batch of earthquake rows using UNWIND (single round trip)."""
        # Main node + relationships (non-tsunami)
        self.run("""
            UNWIND $rows AS r
            MERGE (eq:Earthquake {id: r.id})
            SET eq.time             = r.time,
                eq.year             = r.year,
                eq.decade           = r.decade,
                eq.magnitude        = r.magnitude,
                eq.depth_km         = r.depth_km,
                eq.lat              = r.lat,
                eq.lon              = r.lon,
                eq.place            = r.place,
                eq.tsunami          = r.tsunami,
                eq.alert            = r.alert,
                eq.sig              = r.sig,
                eq.severity         = r.severity,
                eq.name             = r.name,
                eq.deaths           = r.deaths,
                eq.nuclear_incident = r.nuclear_incident,
                eq.tsunami_max_height_m = r.tsunami_height
            WITH eq, r
            MATCH (f:FaultZone {id: r.fzone_id})
            MERGE (eq)-[:ORIGINATED_ON]->(f)
            WITH eq, r
            MATCH (pf:Prefecture {id: r.pref_id})
            MERGE (eq)-[:STRUCK {distance_km: r.dist}]->(pf)
            WITH eq, r
            MERGE (d:Decade {year: r.decade})
            SET d.label = r.decade_label
            MERGE (eq)-[:IN_DECADE]->(d)
        """, rows=rows)

        # Tsunami relationships (separate pass, only for flagged events)
        tsunami_rows = [r for r in rows if r["tsunami"]]
        if tsunami_rows:
            self.run("""
                UNWIND $rows AS r
                MERGE (t:Tsunami {id: r.tid})
                SET t.year          = r.year,
                    t.earthquake_id = r.id,
                    t.max_height_m  = r.tsunami_height,
                    t.source_mag    = r.magnitude
                WITH t, r
                MATCH (eq:Earthquake {id: r.id})
                MERGE (eq)-[:TRIGGERED]->(t)
                WITH t, r
                MATCH (pf:Prefecture {id: r.pref_id})
                MERGE (t)-[:INUNDATED]->(pf)
            """, rows=tsunami_rows)

    def load_earthquakes(self, events):
        print(f"Loading {len(events)} earthquakes...")
        batch_size = 200
        notable = NOTABLE_EVENTS
        _pref_cache = {}

        def get_pref(lat, lon):
            key = (round(lat, 2), round(lon, 2))
            if key not in _pref_cache:
                _pref_cache[key] = nearest_prefecture(lat, lon)
            return _pref_cache[key]

        def pref_coords(pid):
            p = next(x for x in PREFECTURES if x["id"] == pid)
            return p["lat"], p["lon"]

        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            rows = []
            for e in batch:
                fzone_id = assign_fault_zone(e["lat"], e["lon"], e["depth_km"])
                pref_id  = get_pref(e["lat"], e["lon"])
                plat, plon = pref_coords(pref_id)
                extra    = notable.get(e["id"], {})
                rows.append({
                    "id": e["id"], "time": e["time"], "year": e["year"],
                    "decade": e["decade"], "decade_label": f"{e['decade']}s",
                    "magnitude": e["magnitude"], "depth_km": e["depth_km"],
                    "lat": e["lat"], "lon": e["lon"], "place": e["place"],
                    "tsunami": bool(e["tsunami"]), "alert": e["alert"],
                    "sig": e["sig"], "severity": severity_band(e["magnitude"]),
                    "name": extra.get("name"), "deaths": extra.get("deaths"),
                    "nuclear_incident": extra.get("nuclear_incident"),
                    "tsunami_height": extra.get("tsunami_max_height_m"),
                    "fzone_id": fzone_id, "pref_id": pref_id,
                    "dist": round(haversine_km(e["lat"], e["lon"], plat, plon), 1),
                    "tid": f"ts_{e['id']}",
                })

            # Retry once on connection reset
            for attempt in range(2):
                try:
                    self._run_batch(rows)
                    break
                except Exception as exc:
                    if attempt == 0 and "defunct" in str(exc).lower():
                        print(f"  Connection reset at {i} — reconnecting...")
                        self._reconnect()
                    else:
                        raise

            print(f"  {min(i + batch_size, len(events))}/{len(events)} loaded...")

        # WITHIN_50KM_OF nuclear facilities
        print("Building WITHIN_50KM_OF relationships...")
        self.run("""
            MATCH (eq:Earthquake), (nf:NuclearFacility)
            WHERE point.distance(
                point({latitude: eq.lat, longitude: eq.lon}),
                point({latitude: nf.lat, longitude: nf.lon})
            ) < 50000
            MERGE (eq)-[:WITHIN_50KM_OF]->(nf)
        """)


# ── MAIN ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build Shindo Neo4j graph")
    parser.add_argument("--uri",      default=os.getenv("NEO4J_URI"))
    parser.add_argument("--user",     default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD"))
    parser.add_argument("--data",     default="data/earthquakes_raw.json")
    args = parser.parse_args()

    if not args.uri or not args.password:
        print("ERROR: provide --uri and --password (or set NEO4J_URI / NEO4J_PASSWORD)")
        sys.exit(1)

    print(f"\nConnecting to {args.uri} ...")
    g = ShindoGraph(args.uri, args.user, args.password)

    print("Loading earthquake data from", args.data)
    with open(args.data) as f:
        events = json.load(f)
    print(f"  {len(events)} events read\n")

    g.create_constraints()
    g.load_fault_zones()
    g.load_prefectures()
    g.load_nuclear_facilities()
    g.load_earthquakes(events)
    g.close()

    print("\n✓ Shindo graph built successfully!")
    print("  Open Neo4j Aura console → Query → paste a Cypher from 03_sample_queries.cypher")


if __name__ == "__main__":
    main()
