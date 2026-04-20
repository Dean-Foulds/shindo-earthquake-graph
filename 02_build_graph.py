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
    if magnitude >= 5.0:  return "moderate"
    return "minor"


# ── graph builder ────────────────────────────────────────────────

class ShindoGraph:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

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

    def load_earthquakes(self, events):
        print(f"Loading {len(events)} earthquakes...")
        batch_size = 200
        notable = NOTABLE_EVENTS

        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            for e in batch:
                fzone_id  = assign_fault_zone(e["lat"], e["lon"], e["depth_km"])
                pref_id   = nearest_prefecture(e["lat"], e["lon"])
                severity  = severity_band(e["magnitude"])
                extra     = notable.get(e["id"], {})

                self.run("""
                    MERGE (eq:Earthquake {id: $id})
                    SET eq.time         = $time,
                        eq.year         = $year,
                        eq.decade       = $decade,
                        eq.magnitude    = $magnitude,
                        eq.depth_km     = $depth_km,
                        eq.lat          = $lat,
                        eq.lon          = $lon,
                        eq.place        = $place,
                        eq.tsunami      = $tsunami,
                        eq.alert        = $alert,
                        eq.sig          = $sig,
                        eq.severity     = $severity,
                        eq.name         = $name,
                        eq.deaths       = $deaths,
                        eq.nuclear_incident = $nuclear_incident,
                        eq.tsunami_max_height_m = $tsunami_height
                """,
                    id=e["id"], time=e["time"], year=e["year"],
                    decade=e["decade"], magnitude=e["magnitude"],
                    depth_km=e["depth_km"], lat=e["lat"], lon=e["lon"],
                    place=e["place"], tsunami=e["tsunami"],
                    alert=e["alert"], sig=e["sig"], severity=severity,
                    name=extra.get("name"),
                    deaths=extra.get("deaths"),
                    nuclear_incident=extra.get("nuclear_incident"),
                    tsunami_height=extra.get("tsunami_max_height_m"),
                )

                # ORIGINATED_ON → FaultZone
                self.run("""
                    MATCH (eq:Earthquake {id: $eid}), (f:FaultZone {id: $fid})
                    MERGE (eq)-[:ORIGINATED_ON]->(f)
                """, eid=e["id"], fid=fzone_id)

                # STRUCK → nearest Prefecture
                self.run("""
                    MATCH (eq:Earthquake {id: $eid}), (pf:Prefecture {id: $pid})
                    MERGE (eq)-[:STRUCK {distance_km: $dist}]->(pf)
                """, eid=e["id"], pid=pref_id,
                    dist=round(haversine_km(e["lat"], e["lon"],
                               next(p for p in PREFECTURES if p["id"] == pref_id)["lat"],
                               next(p for p in PREFECTURES if p["id"] == pref_id)["lon"]), 1))

                # TRIGGERED → Tsunami node (if flagged)
                if e["tsunami"]:
                    self.run("""
                        MERGE (t:Tsunami {id: $tid})
                        SET t.year            = $year,
                            t.earthquake_id   = $eid,
                            t.max_height_m    = $height,
                            t.source_mag      = $mag
                        WITH t
                        MATCH (eq:Earthquake {id: $eid})
                        MERGE (eq)-[:TRIGGERED]->(t)
                        WITH t
                        MATCH (pf:Prefecture {id: $pid})
                        MERGE (t)-[:INUNDATED]->(pf)
                    """, tid=f"ts_{e['id']}", year=e["year"],
                        eid=e["id"], height=extra.get("tsunami_max_height_m"),
                        mag=e["magnitude"], pid=pref_id)

                # IN_DECADE → Decade node
                self.run("""
                    MERGE (d:Decade {year: $decade})
                    SET d.label = $label
                    WITH d
                    MATCH (eq:Earthquake {id: $eid})
                    MERGE (eq)-[:IN_DECADE]->(d)
                """, decade=e["decade"], label=f"{e['decade']}s", eid=e["id"])

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
