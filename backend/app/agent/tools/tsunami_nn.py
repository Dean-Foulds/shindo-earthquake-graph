DEFINITION = {
    "name": "get_tsunami_nearest_neighbours",
    "description": (
        "Queries the Neo4j knowledge graph for the 5 most similar "
        "historical tsunami events based on magnitude, sea floor depth, "
        "and latitude. Returns measured wave heights, casualties, and "
        "building damage from real past events. "
        "Only call this when a tsunami warning has been issued."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "magnitude": {
                "type": "number",
                "description": "Moment magnitude of the earthquake"
            },
            "sea_floor_depth": {
                "type": "number",
                "description": "Sea floor depth in metres (negative for ocean)"
            },
            "latitude": {
                "type": "number",
                "description": "Epicentre latitude"
            }
        },
        "required": ["magnitude", "sea_floor_depth", "latitude"]
    }
}

QUERY = """
    MATCH (e:Earthquake)-[:TRIGGERED]->(t:Tsunami)
    WHERE t.waveHeightAtShoreM IS NOT NULL
      AND t.waveHeightAtShoreM > 0.1
      AND abs(e.momentMagnitude - $mag) < 1.5
      AND abs(e.seaFloorDepthM  - $depth) < 1000
      AND abs(e.epicentreLat    - $lat) < 5.0
    WITH e, t,
         abs(e.momentMagnitude - $mag) * 2.0     AS magScore,
         abs(e.seaFloorDepthM  - $depth) / 500.0 AS depthScore,
         abs(e.epicentreLat    - $lat)            AS latScore
    RETURN t.waveHeightAtShoreM   AS waveHeight,
           t.tsunamiFatalities    AS fatalities,
           t.buildingsWashedAway  AS buildingsDestroyed,
           t.numberOfRunups       AS observationPoints,
           t.locationName         AS location,
           e.momentMagnitude      AS magnitude,
           e.seaFloorDepthM       AS seaFloorDepth,
           e.hypocentralDepthKm   AS hypocentralDepth,
           round(magScore + depthScore + latScore, 3) AS similarity
    ORDER BY similarity / log(t.numberOfRunups + 2)
    LIMIT 5
"""

async def get_tsunami_nearest_neighbours(
    magnitude       : float,
    sea_floor_depth : float,
    latitude        : float,
    db              = None
) -> dict:
    rows = await db.cypher_read(
        QUERY,
        params={"mag": magnitude, "depth": sea_floor_depth, "lat": latitude}
    )

    if not rows:
        return {
            "found"      : False,
            "message"    : "No similar historical tsunami events found",
            "neighbours" : []
        }

    wave_heights = [r["waveHeight"] for r in rows if r.get("waveHeight")]

    return {
        "found"            : True,
        "neighbours"       : rows,
        "wave_height_min"  : round(min(wave_heights), 2),
        "wave_height_max"  : round(max(wave_heights), 2),
        "wave_height_avg"  : round(sum(wave_heights) / len(wave_heights), 2),
        "historical_basis" : len(rows),
    }
