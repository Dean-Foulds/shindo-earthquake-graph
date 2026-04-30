# 震度 Shindo — Japan Seismic Risk Intelligence Graph

> **Agent Name: 震度 (Shindo)** — Japan's official seismic intensity scale.  
> A cascading risk graph that connects earthquakes, fault zones, tsunamis, nuclear facilities, and prefectures — so an AI agent can reason over disaster chains, not just look up events.

---

## Neo4j Competition Submission

### Agent Name

**震度 Shindo** — named after Japan's official seismic intensity scale (JMA). Shindo measures the intensity of shaking at a specific location, not just the energy at the source. This agent reasons the same way: local impact and cascading consequences, not just raw magnitude.

### What It Does

震度 Shindo is a seismic intelligence agent for Japan. The user clicks anywhere on a live SVG map to place a simulated earthquake. The agent immediately analyses the event against the graph:

- Which fault zone ruptured, and what is its historical overdue ratio?
- Which prefectures are in the felt zone? Which have nuclear facilities?
- Are there historical analogs in the graph? What happened then?
- Is tsunami risk expected given the fault type and depth?

Every claim the agent makes is anchored to a Cypher query result from the graph — no hallucination.

Beyond the map there are three analytical views:

- **EDA Charts** — decade-by-decade event counts, fault zone death totals, prefecture composite risk index
- **Risk Analysis** — statistical recurrence gauges: how long since each fault zone last had a major event versus its historical average interval, expressed as an overdue ratio
- **Cypher Queries** — graph schema explorer with template query patterns pre-loaded

### Dataset and Why a Graph Fits

**Dataset:** USGS Earthquake Hazards Program (~20,000 M4.0+ events, 1950–2024) + IAEA PRIS nuclear reactor registry + curated fault zone reference data + JMA prefecture data (47 prefectures with coastal classifications).

**Why a graph:** Japan's disasters don't happen in isolation — they cascade:

```
Fault rupture → Ground shaking → Tsunami generation → Prefecture inundation → Nuclear facility exposure
```

A CSV stores events. A graph stores the chain — and an agent can traverse it in a single query. The nuclear proximity layer is the distinguishing move. Post-Fukushima, this is the question that actually matters in Japanese disaster planning. In SQL you'd need a spatial join, a subquery, and three table hops. In Cypher:

```cypher
MATCH (eq:Earthquake)-[:WITHIN_50KM_OF]->(nf:NuclearFacility)
WHERE eq.magnitude >= 6.5
RETURN eq.time, eq.magnitude, nf.name, nf.status
```

The 2011 Tōhoku earthquake didn't just happen — it traversed a graph:

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

### Agent in the Aura Console

**Graph visualisation — full schema, all node types connected:**

![Aura console — full graph schema visualisation with STRUCK relationship query](data/Pasted%20image%20(10).png)

**Nuclear proximity layer — WITHIN_50KM_OF relationship between earthquakes and facilities:**

![Aura console — WITHIN_50KM_OF graph showing earthquake-to-nuclear-facility proximity edges](data/Pasted%20image%20(11).png)

**Agent configuration — 震度 Shindo agent wired to the Earthquake Data instance:**

![Aura agent config — instance, prompt instructions, and preview chat showing 137 M5+ events in 2023](data/Pasted%20image%20(12).png)

**All nine Cypher Template tools registered on the agent:**

![Aura agent config — cascade_trace, compound_risk_corridors, historical_analog_finder, nuclear_proximity_risk, decade_pattern_analysis, fault_zone_lethality, the_hamoaka_question, region_vulnerability_score, graph_summary](data/Pasted%20image%20(13).png)

---

### Agent in Action

**Live map — Japan with all fault zones rendered, ready to simulate:**

![Shindo live map — Japan SVG with fault zone overlays and agent chat panel](data/Pasted%20image.png)

**Active simulation — epicentre placed, impact zone calculated, nuclear exposure flagged:**

![Simulation running — affected prefectures highlighted, nuclear proximity risk shown](data/Pasted%20image%20(2).png)

**Agent analysis — structured response grounded in graph data:**

![Agent response to "give me your analysis of this event"](data/Pasted%20image%20(3).png)

**Data Analysis Dashboard — EDA Charts: decade bar chart, fault zone deaths, prefecture risk index:**

![EDA charts dashboard — 4,720 total events, M9.1 max, decade breakdown, fault zone lethality](data/Pasted%20image%20(4).png)

**Dashboard with agent responding to event analysis alongside EDA charts:**

![Dashboard with agent chat active alongside EDA charts and risk tab](data/Pasted%20image%20(5).png)

**Risk Analysis tab — statistical recurrence overview with disclaimer:**

![Risk analysis tab — historical overdue ratio explanation and top overdue fault zones](data/Pasted%20image%20(6).png)

