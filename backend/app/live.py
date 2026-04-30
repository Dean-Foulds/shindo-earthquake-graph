"""
Live earthquake feed endpoints for the Shindo frontend.
Serves recent JMA events to display on the map before simulation.
"""

from fastapi import APIRouter, Depends
from .db import get_db, Neo4jService

router = APIRouter(prefix="/live")


@router.get("/earthquakes")
async def get_live_earthquakes(
    limit: int = 20,
    min_magnitude: float = 3.0,
    db: Neo4jService = Depends(get_db)
):
    return await db.cypher_read("""
        MATCH (e:Earthquake)
        WHERE e.momentMagnitude >= $min_mag
          AND e.epicentreLat IS NOT NULL
          AND e.epicentreLon IS NOT NULL
          AND e.occurrenceDateTime IS NOT NULL
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
    """, params={"min_mag": min_magnitude, "limit": limit})


@router.get("/status")
async def get_live_status(db: Neo4jService = Depends(get_db)):
    """
    Returns the status of the live feed —
    last updated time and event count.
    """
    rows = await db.cypher_read("""
        MATCH (e:Earthquake)
        WHERE e.source = 'JMA_LIVE'
        RETURN count(e)              AS total_live_events,
               max(e.fetchedAt)      AS last_updated,
               max(e.occurrenceDateTime) AS latest_event
    """)

    recent = await db.cypher_read("""
        MATCH (e:Earthquake)
        WHERE e.momentMagnitude >= 3.0
          AND e.occurrenceDateTime >= toString(
                datetime() - duration({days: 30})
              )
        RETURN count(e) AS events_last_30_days
    """)

    status = rows[0] if rows else {}
    status["events_last_30_days"] = recent[0]["events_last_30_days"] if recent else 0
    return status
