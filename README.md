# Shindo — Japan Seismic Risk Intelligence Graph

**震度** (shindo) — Japan's seismic intensity scale. The name for this agent.

A Neo4j knowledge graph that connects earthquakes, fault zones, tsunamis,
nuclear facilities, and prefectures — so an AI agent can reason over
cascading disaster risk, not just look up events.

---

## Setup (5 minutes)

### Prerequisites
```bash
pip install requests neo4j pandas
```

### Step 1 — Fetch earthquake data from USGS
```bash
python 01_fetch_usgs.py
```
Downloads ~5,000 M5.0+ events for Japan (1950–2024) into `data/earthquakes_raw.json`.
Takes ~2 minutes. USGS is free, no API key needed.

### Step 2 — Build the graph in Neo4j Aura
```bash
python 02_build_graph.py \
  --uri "neo4j+s://XXXXXXXX.databases.neo4j.io" \
  --user neo4j \
  --password "YOUR_PASSWORD"
```

Or use environment variables:
```bash
export NEO4J_URI="neo4j+s://XXXXXXXX.databases.neo4j.io"
export NEO4J_PASSWORD="YOUR_PASSWORD"
python 02_build_graph.py
```

Takes ~5 minutes. Safe to re-run (idempotent — uses MERGE).

### Step 3 — Explore with sample queries
Open Neo4j Aura Console → your instance → **Query** tab.
Paste queries from `03_sample_queries.cypher`.

---

## What's in the graph

| Node type        | Count (approx) | Key properties                              |
|------------------|---------------|----------------------------------------------|
| Earthquake       | ~5,000        | magnitude, depth_km, lat, lon, tsunami, year |
| FaultZone        | 9             | name, type, predicted_max_mag                |
| Prefecture       | 47            | name, region, coast, population_m            |
| NuclearFacility  | 15            | name, status, reactors, operator             |
| Tsunami          | ~200          | max_height_m, year                           |
| Decade           | 8             | year, label                                  |

| Relationship       | Meaning                                         |
|--------------------|-------------------------------------------------|
| ORIGINATED_ON      | Earthquake → FaultZone                          |
| STRUCK             | Earthquake → Prefecture (nearest centroid)      |
| TRIGGERED          | Earthquake → Tsunami                            |
| INUNDATED          | Tsunami → Prefecture                            |
| UNDERLIES          | FaultZone → Prefecture                          |
| CONTAINS           | Prefecture → NuclearFacility                    |
| WITHIN_50KM_OF     | Earthquake → NuclearFacility (spatial)          |
| BORDERS            | Prefecture → Prefecture                         |
| IN_DECADE          | Earthquake → Decade                             |

---

## The 3 agent tools to configure in Neo4j Aura

### 1. Cypher templates
Pre-built queries for common risk questions:
- Cascade trace (fault → quake → tsunami → prefecture → nuclear)
- Compounded risk corridors
- Nuclear proximity alerts

### 2. Text2Cypher
Natural language → Cypher generation.
Works well for: "Which prefectures on the Nankai Trough also have nuclear plants?"

### 3. Similarity search
Find historical earthquakes similar to a given event by
magnitude, depth, and fault type.

---

## Why a graph?

A CSV can tell you *what* happened.
A graph can tell you *why it was devastating* — by traversing the
connections between the fault that ruptured, the prefecture it hit,
the tsunami it generated, and the nuclear plant 8km away.

The query that makes this real:

```cypher
MATCH path =
    (fz:FaultZone)<-[:ORIGINATED_ON]-(eq:Earthquake)
    -[:TRIGGERED]->(t:Tsunami)
    -[:INUNDATED]->(pf:Prefecture)
    <-[:CONTAINS]-(nf:NuclearFacility)
WHERE eq.magnitude >= 7.5
RETURN fz.name, eq.magnitude, t.max_height_m, pf.name, nf.name, nf.status
```

That traversal is impossible to express cleanly in SQL.
In Cypher, it's one `MATCH` statement.
