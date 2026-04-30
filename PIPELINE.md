# Data Pipeline Setup (Run Once)

Builds the Neo4j graph from raw USGS and reference data. Only needs to run once; all scripts are safe to re-run (MERGE throughout).

## Prerequisites

```bash
pip install requests neo4j python-dotenv voyageai
```

Create `.env` in the project root:

```env
NEO4J_URI=neo4j+s://<id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
VOYAGE_API_KEY=<key>
```

## Step 1 — Fetch USGS earthquake data

```bash
python 01_fetch_usgs.py
```

Downloads M4.0+ events for Japan (1950–2024) into `data/earthquakes_raw.json`. Free, no API key. Takes ~2 min.

## Step 2 — Build the graph

```bash
python 02_build_graph.py
```

Loads fault zones, prefectures, nuclear facilities, and all earthquake events. Builds all relationships including geographic proximity. Takes ~5 min. Safe to re-run.

> **Note:** Uses UNWIND batching (~200 events per query) and reconnects automatically on Aura session timeout.

## Step 3 — Add vector embeddings

```bash
python 04_embed_graph.py
```

Embeds all nodes with Voyage AI `voyage-3` (1024-dim) and registers vector indexes in Neo4j Aura. Enables semantic search across earthquakes, fault zones, nuclear facilities, and prefectures.

## Step 4 — Explore with sample queries

Open Neo4j Aura Console → your instance → **Query** tab. Paste from `03_sample_queries.cypher`.



---

## Data Pipeline

See [PIPELINE.md](PIPELINE.md) for the full setup guide — fetching USGS data, building the graph, adding vector embeddings, and running sample queries.

---

## Backend API

FastAPI service. All routes are async — uses `AsyncGraphDatabase` and `httpx.AsyncClient`.

### Local development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Set `backend/.env`:

```env
NEO4J_URI=neo4j+s://<id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
VOYAGE_API_KEY=<key>
AURA_CLIENT_ID=<id>
AURA_CLIENT_SECRET=<secret>
AURA_AGENT_URL=https://api.neo4j.io/v2beta1/organizations/.../agents/.../invoke
CORS_ORIGINS=http://localhost:5173
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
| `AURA_AGENT_URL` | Aura agent invoke URL |
| `CORS_ORIGINS` | Comma-separated allowed origins |

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/agent/chat` | Proxy to Neo4j Aura 震度 agent |
| `GET` | `/analysis/predict` | Statistical recurrence analysis (1-hour cache) |
| `GET` | `/earthquakes` | Direct Neo4j query |

### Tests

```bash
cd backend && pytest -v
```

Uses FastAPI `TestClient` with `app.dependency_overrides` — no live Neo4j required in CI.

---

## Frontend

React + Vite app.

### Local development

```bash
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

Set `frontend/.env.local`:

```env
VITE_API_URL=http://localhost:8000
```

### Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `shindo_live.jsx` | Interactive SVG map — simulate earthquakes, fault zone highlighting, AI chat |
| `/dashboard` | `Dashboard.jsx` | EDA charts, risk analysis gauges, Cypher explorer, AI chat |

---

## Deployment

### Backend — Railway

1. Connect the GitHub repo in Railway → select the `backend/` service root
2. Railway detects `railway.toml` and builds via Dockerfile
3. Set all environment variables in the Railway dashboard
4. Add your Cloudflare Pages domain to `CORS_ORIGINS`

**`railway.toml`:**
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"
```

**`Dockerfile` CMD** (shell form required so `$PORT` expands at runtime):
```dockerfile
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Frontend — Cloudflare Pages

| Setting | Value |
|---------|-------|
| Framework preset | Vite |
| Build command | `npm run build` |
| Output directory | `dist` |
| Root directory | `frontend` |
| `VITE_API_URL` | Railway backend URL |

Deploys automatically on push to `main`.

---