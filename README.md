# Shindo — Japan Seismic Risk Intelligence Graph

**Agent Name: 震度 (Shindo)**

Japan's seismic intensity scale. A cascading risk graph that connects earthquakes, fault zones, tsunamis, nuclear facilities, and prefectures — so an AI agent can reason over disaster chains, not just look up events.

---

## Submission

| | |
|---|---|
| **Agent Name** | 震度 Shindo |
| **Dataset** | USGS Earthquake Hazards Program (~20,000 M4.0+ events, 1950–2024) + IAEA PRIS nuclear reactor registry + curated fault zone and prefecture reference data |
| **Why a graph** | Japan's disasters cascade. A CSV stores events. A graph stores the chain — and an agent can traverse it. |
| **Tools implemented** | Cypher Template · Text2Cypher · Similarity Search |

> Screenshots and live agent link below.

---

## What Is the Shindo Scale?

震度 (shindo) is Japan's official seismic intensity scale, published by the Japan Meteorological Agency (JMA). Unlike moment magnitude (Mw), which measures energy released at the source, Shindo measures **the intensity of shaking at a specific location**. The same earthquake registers a different Shindo value in Tokyo versus Osaka.

| Shindo | JMA Level | Typical Effects |
|--------|-----------|----------------|
| 0 | Micro | Not felt |
| 1 | Minor | Felt by still observers indoors |
| 2 | Light | Hanging objects sway noticeably |
| 3 | Weak | Dishes rattle; felt outdoors |
| 4 | Moderate | Unstable objects fall; most people frightened |
| 5 Lower | Strong | Heavy furniture moves; many seek safety |
| 5 Upper | Strong | Many people cannot move without holding on |
| 6 Lower | Very Strong | Impossible to stand; partial building collapse |
| 6 Upper | Very Strong | Cannot move at all; most unreinforced buildings collapse |
| 7 | Violent | Ground deforms; landslides; extreme tsunami risk |

Key distinctions:
- **Location-based** — JMA broadcasts per-municipality readings, not per-earthquake values
- **5 and 6 split** into Lower (弱) and Upper (強) for resolution at the most damaging range
- **7 is the ceiling** — the 2011 Tōhoku earthquake registered 7 in parts of Miyagi
- **Not logarithmic** — levels are defined by observable damage, not a formula

This agent is named 震度 because it reasons about local impact and cascading consequences — not just raw magnitude at the source.

---

## Why This Dataset, Why a Graph

Japan is the most earthquake-instrumented country on Earth. The risk architecture is genuinely layered, which is exactly what makes a graph matter over a table.

**The core idea: don't build an earthquake lookup. Build a cascading risk graph.**

Japan's disasters don't happen in isolation. They chain:

```
Fault rupture → Ground shaking → Tsunami generation → Prefecture inundation → Nuclear facility exposure
```

A CSV stores events. A graph stores that chain — and an agent can traverse it in a single query.

**The nuclear proximity layer is the distinguishing move.** Post-Fukushima, this is the question that actually matters in Japanese disaster planning. In SQL you'd need a spatial join, a subquery, and three table hops. In Cypher:

```cypher
MATCH (eq:Earthquake)-[:WITHIN_50KM_OF]->(nf:NuclearFacility)
WHERE eq.magnitude >= 6.5
RETURN eq.time, eq.magnitude, nf.name, nf.status
```

**The submission story:** The 2011 Tōhoku earthquake didn't just happen — it traversed a graph.

```
Japan Trench ruptured
  → M9.1 earthquake struck
    → 40m tsunami generated
      → Miyagi, Iwate, Fukushima inundated
        → Fukushima Daiichi within 10km of impact
          → cascading nuclear crisis
```

Every link in that chain is a graph edge. The agent can trace it, explain it, and ask: which other fault zones have the same potential?

---

## Graph Schema

### Node Labels

| Label | Count | Key Properties |
|-------|-------|----------------|
| `Earthquake` | ~20,000 | `id`, `magnitude`, `depth_km`, `lat`, `lon`, `year`, `decade`, `severity`, `deaths`, `tsunami` |