**Risk Analysis — per-fault-zone gauges (Noto Peninsula, Ryukyu Trench, Sagami Trough):**

![Fault zone overdue ratio gauges — Noto 0.18×, Ryukyu 1.67×, Sagami 4.33×](data/Pasted%20image%20(7).png)

**Cypher Queries tab — graph schema explorer with four template patterns:**

![Cypher explorer — schema diagram and template query list](data/Pasted%20image%20(8).png)

**Cascade trace query executed — fault zone through to nuclear facility:**

![Cascade trace Cypher results — full chain from fault zone to nuclear facility](data/Pasted%20image%20(9).png)

### Live Agent

**Frontend:** [shindo.pages.dev](https://shindo-earthquake-graph.pages.dev/)

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

This agent is named 震度 because it reasons about local impact and cascading consequences — not just raw magnitude at the source.

---

## Graph Schema

### Node Labels

| Label | Count | Key Properties |
|-------|-------|----------------|
| `Earthquake` | ~20,000 | `id`, `magnitude`, `depth_km`, `lat`, `lon`, `year`, `decade`, `severity`, `deaths`, `tsunami` |
| `FaultZone` | 9 | `id`, `name`, `type`, `plates`, `predicted_max_mag`, `last_major_year` |
| `Tsunami` | ~200 | `id`, `max_height_m`, `source_mag`, `year` |
| `Prefecture` | 47 | `id`, `name`, `region`, `lat`, `lon`, `coast`, `population_m` |
| `NuclearFacility` | 15 | `id`, `name`, `lat`, `lon`, `reactors`, `status`, `operator` |
| `Decade` | 8 | `year`, `label` |

> `severity` values: `minor` (M<4.0) · `moderate` (M4.0–4.9) · `strong` (M5.0–6.9) · `major` (M7.0–7.9) · `catastrophic` (M8.0+)

### Relationship Types

| Relationship | From → To | Meaning |
|-------------|-----------|---------|
| `ORIGINATED_ON` | Earthquake → FaultZone | Quake occurred on this fault |
| `TRIGGERED` | Earthquake → Tsunami | Quake caused a tsunami |
| `STRUCK` | Earthquake → Prefecture | Nearest affected prefecture |
| `INUNDATED` | Tsunami → Prefecture | Tsunami reached this coast |
| `UNDERLIES` | FaultZone → Prefecture | Fault runs beneath the prefecture |
| `CONTAINS` | Prefecture → NuclearFacility | Plant is in this prefecture |
| `WITHIN_50KM_OF` | Earthquake → NuclearFacility | Epicentre within 50km of plant |
| `BORDERS` | Prefecture → Prefecture | Geographic adjacency |
| `IN_DECADE` | Earthquake → Decade | Temporal grouping |

### Neo4j Best Practices Used

- **MERGE throughout** — all load scripts are idempotent; safe to re-run without duplicates
- **Constraints before data** — unique constraints on `id`/`year` created first
- **Indexes on query hotpaths** — `magnitude`, `year`, `tsunami` indexed for range scans
- **Vector indexes** — `earthquake_embedding`, `fault_zone_embedding`, `nuclear_embedding`, `prefecture_embedding` via `db.index.vector.queryNodes`
- **Read-only guard** — `cypher_read()` in the API rejects any query containing write keywords before it reaches Neo4j

---

## Agent Tools

### Cypher Templates (9 registered)

| Tool | Description |
|------|-------------|
| `the_cascade_trace` | Full chain: fault zone → earthquake → tsunami → prefecture → nuclear facility |
| `compund_risk_corridors` | Subduction faults overlapping nuclear-hosting, Pacific-coast prefectures |
| `historical_analog_finder` | Past events near a given location and magnitude |
| `nuclear_proximaty_risk` | M6.5+ events within 50km of any nuclear plant |
| `decade_patter_analysis` | Event counts and deaths grouped by decade |
| `fault_zone_leathality` | Total deaths attributed to each fault zone |
| `the_hamoaka_question` | Hamaoka nuclear plant specific risk analysis |
| `region_vunrability_score` | Composite risk score per prefecture |
| `graph_summary` | Node and relationship counts across the full graph |

### Text2Cypher

Natural language → Cypher generation. Examples:

- *"Which prefectures on the Nankai Trough also have nuclear plants?"*
- *"What M7+ earthquakes struck Miyagi in the 2000s?"*
- *"Which fault zone has caused the most deaths?"*
- *"Show me every earthquake that triggered a tsunami and hit an active nuclear plant"*

### Similarity Search

Given a simulated earthquake, the agent finds historical analogs by magnitude, depth, and location:

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

Vector semantic search is also available over node embeddings using Voyage AI `voyage-3` (1024-dim).

---

