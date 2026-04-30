"""
JMA Live Earthquake Feed Poller
================================
Polls the JMA ATOM feed every 60 seconds for new earthquake events.
Parses the XML, fetches event detail, and writes to Neo4j.

Run as a background service alongside the FastAPI backend.

Usage:
    cd japanese_earth_quake_project
    python data/live/poll_live_feed.py
"""

import time
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import os
import re

load_dotenv()

# ── Config ────────────────────────────────────────────────
JMA_FEED_URL   = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
POLL_INTERVAL  = 60   # seconds
NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Track events already processed this session
seen_ids: set = set()

# ── Neo4j ─────────────────────────────────────────────────
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def write_event(event: dict):
    """Write a new JMA earthquake event to Neo4j."""
    with driver.session() as session:
        session.run("""
            MERGE (e:Earthquake {id: $id})
            SET e.occurrenceDateTime = $occurrenceDateTime,
                e.epicentreLat       = $lat,
                e.epicentreLon       = $lon,
                e.hypocentralDepthKm = $depth,
                e.momentMagnitude    = $magnitude,
                e.jmaIntensity       = $intensity,
                e.place              = $place,
                e.source             = 'JMA_LIVE',
                e.fetchedAt          = $fetchedAt,
                e.year               = $year
        """, **event)
    print(f"  ✅ Saved: {event['id']} | M{event['magnitude']} | {event['place']}")

# ── JMA XML parsing ───────────────────────────────────────
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

def fetch_feed() -> list[str]:
    """
    Fetch the JMA ATOM feed and return URLs of new earthquake entries.
    Filters for earthquake-related entries only (VXSE — seismology reports).
    """
    try:
        resp = httpx.get(JMA_FEED_URL, timeout=15)
        root = ET.fromstring(resp.text)
    except Exception as e:
        print(f"  ⚠️  Feed fetch error: {e}")
        return []

    new_urls = []
    for entry in root.findall("atom:entry", ATOM_NS):
        entry_id = entry.findtext("atom:id", namespaces=ATOM_NS) or ""
        title    = entry.findtext("atom:title", namespaces=ATOM_NS) or ""

        # Only process earthquake intensity reports (震度速報 / 震源・震度情報)
        if "VXSE" not in entry_id:
            continue

        if entry_id in seen_ids:
            continue

        seen_ids.add(entry_id)

        link = entry.find("atom:link", ATOM_NS)
        if link is not None:
            url = link.attrib.get("href", "")
            if url:
                new_urls.append(url)

    return new_urls

def parse_event_xml(url: str) -> dict | None:
    """
    Fetch and parse a single JMA earthquake event XML.
    Maps JMA fields to our ontology property names.
    """
    try:
        resp = httpx.get(url, timeout=15)
        root = ET.fromstring(resp.text)
    except Exception as e:
        print(f"  ⚠️  Event fetch error {url}: {e}")
        return None

    # JMA XML namespaces
    ns = {
        "jmx"     : "http://xml.kishou.go.jp/jmaxml1/",
        "jmx_eb"  : "http://xml.kishou.go.jp/jmaxml1/elementBasis/",
        "eb"      : "http://xml.kishou.go.jp/jmaxml1/elementBasis/",
    }

    try:
        # Extract fields — structure varies by report type
        # Try multiple paths as JMA XML structure varies
        lat       = None
        lon       = None
        depth     = None
        magnitude = None
        intensity = "0"
        place     = ""
        dt_str    = None

        # Origin time
        for path in [".//OriginTime", ".//DateTime"]:
            el = root.find(path)
            if el is not None and el.text:
                dt_str = el.text.strip()
                break

        # Coordinates
        coord_el = root.find(".//jmx_eb:Coordinate", ns)
        if coord_el is None:
            coord_el = root.find(".//{http://xml.kishou.go.jp/jmaxml1/elementBasis/}Coordinate")
        if coord_el is not None and coord_el.text:
            # JMA format: +38.3+142.4-10/ or similar
            coord_text = coord_el.text.strip()
            parts = re.findall(r'[+-]\d+\.?\d*', coord_text)
            if len(parts) >= 2:
                lat   = float(parts[0])
                lon   = float(parts[1])
                depth = abs(float(parts[2])) / 1000 if len(parts) > 2 else None

        # Magnitude
        for path in [
            ".//jmx_eb:Magnitude",
            ".//{http://xml.kishou.go.jp/jmaxml1/elementBasis/}Magnitude"
        ]:
            el = root.find(path)
            if el is not None and el.text:
                try:
                    magnitude = float(el.text.strip())
                except ValueError:
                    pass
                break

        # Intensity
        for path in [".//MaxInt", ".//Intensity"]:
            el = root.find(path)
            if el is not None and el.text:
                intensity = el.text.strip()
                break

        # Place name
        for path in [".//Name", ".//Area/Name", ".//Hypocenter/Area/Name"]:
            el = root.find(path)
            if el is not None and el.text:
                place = el.text.strip()
                break

        # Require minimum fields
        if not all([dt_str, lat, lon, magnitude]):
            return None

        # Filter to Japan region
        if not (23 <= lat <= 50 and 120 <= lon <= 150):
            return None

        # Parse datetime
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)

        event_id = f"jma_live_{dt.strftime('%Y%m%d%H%M%S')}_{abs(int(lat*100))}_{abs(int(lon*100))}"

        return {
            "id"                : event_id,
            "occurrenceDateTime": dt.isoformat(),
            "lat"               : lat,
            "lon"               : lon,
            "depth"             : depth or 10.0,
            "magnitude"         : magnitude,
            "intensity"         : intensity,
            "place"             : place or "Japan",
            "fetchedAt"         : datetime.now(timezone.utc).isoformat(),
            "year"              : dt.year,
        }

    except Exception as e:
        print(f"  ⚠️  Parse error: {e}")
        return None

# ── Main polling loop ─────────────────────────────────────
def run():
    print("═" * 50)
    print("  JMA Live Feed Poller")
    print(f"  Polling every {POLL_INTERVAL}s")
    print("═" * 50)

    while True:
        now = datetime.now(timezone.utc).astimezone().strftime("%H:%M:%S")
        print(f"\n[{now}] Checking JMA feed...")

        try:
            new_urls = fetch_feed()

            if new_urls:
                print(f"  Found {len(new_urls)} new earthquake report(s)")
                for url in new_urls:
                    event = parse_event_xml(url)
                    if event:
                        write_event(event)
            else:
                print(f"  No new events")

        except Exception as e:
            print(f"  ⚠️  Poll error: {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run()