"""
JMA Live Feed Poller — async background task
Polls the JMA ATOM feed every 60 seconds and writes new events to Neo4j.
Launched automatically by FastAPI on startup.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

import httpx

JMA_FEED_URL  = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
POLL_INTERVAL = 60
ATOM_NS       = {"atom": "http://www.w3.org/2005/Atom"}

seen_ids: set = set()


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
        if "VXSE" not in entry_id or entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        link = entry.find("atom:link", ATOM_NS)
        if link is not None:
            url = link.attrib.get("href", "")
            if url:
                urls.append(url)
    return urls


async def _parse_event(client: httpx.AsyncClient, url: str) -> Optional[dict]:
    try:
        resp = await client.get(url, timeout=15)
        root = ET.fromstring(resp.text)
    except Exception as e:
        print(f"[poller] event fetch error {url}: {e}")
        return None

    ns = {"jmx_eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis/"}

    lat = lon = depth = magnitude = None
    intensity = "0"
    place = ""
    dt_str = None

    for path in [".//OriginTime", ".//DateTime"]:
        el = root.find(path)
        if el is not None and el.text:
            dt_str = el.text.strip()
            break

    coord_el = root.find(".//jmx_eb:Coordinate", ns)
    if coord_el is None:
        coord_el = root.find(".//{http://xml.kishou.go.jp/jmaxml1/elementBasis/}Coordinate")
    if coord_el is not None and coord_el.text:
        parts = re.findall(r'[+-]\d+\.?\d*', coord_el.text.strip())
        if len(parts) >= 2:
            lat   = float(parts[0])
            lon   = float(parts[1])
            depth = abs(float(parts[2])) / 1000 if len(parts) > 2 else None

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

    for path in [".//MaxInt", ".//Intensity"]:
        el = root.find(path)
        if el is not None and el.text:
            intensity = el.text.strip()
            break

    for path in [".//Hypocenter/Area/Name", ".//Area/Name", ".//Name"]:
        el = root.find(path)
        if el is not None and el.text:
            place = el.text.strip()
            break

    if not all([dt_str, lat, lon, magnitude]):
        return None
    if not (23 <= lat <= 50 and 120 <= lon <= 150):
        return None

    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)

    event_id = f"jma_live_{dt.strftime('%Y%m%d%H%M%S')}_{abs(int(lat*100))}_{abs(int(lon*100))}"
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


async def run_poller(db):
    """Async polling loop — run as an asyncio background task."""
    print(f"[poller] started, polling JMA every {POLL_INTERVAL}s")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                urls = await _fetch_feed(client)
                if urls:
                    print(f"[poller] {len(urls)} new report(s)")
                    for url in urls:
                        event = await _parse_event(client, url)
                        if event:
                            await _write_event(db, event)
            except asyncio.CancelledError:
                print("[poller] stopped")
                return
            except Exception as e:
                print(f"[poller] error: {e}")
            await asyncio.sleep(POLL_INTERVAL)
