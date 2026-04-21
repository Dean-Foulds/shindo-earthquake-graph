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
