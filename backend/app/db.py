import os
from typing import Optional
from neo4j import AsyncGraphDatabase

VOYAGE_MODEL = "voyage-3"
EMBED_DIM    = 1024

class Neo4jService:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        self._vo = None

    def _voyage(self):
        if not self._vo:
            import voyageai
            self._vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
        return self._vo

    async def run(self, query, **params):
        async with self.driver.session() as session:
            result = await session.run(query, **params)
            return [r.data() async for r in result]

    async def embed_query(self, text: str) -> list[float]:
        import asyncio
        result = await asyncio.to_thread(
            self._voyage().embed, [text], model=VOYAGE_MODEL, input_type="query"
        )
        return result.embeddings[0]

    async def semantic_search(self, query: str, label: str = "Earthquake", top_k: int = 5) -> list[dict]:
        index_map = {
            "Earthquake":      "earthquake_embedding",
            "FaultZone":       "fault_zone_embedding",
            "NuclearFacility": "nuclear_embedding",
            "Prefecture":      "prefecture_embedding",
        }
        idx = index_map.get(label, "earthquake_embedding")
        vec = await self.embed_query(query)
        async with self.driver.session() as s:
            result = await s.run(f"""
                CALL db.index.vector.queryNodes('{idx}', $k, $vec)
                YIELD node, score
                RETURN node, score
                ORDER BY score DESC
            """, k=top_k, vec=vec)
            results = []
            async for r in result:
                node = dict(r["node"])
                node.pop("embedding", None)
                results.append({"score": round(r["score"], 4), "node": node})
            return results

    async def cypher_read(self, query: str, params: Optional[dict] = None) -> list[dict]:
        forbidden = ("CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DROP", "CALL {")
        upper = query.upper()
        for kw in forbidden:
            if kw in upper:
                raise ValueError(f"Write operation not allowed: {kw}")
        async with self.driver.session() as s:
            result = await s.run(query, **(params or {}))
            return [r.data() async for r in result]

    async def get_earthquake(self, eq_id: str) -> Optional[dict]:
        rows = await self.run("""
            MATCH (e:Earthquake {id: $id})
            OPTIONAL MATCH (e)-[:ORIGINATED_ON]->(fz:FaultZone)
            OPTIONAL MATCH (e)-[:TRIGGERED]->(t:Tsunami)
            OPTIONAL MATCH (e)-[:STRUCK]->(pf:Prefecture)
            RETURN e, fz.name AS fault_zone,
                   t.max_height_m AS tsunami_height_m,
                   collect(pf.name) AS prefectures
        """, id=eq_id)
        if not rows:
            return None
        r = rows[0]
        node = dict(r["e"])
        node.pop("embedding", None)
        node["fault_zone"]       = r["fault_zone"]
        node["tsunami_height_m"] = r["tsunami_height_m"]
        node["prefectures"]      = r["prefectures"]
        return node

    async def find_similar_events(self, lat: float, lon: float,
                                  magnitude: float, top_k: int = 5) -> list[dict]:
        return await self.run("""
            MATCH (e:Earthquake)
            WHERE abs(e.lat - $lat) < 3 AND abs(e.lon - $lon) < 3
              AND abs(e.magnitude - $mag) < 1.5
            OPTIONAL MATCH (e)-[:ORIGINATED_ON]->(fz:FaultZone)
            OPTIONAL MATCH (e)-[:TRIGGERED]->(t:Tsunami)
            RETURN e.id AS id, e.magnitude AS magnitude, e.year AS year,
                   e.place AS place, e.depth_km AS depth_km,
                   e.deaths AS deaths, fz.name AS fault_zone,
                   t.max_height_m AS tsunami_height_m
            ORDER BY abs(e.magnitude - $mag) + abs(e.lat - $lat) + abs(e.lon - $lon)
            LIMIT $k
        """, lat=lat, lon=lon, mag=magnitude, k=top_k)

    async def graph_summary(self) -> dict:
        rows = await self.run("""
            MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count
        """)
        return {r["type"]: r["count"] for r in rows if r["type"]}


def get_db():
    return Neo4jService()