> `severity` values: `minor` (M<4.0) · `moderate` (M4.0–4.9) · `strong` (M5.0–6.9) · `major` (M7.0–7.9) · `catastrophic` (M8.0+)
| `FaultZone` | 9 | `id`, `name`, `type`, `plates`, `predicted_max_mag`, `last_major_year` |
| `Tsunami` | ~200 | `id`, `max_height_m`, `source_mag`, `year` |
| `Prefecture` | 47 | `id`, `name`, `region`, `lat`, `lon`, `coast`, `population_m` |
| `NuclearFacility` | 15 | `id`, `name`, `lat`, `lon`, `reactors`, `status`, `operator` |
| `Decade` | 8 | `year`, `label` |

### Relationship Types

| Relationship | From → To | Properties | Meaning |
|-------------|-----------|------------|---------|
| `ORIGINATED_ON` | Earthquake → FaultZone | — | Quake occurred on this fault |
| `TRIGGERED` | Earthquake → Tsunami | — | Quake caused a tsunami |
| `STRUCK` | Earthquake → Prefecture | `distance_km` | Nearest affected prefecture |
| `INUNDATED` | Tsunami → Prefecture | — | Tsunami reached this coast |
| `UNDERLIES` | FaultZone → Prefecture | — | Fault runs beneath the prefecture |
| `CONTAINS` | Prefecture → NuclearFacility | — | Plant is in this prefecture |
| `WITHIN_50KM_OF` | Earthquake → NuclearFacility | — | Epicentre within 50km of plant |
| `BORDERS` | Prefecture → Prefecture | — | Geographic adjacency |
| `IN_DECADE` | Earthquake → Decade | — | Temporal grouping |

### Neo4j Best Practices

- **MERGE throughout** — all load scripts are idempotent; safe to re-run without duplicates
- **Constraints before data** — unique constraints on `id`/`year` created first, preventing bad loads
- **Indexes on query hotpaths** — `magnitude`, `year`, `tsunami` indexed for range scans
- **Vector indexes** — `earthquake_embedding`, `fault_zone_embedding`, `nuclear_embedding`, `prefecture_embedding` enable semantic search via `db.index.vector.queryNodes`
- **Read-only guard** — `cypher_read()` in the API rejects any query containing write keywords before it reaches Neo4j
- **No unbounded MATCH** — all queries use `LIMIT` or relationship traversal bounds

---

## The Three Agent Tools

### 1. Cypher Templates

Pre-built queries for the high-value risk questions:

**Cascade trace** — fault zone through to nuclear exposure:
```cypher
MATCH path =
    (fz:FaultZone)<-[:ORIGINATED_ON]-(eq:Earthquake)
    -[:TRIGGERED]->(t:Tsunami)
    -[:INUNDATED]->(pf:Prefecture)
    <-[:CONTAINS]-(nf:NuclearFacility)
WHERE eq.magnitude >= 7.5
RETURN fz.name, eq.magnitude, t.max_height_m, pf.name, nf.name, nf.status
ORDER BY eq.magnitude DESC
```

**Compounded risk corridors** — subduction fault + nuclear + Pacific coast:
```cypher
MATCH (fz:FaultZone)-[:UNDERLIES]->(pf:Prefecture)<-[:CONTAINS]-(nf:NuclearFacility)
WHERE fz.type = 'subduction' AND pf.coast IN ['pacific', 'both']
RETURN pf.name, fz.name, nf.name, fz.predicted_max_mag
ORDER BY fz.predicted_max_mag DESC
```

**Nuclear proximity alerts** — M6.5+ within 50km of any plant:
```cypher
MATCH (eq:Earthquake)-[:WITHIN_50KM_OF]->(nf:NuclearFacility)
WHERE eq.magnitude >= 6.5
MATCH (eq)-[:ORIGINATED_ON]->(fz:FaultZone)
RETURN eq.time, eq.magnitude, nf.name, nf.status, fz.name
ORDER BY eq.magnitude DESC
```

### 2. Text2Cypher

Natural language → Cypher generation. Examples the agent handles:

- *"Which prefectures on the Nankai Trough also have nuclear plants?"*
- *"What M7+ earthquakes struck Miyagi in the 2000s?"*
- *"Which fault zone has caused the most deaths?"*
- *"Show me every earthquake that triggered a tsunami and hit an active nuclear plant"*

### 3. Similarity Search

Given a simulated earthquake (from the live map), the agent finds historical analogs by magnitude, depth, location, and fault type:

