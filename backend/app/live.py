"""
Live earthquake feed for the map, shown before the user picks a simulation point.

USGS is the source of truth here rather than the graph. The graph only ever holds
what the poller has written into it, so a fresh or unreachable database means an
empty map — whereas USGS always has the real recent record. The graph is still
consulted, and anything it knows about is merged in, but it is never required.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends

from .db import get_db, Neo4jService

router = APIRouter(prefix="/live")

USGS_URL   = "https://earthquake.usgs.gov/fdsnws/event/1/query"
JAPAN_BBOX = {"minlatitude": 24, "maxlatitude": 46, "minlongitude": 122, "maxlongitude": 148}
CACHE_TTL  = 60  # the frontend polls every 60s; don't re-hit USGS per client

_cache: dict[tuple, tuple[float, list]] = {}


async def _fetch_usgs(days: int, min_magnitude: float, limit: int) -> list[dict]:
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    params = {
        "format":       "geojson",
        "starttime":    start,
        "minmagnitude": min_magnitude,
        "orderby":      "time",
        "limit":        min(limit, 20000),
        **JAPAN_BBOX,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(USGS_URL, params=params, timeout=30)
        resp.raise_for_status()
        features = resp.json().get("features", [])

    events = []
    for f in features:
        p, coords = f.get("properties", {}), f.get("geometry", {}).get("coordinates")
        if not coords or p.get("mag") is None:
            continue
        events.append({
            "id":            f"usgs_{f['id']}",
            "lat":           round(coords[1], 4),
            "lon":           round(coords[0], 4),
            "magnitude":     round(p["mag"], 1),
            "time":          datetime.fromtimestamp(
                                 p["time"] / 1000, tz=timezone.utc).isoformat(),
            "depth_km":      round(coords[2], 1) if len(coords) > 2 else None,
            "place":         p.get("place") or "Japan",
            "source":        "USGS",
            "intensity":     None,
            "faultType":     None,
            "seaFloorDepth": None,
        })
    return events


async def _fetch_graph(days: int, min_magnitude: float, limit: int,
                       db: Neo4jService) -> list[dict]:
    since = (
        (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        if days > 0 else "0000"
    )
    return await db.cypher_read("""
        MATCH (e:Earthquake)
        WHERE e.momentMagnitude >= $min_mag
          AND e.epicentreLat IS NOT NULL
          AND e.epicentreLon IS NOT NULL
          AND e.occurrenceDateTime IS NOT NULL
          AND e.occurrenceDateTime >= $since
        RETURN e.id                AS id,
               e.epicentreLat     AS lat,
               e.epicentreLon     AS lon,
               e.momentMagnitude  AS magnitude,
               e.occurrenceDateTime AS time,
               e.faultType        AS faultType,
               e.seaFloorDepthM   AS seaFloorDepth,
               e.place            AS place,
               e.source           AS source,
               e.jmaIntensity     AS intensity
        ORDER BY e.occurrenceDateTime DESC
        LIMIT $limit
    """, params={"min_mag": min_magnitude, "limit": limit, "since": since})


@router.get("/earthquakes")
async def get_live_earthquakes(
    days: int = 20,
    limit: int = 500,
    min_magnitude: float = 4.0,
    db: Neo4jService = Depends(get_db),
):
    """
    Events in the last `days`, newest first. Served from USGS and enriched with
    any graph records for the same window; a graph failure is non-fatal.
    """
    key = (days, limit, min_magnitude)
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]

    usgs, graph = await asyncio.gather(
        _fetch_usgs(days, min_magnitude, limit),
        _fetch_graph(days, min_magnitude, limit, db),
        return_exceptions=True,
    )

    events = usgs if isinstance(usgs, list) else []
    if isinstance(graph, list):
        # Same quake can appear in both feeds under different IDs; dedupe on a
        # coarse time+position key and prefer the graph row, which carries JMA
        # intensity and fault-zone enrichment USGS doesn't have.
        def fuzzy(e) -> tuple:
            return (str(e.get("time"))[:13], round(float(e["lat"]), 1),
                    round(float(e["lon"]), 1))
        merged = {fuzzy(e): e for e in events}
        merged.update({fuzzy(e): e for e in graph if e.get("lat") and e.get("lon")})
        events = sorted(merged.values(), key=lambda e: str(e.get("time")), reverse=True)
    elif not events:
        # Both sources failed — surface it rather than returning a silent [].
        raise RuntimeError(f"live feed unavailable: usgs={usgs!r} graph={graph!r}")

    events = events[:limit]
    _cache[key] = (time.monotonic(), events)
    return events


@router.get("/status")
async def get_live_status(days: int = 20, db: Neo4jService = Depends(get_db)):
    """Feed health: how many events we can see, and whether the graph is reachable."""
    events = await get_live_earthquakes(days=days, db=db)
    graph_ok, total_live = True, None
    try:
        rows = await db.cypher_read("""
            MATCH (e:Earthquake) WHERE e.source = 'JMA_LIVE'
            RETURN count(e) AS total_live_events, max(e.fetchedAt) AS last_updated
        """)
        total_live = rows[0]["total_live_events"] if rows else 0
    except Exception:
        graph_ok = False

    return {
        "events_in_window":  len(events),
        "window_days":       days,
        "latest_event":      events[0]["time"] if events else None,
        "sources":           sorted({e["source"] for e in events}),
        "graph_reachable":   graph_ok,
        "total_live_events": total_live,
    }
