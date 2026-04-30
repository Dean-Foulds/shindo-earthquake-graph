from app.db import Neo4jService

DEFINITION = {
    "name": "get_sea_floor_depth",
    "description": (
        "Looks up the sea floor depth or land elevation at a given "
        "latitude and longitude. "
        "Returns depth in metres — negative means ocean floor, "
        "positive means land above sea level. "
        "Always call this first before any tsunami or damage assessment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "latitude":  {
                "type": "number",
                "description": "Latitude of the point (24 to 50 for Japan)"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude of the point (120 to 150 for Japan)"
            }
        },
        "required": ["latitude", "longitude"]
    }
}

async def get_sea_floor_depth(latitude: float, longitude: float) -> dict:
    db = Neo4jService()
    rows = await db.cypher_read("""
        MATCH (e:Earthquake)
        WHERE e.seaFloorDepthM IS NOT NULL
          AND abs(e.epicentreLat - $lat) < 1.0
          AND abs(e.epicentreLon - $lon) < 1.0
        RETURN e.seaFloorDepthM AS depth
        ORDER BY abs(e.epicentreLat - $lat) +
                 abs(e.epicentreLon - $lon)
        LIMIT 1
    """, params={"lat": latitude, "lon": longitude})

    depth = rows[0]["depth"] if rows else -4000.0

    return {
        "latitude"        : latitude,
        "longitude"       : longitude,
        "sea_floor_depth" : round(depth, 1),
        "is_offshore"     : depth < 0,
        "description"     : (
            f"{'Ocean floor' if depth < 0 else 'Land'} at "
            f"{abs(depth):.0f}m "
            f"{'below' if depth < 0 else 'above'} sea level"
        )
    }