```cypher
MATCH (e:Earthquake)
WHERE abs(e.lat - $lat) < 3 AND abs(e.lon - $lon) < 3
  AND abs(e.magnitude - $mag) < 1.5
OPTIONAL MATCH (e)-[:ORIGINATED_ON]->(fz:FaultZone)
OPTIONAL MATCH (e)-[:TRIGGERED]->(t:Tsunami)
RETURN e.id, e.magnitude, e.year, e.place, fz.name, t.max_height_m
ORDER BY abs(e.magnitude - $mag) + abs(e.lat - $lat) + abs(e.lon - $lon)
LIMIT 5
```

Vector semantic search is also available over embedded node descriptions using `voyage-3` (1024-dim) for free-text queries.

---

## Setup — Data Pipeline (Run Once)

### Prerequisites
```bash
pip install requests neo4j python-dotenv voyageai
```

Create `.env` in the project root:
```
NEO4J_URI=neo4j+s://<id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
VOYAGE_API_KEY=<key>
```

### Step 1 — Fetch USGS earthquake data
```bash
python 01_fetch_usgs.py
```
Downloads M4.0+ events for Japan (1950–2024) into `data/earthquakes_raw.json`. Free, no API key. Takes ~2 min.

### Step 2 — Build the graph
```bash
python 02_build_graph.py
```
Loads fault zones, prefectures, nuclear facilities, and all earthquake events. Builds all relationships including geographic proximity. Takes ~5 min. Safe to re-run.

### Step 3 — Add vector embeddings
```bash
python 04_embed_graph.py
```
Embeds all nodes with Voyage AI `voyage-3` and registers vector indexes in Neo4j Aura. Enables semantic search.

### Step 4 — Explore with sample queries
Open Neo4j Aura Console → your instance → **Query** tab. Paste from `03_sample_queries.cypher`.

---

## Backend API (`backend/`)

FastAPI service deployed on Railway (port 8000).

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `NEO4J_URI` | `neo4j+s://<id>.databases.neo4j.io` |
| `NEO4J_USER` | `neo4j` |
| `NEO4J_PASSWORD` | Aura instance password |
| `VOYAGE_API_KEY` | Semantic search embeddings |
| `AURA_CLIENT_ID` | OAuth2 client ID for Aura Agent API |
| `AURA_CLIENT_SECRET` | OAuth2 client secret |
| `AURA_AGENT_URL` | `https://api.neo4j.io/v2beta1/organizations/.../agents/.../invoke` |
| `CORS_ORIGINS` | Comma-separated allowed origins |

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/agent/chat` | Proxy to Neo4j Aura 震度 agent |
| `GET` | `/earthquakes` | Direct Neo4j query (used in tests) |

The `/agent/chat` endpoint prepends an active simulation context block when the user has a scenario running on the map:
```
[ACTIVE SIMULATION] Epicentre: 35.60°N 139.70°E | M7.5 depth 20km |
Fault: Tokyo Metropolitan Fault | Affected: Tokyo, Kanagawa | Tsunami risk: low
```

### Aura Agent OAuth Flow
1. `POST https://api.neo4j.io/oauth/token` — Basic auth (base64 `client_id:client_secret`)
2. Token cached in memory with 30-second expiry buffer
3. All agent calls use `Authorization: Bearer <token>`

### Tests
```bash
cd backend && pytest -v
```
Uses FastAPI `TestClient` with `app.dependency_overrides` to inject a mock DB — no live Neo4j required in CI.

---

## Frontend (`frontend/`)

React + Vite app deployed on Cloudflare Pages.

```bash
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

Set `frontend/.env.local`:
```
VITE_API_URL=http://localhost:8000
```

### Pages

| Route | Component | What it does |
|-------|-----------|-------------|
| `/` | `shindo_live.jsx` | Interactive SVG map of Japan — magnitude/depth sliders, fault zone highlight, prefecture impact, AI chat |
| `/dashboard` | `Dashboard.jsx` | Metrics, decade bar chart, Cypher explorer, AI chat |

Chat history persists across page navigation (state lifted to `App.jsx`, passed as props).

Slider changes trigger a debounced (800ms) re-analysis that updates the fault zone, affected prefectures, tsunami risk, and fetches historical analogs.

---

## Deployment

### Backend — Railway
- Start: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Set all env vars in Railway dashboard
- Add Cloudflare Pages domain to `CORS_ORIGINS`

### Frontend — Cloudflare Pages
- Build: `npm run build` | Output: `dist` | Root: `frontend`
- Set `VITE_API_URL` to the Railway backend URL

### CI/CD — GitHub Actions
Trigger: push to `main`, `develop`, `feature/**`
Jobs: `test` → `build` (Docker) → `deploy` (main only)
