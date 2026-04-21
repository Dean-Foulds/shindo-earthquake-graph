import os
from typing import Optional
from neo4j import GraphDatabase

VOYAGE_MODEL = "voyage-3"
EMBED_DIM    = 1024

class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        self._vo = None

    def _voyage(self):
        if not self._vo:
            import voyageai
            self._vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
        return self._vo

    def run(self, query, **params):
        with self.driver.session() as session:
            return [r.data() for r in session.run(query, **params)]

    def embed_query(self, text: str) -> list[float]:
        result = self._voyage().embed([text], model=VOYAGE_MODEL, input_type="query")
        return result.embeddings[0]

    # ── Semantic search ──────────────────────────────────────────
    def semantic_search(self, query: str, label: str = "Earthquake", top_k: int = 5) -> list[dict]:
        """Vector similarity search over any embedded node type."""
        index_map = {
            "Earthquake":      "earthquake_embedding",
            "FaultZone":       "fault_zone_embedding",
            "NuclearFacility": "nuclear_embedding",
            "Prefecture":      "prefecture_embedding",
        }
        idx = index_map.get(label, "earthquake_embedding")
        vec = self.embed_query(query)
        with self.driver.session() as s:
            rows = s.run(f"""
                CALL db.index.vector.queryNodes('{idx}', $k, $vec)
                YIELD node, score
                RETURN node, score
                ORDER BY score DESC
            """, k=top_k, vec=vec)
            results = []
            for r in rows:
                node = dict(r["node"])
                node.pop("embedding", None)   # don't send vectors to Claude
                results.append({"score": round(r["score"], 4), "node": node})
            return results

    # ── Safe read-only Cypher ────────────────────────────────────
    def cypher_read(self, query: str, params: Optional[dict] = None) -> list[dict]:
        """Execute a read-only Cypher query. Raises if query contains writes."""
        forbidden = ("CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DROP", "CALL {")
        upper = query.upper()
        for kw in forbidden:
            if kw in upper:
                raise ValueError(f"Write operation not allowed: {kw}")
        with self.driver.session() as s:
            return [r.data() for r in s.run(query, **(params or {}))]

    # ── Convenience fetchers ─────────────────────────────────────
    def get_earthquake(self, eq_id: str) -> Optional[dict]:
        rows = self.run("""
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

    def find_similar_events(self, lat: float, lon: float,
                            magnitude: float, top_k: int = 5) -> list[dict]:
        """Find historical earthquakes near a location and magnitude."""
        rows = self.run("""
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
        return rows

    def graph_summary(self) -> dict:
        rows = self.run("""
            MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count
        """)
        return {r["type"]: r["count"] for r in rows if r["type"]}


def get_db():
    return Neo4jService()
