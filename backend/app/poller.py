"""
JMA Live Feed Poller — async background task
Polls the JMA ATOM feed every 60 seconds and writes new events to Neo4j.
On startup, backfills the last 24 hours from USGS (the JMA short feed only
covers the most recent ~2 hours).
Launched automatically by FastAPI on startup.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

JMA_FEED_URL  = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
USGS_URL      = "https://earthquake.usgs.gov/fdsnws/event/1/query"
POLL_INTERVAL = 60
ATOM_NS       = {"atom": "http://www.w3.org/2005/Atom"}
JAPAN_BBOX    = {"minlatitude": 24, "maxlatitude": 46, "minlongitude": 122, "maxlongitude": 148}

seen_ids: set = set()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_any(root, *local_names) -> Optional[ET.Element]:
    """Find first element matching any of the given local names, ignoring namespace."""
    for name in local_names:
        for el in root.iter():
            if el.tag.split("}")[-1] == name:
                return el
    return None


def _text(root, *local_names) -> Optional[str]:
    el = _find_any(root, *local_names)
    return el.text.strip() if el is not None and el.text else None


def _make_event(event_id, dt, lat, lon, depth, magnitude, intensity, place) -> dict:
    return {
        "id":                 event_id,
        "occurrenceDateTime": dt.isoformat(),
        "lat":                lat,
        "lon":                lon,
        "depth":              depth or 10.0,
        "magnitude":          magnitude,
        "intensity":          intensity,
        "place":              place or "Japan",
        "fetchedAt":          datetime.now(timezone.utc).isoformat(),
        "year":               dt.year,
    }


async def _write_event(db, event: dict):
    async with db.driver.session() as session:
        await session.run("""
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
    print(f"[poller] saved M{event['magnitude']} {event['place']} ({event['id']})")


# ── JMA feed polling ──────────────────────────────────────────────────────────

async def _fetch_feed(client: httpx.AsyncClient) -> list[str]:
    try:
        resp = await client.get(JMA_FEED_URL, timeout=15)
        root = ET.fromstring(resp.text)
    except Exception as e:
        print(f"[poller] feed fetch error: {e}")
        return []

    urls = []
    for entry in root.findall("atom:entry", ATOM_NS):
        entry_id = entry.findtext("atom:id", namespaces=ATOM_NS) or ""
        # VXSE53 = 震源・震度情報, VXSE51 = 震度速報 — both contain earthquakes
        if "VXSE" not in entry_id or entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        link = entry.find("atom:link", ATOM_NS)
        if link is not None:
            url = link.attrib.get("href", "")
            if url:
                urls.append(url)
    return urls


async def _parse_jma_event(client: httpx.AsyncClient, url: str) -> Optional[dict]:
    try:
        resp = await client.get(url, timeout=15)
        root = ET.fromstring(resp.text)
    except Exception as e:
        print(f"[poller] event fetch error {url}: {e}")
        return None

    dt_str    = _text(root, "OriginTime")
    coord_el  = _find_any(root, "Coordinate")
    magnitude = None
    intensity = _text(root, "MaxInt") or "0"
    place     = _text(root, "Name") or ""

    lat = lon = depth = None
    if coord_el is not None and coord_el.text:
        parts = re.findall(r'[+-]\d+\.?\d*', coord_el.text.strip())
        if len(parts) >= 2:
            lat   = float(parts[0])
            lon   = float(parts[1])
            # JMA depth is in metres (e.g. -10000 = 10 km)
            depth = abs(float(parts[2])) / 1000 if len(parts) > 2 else None

    mag_el = _find_any(root, "Magnitude")
    if mag_el is not None and mag_el.text:
        try:
            magnitude = float(mag_el.text.strip())
        except ValueError:
            pass

    if not all([dt_str, lat, lon, magnitude]):
        return None
    if not (23 <= lat <= 50 and 120 <= lon <= 150):
        return None

    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)

    event_id = f"jma_live_{dt.strftime('%Y%m%d%H%M%S')}_{abs(int(lat*100))}_{abs(int(lon*100))}"
    return _make_event(event_id, dt, lat, lon, depth, magnitude, intensity, place)


# ── USGS 24-hour backfill ─────────────────────────────────────────────────────

async def backfill_24h(db, client: httpx.AsyncClient):
    """On startup, fetch the last 24 hours from USGS and write any missing events."""
    start = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    params = {
        "format":       "geojson",
        "starttime":    start,
        "minmagnitude": 3.0,
        "orderby":      "time-asc",
        **JAPAN_BBOX,
    }
    print("[poller] backfilling last 24h from USGS...")
    try:
        resp = await client.get(USGS_URL, params=params, timeout=30)
        resp.raise_for_status()
        features = resp.json().get("features", [])
    except Exception as e:
        print(f"[poller] USGS backfill error: {e}")
        return

    count = 0
    for f in features:
        p      = f["properties"]
        coords = f["geometry"]["coordinates"]
        try:
            dt = datetime.utcfromtimestamp(p["time"] / 1000).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        lat, lon = round(coords[1], 4), round(coords[0], 4)
        if not (23 <= lat <= 50 and 120 <= lon <= 150):
            continue
        event_id = f"usgs_live_{f['id']}"
        if event_id in seen_ids:
            continue
        seen_ids.add(event_id)
        event = _make_event(
            event_id, dt, lat, lon,
            depth=round(coords[2], 1),
            magnitude=p.get("mag"),
            intensity=str(p.get("cdi") or p.get("mmi") or "0"),
            place=p.get("place", "Japan"),
        )
        if event["magnitude"] is None:
            continue
        await _write_event(db, event)
        count += 1

    print(f"[poller] backfill complete — {count} new events from USGS")


# ── Main polling loop ─────────────────────────────────────────────────────────

async def run_poller(db):
    """Async polling loop — run as an asyncio background task."""
    print(f"[poller] started, polling JMA every {POLL_INTERVAL}s")
    async with httpx.AsyncClient() as client:
        await backfill_24h(db, client)
        while True:
            try:
                urls = await _fetch_feed(client)
                if urls:
                    print(f"[poller] {len(urls)} new JMA report(s)")
                    for url in urls:
                        event = await _parse_jma_event(client, url)
                        if event:
                            await _write_event(db, event)
            except asyncio.CancelledError:
                print("[poller] stopped")
                return
            except Exception as e:
                print(f"[poller] error: {e}")
            await asyncio.sleep(POLL_INTERVAL)
