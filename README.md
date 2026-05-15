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
| `Earthquake` | ~33,875 | `id`, `momentMagnitude`, `hypocentralDepthKm`, `epicentreLat`, `epicentreLon`, `occurrenceDateTime`, `year`, `decade`, `severity`, `faultType`, `seaFloorDepthM`, `jmaIntensity`, `significanceScore` |
| `FaultZone` | 9 | `id`, `name`, `type`, `plates`, `predicted_max_mag`, `last_major_year` |
| `Tsunami` | ~180 | `id`, `waveHeightAtShoreM`, `tsunamiIntensity`, `iidaMagnitude`, `tsunamiFatalities`, `buildingsWashedAway`, `numberOfRunups`, `oceanicTsunami` |
| `Prefecture` | 47 | `id`, `name`, `region`, `lat`, `lon`, `coast`, `population_m`, `prefectureCode` |
| `NuclearFacility` | 15 | `id`, `name`, `lat`, `lon`, `reactors`, `status`, `operator` |
| `Decade` | 8 | `year`, `label` |
| `ShakingDamage` | 6 | `shakingFatalities`, `shakingInjuries`, `buildingsTotallyDestroyed` |
| `TsunamiEvent` | 5 | `tsunamiGenerated`, `minutesToShore` |
| `InundationZone` | 5 | `inundationDistanceKm`, `maxInlandElevationM`, `inundationAreaKm2` |
| `LandslideRisk` | 5 | `landslideRiskLevel`, `landslideOccurred`, `numberOfLandslides`, `terrainType` |
| `FireAfterQuake` | 4 | `numberOfFires`, `fireCause`, `areaBurnedHectares`, `buildingsBurnedDown` |
| `TsunamiWarning` | 4 | `warningLevel`, `minutesFromQuakeToWarning` |
| `WaveProfile` | 3 | `waveHeightAtSourceM`, `waveHeightAtShoreM`, `waveSpeedKmh` |
| `TsunamiDamage` | 3 | `tsunamiFatalities`, `tsunamiMissing`, `buildingsWashedAway` |
| `NuclearIncident` | 3 | `facilityName`, `inesLevel`, `scramActivated`, `coolingSystemIntact` |
| `DamageReport` | 3 | `reportDateTime`, `reportedBy` |
| `City` | 33 | `cityName`, `distanceFromEpicentreKm` |

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
| `hasDamageReport` | Earthquake → DamageReport | Links event to damage assessment |
| `hasShakingDamage` | Earthquake → ShakingDamage | Ground shaking casualties and buildings |
| `hasFireRisk` | Earthquake → FireAfterQuake | Post-earthquake fire data |
| `hasLandslideRisk` | Earthquake → LandslideRisk | Terrain-triggered landslide data |
| `hasNuclearIncident` | Earthquake → NuclearIncident | Nuclear facility impact record |
| `triggeredTsunami` | Earthquake → TsunamiEvent | Detailed tsunami chain |
| `hasWarning` | TsunamiEvent → TsunamiWarning | JMA warning issued |
| `hasWaveProfile` | TsunamiEvent → WaveProfile | Wave physics measurements |
| `causedInundation` | TsunamiEvent → InundationZone | Inland flooding extent |
| `hasTsunamiDamage` | InundationZone → TsunamiDamage | Water damage record |
| `inundatedPrefecture` | InundationZone → Prefecture | Which prefecture was flooded |
| `affectsPrefecture` | Earthquake → Prefecture | Broader felt-zone coverage |

### Neo4j Best Practices Used

- **MERGE throughout** — all load scripts are idempotent; safe to re-run without duplicates
- **Constraints before data** — unique constraints on `id`/`year` created first
- **Indexes on query hotpaths** — `momentMagnitude`, `year`, `faultType`, `seaFloorDepthM` indexed for range scans
- **Vector indexes** — 12 total: `earthquake_embedding`, `fault_zone_embedding`, `nuclear_embedding`, `prefecture_embedding`, `tsunami_embedding` + 7 new indexes for Perseus-added node types, all using Voyage AI `voyage-3` (1024-dim)
- **Read-only guard** — `cypher_read()` in the API rejects any query containing write keywords before it reaches Neo4j

---

## Formal Ontology

**Base URI:** `http://deanfoulds.xyz/ontology/earthquake#`  
**Format:** Turtle (TTL) — W3C standard RDF serialisation  
**Language:** OWL 2 with RDFS annotations  
**Bilingual:** All classes and properties labelled in English (`@en`) and Japanese (`@ja`)  
**File:** `ontology/japanese_earthquake.ttl`

### OWL Classes (13)

#### Seismic Event Classes

| Class | Japanese | Description |
|---|---|---|
| `Earthquake` | 地震 | Core seismic event |
| `TsunamiEvent` | 津波 | Tsunami triggered by an earthquake |
| `TsunamiWarning` | 津波警報 | JMA-issued warning (Advisory / Warning / Major Warning) |
| `WaveProfile` | 津波波形 | Physical wave characteristics at source and shore |
| `InundationZone` | 浸水域 | Area of land flooded by tsunami inland penetration |
| `TsunamiDamage` | 津波被害 | Damage caused by water (separate from shaking damage) |

#### Geographic Classes

| Class | Japanese | Description |
|---|---|---|
| `Prefecture` | 都道府県 | Administrative division of Japan |
| `City` | 市区町村 | City, town or village |

#### Damage Classes (all subclasses of DamageReport)

| Class | Japanese | Description |
|---|---|---|
| `DamageReport` | 被害報告 | Parent damage assessment class |
| `ShakingDamage` | 揺れによる被害 | Ground shaking damage — casualties and buildings |
| `FireAfterQuake` | 地震後火災 | Post-earthquake fires from gas lines, electrical faults |
| `LandslideRisk` | 土砂災害リスク | Landslide triggered by shaking in mountainous terrain |
| `NuclearIncident` | 原子力事故 | Nuclear facility impact or risk (INES scale) |

### Object Property Map

```
Earthquake ──[hasEpicentre]──────────────► Epicentre
Earthquake ──[affectsPrefecture]──────────► Prefecture
Earthquake ──[triggeredTsunami]───────────► TsunamiEvent
Earthquake ──[hasDamageReport]────────────► DamageReport
Earthquake ──[hasShakingDamage]───────────► ShakingDamage
Earthquake ──[hasFireRisk]────────────────► FireAfterQuake
Earthquake ──[hasLandslideRisk]───────────► LandslideRisk
Earthquake ──[hasNuclearIncident]─────────► NuclearIncident
TsunamiEvent ──[hasWarning]───────────────► TsunamiWarning
TsunamiEvent ──[hasWaveProfile]───────────► WaveProfile
TsunamiEvent ──[causedInundation]─────────► InundationZone
InundationZone ──[hasTsunamiDamage]───────► TsunamiDamage
InundationZone ──[inundatedPrefecture]────► Prefecture
```

### Data Properties

#### Earthquake Node

| Property | Type | Description | Source |
|---|---|---|---|
| `occurrenceDateTime` | xsd:dateTime | Event date and time (UTC) | USGS / JMA |
| `epicentreLat` | xsd:decimal | Epicentre latitude | USGS / JMA |
| `epicentreLon` | xsd:decimal | Epicentre longitude | USGS / JMA |
| `hypocentralDepthKm` | xsd:decimal | Depth below surface (km) | USGS / JMA |
| `momentMagnitude` | xsd:decimal | Moment magnitude (Mw) | USGS / JMA |
| `jmaIntensity` | xsd:string | JMA seismic intensity (0–7) | JMA |
| `faultType` | xsd:string | subduction / strike-slip / reverse | Inferred |
| `seaFloorDepthM` | xsd:decimal | GEBCO sea floor depth at epicentre (m) | GEBCO 2026 |
| `significanceScore` | xsd:integer | USGS significance score | USGS |
| `source` | xsd:string | Data origin (`USGS`, `JMA_LIVE`, `usgs_live`) | Pipeline |

#### Tsunami Node

| Property | Type | Description | Source |
|---|---|---|---|
| `waveHeightAtShoreM` | xsd:decimal | Maximum observed wave height at shore (m) | NOAA NCEI |
| `tsunamiIntensity` | xsd:decimal | Iida-Imamura tsunami intensity | NOAA NCEI |
| `iidaMagnitude` | xsd:decimal | Iida tsunami magnitude | NOAA NCEI |
| `tsunamiFatalities` | xsd:integer | Deaths directly from tsunami | NOAA NCEI |
| `buildingsWashedAway` | xsd:integer | Buildings destroyed by water | NOAA NCEI |
| `numberOfRunups` | xsd:integer | Number of observation points | NOAA NCEI |
| `oceanicTsunami` | xsd:boolean | Whether wave crossed open ocean | NOAA NCEI |

### JMA Tsunami Warning Levels

| Level | Japanese | Magnitude Threshold | Expected Wave |
|---|---|---|---|
| Major Tsunami Warning | 大津波警報 | M ≥ 8.0 | > 3m |
| Tsunami Warning | 津波警報 | M ≥ 7.0 | 1–3m |
| Tsunami Advisory | 津波注意報 | M ≥ 6.0 | < 1m |

JMA issues warnings within 3 minutes of detection based on magnitude and epicentre location alone. This rule is implemented in `backend/app/agent/tools/jma_warning.py`.

---

## Data Sources & Enrichment Pipeline

The graph was built in three stages: raw ingestion, schema enrichment, and knowledge enrichment via Perseus NLP.

### Stage 1 — Raw Ingestion

**Script:** `01_fetch_usgs.py`  
**Source:** USGS Earthquake Hazards Program  
**Coverage:** M4.0+ events, Japan bounding box (24°N–46°N, 122°E–148°E), 1950–2024  
**Method:** Fetched in decade chunks (USGS caps single requests at 20,000 events)  
**Output:** `data/earthquakes_raw.json` — ~20,000 events

**Script:** `02_build_graph.py`  
Loads raw JSON to Neo4j, creates all constraints and indexes, and builds the initial node/relationship structure.

### Stage 2 — Field Enrichment

#### GEBCO Sea Floor Depth

**Script:** `data/enrichment/gebco_enrichment.py`  
**Field added:** `seaFloorDepthM`  
**Source:** GEBCO 2026 Grid NetCDF (bounding box 20°N–50°N, 120°E–150°E)

Sea floor depth at the epicentre is critical for tsunami simulation — a shallow shelf quake and a deep trench quake of identical magnitude produce fundamentally different waves. Without this field, nearest-neighbour inference is unreliable.

**Method:** All 32,976 lat/lon pairs vectorised as a single numpy operation against a `RegularGridInterpolator` (~30 seconds vs ~5 hours for individual API calls), written back in batches of 1,000.

| Metric | Value |
|---|---|
| Nodes enriched | 32,976 |
| Deepest ocean event | -9,781m |
| Highest land event | +2,620m |
| Average depth | -2,206m |
| Offshore events | 29,334 (89%) |
| Onshore events | 3,642 (11%) |

#### NOAA Tsunami Wave Data

**Script:** `data/enrichment/noaa_tsunami_enrichment.py`  
**Source:** NOAA NCEI Global Historical Tsunami Database (Japan, 1952–2024)

The original Tsunami nodes were sparse (id, earthquake_id, source_mag, year only). NOAA data provides measured wave heights and damage records the nearest-neighbour engine needs.

**Matching strategy:** Match by year (exact) + lat/lon within 1 degree — closest geographic match wins. Enriches existing Tsunami nodes if linked, creates and links new ones if not.

| NOAA Field | Ontology Property | Coverage |
|---|---|---|
| `maxWaterHeight` | `waveHeightAtShoreM` | 93% |
| `tsIntensity` | `tsunamiIntensity` | 42% |
| `tsMtIi` | `iidaMagnitude` | 42% |
| `deaths` | `tsunamiFatalities` | 7% |
| `deathsTotal` | `tsunamiFatalitiesTotal` | 16% |
| `injuriesTotal` | `tsunamiInjuriesTotal` | 16% |
| `housesDestroyedTotal` | `buildingsWashedAway` | 16% |
| `numRunups` | `numberOfRunups` | 100% |
| `oceanicTsunami` | `oceanicTsunami` | 100% |

| Outcome | Count |
|---|---|
| Enriched existing Tsunami nodes | 41 |
| Created new Tsunami nodes | 88 |
| Created standalone new pairs | 3 |
| **Total processed** | **135** |

> **Data quality note:** NOAA `maxWaterHeight` for 2011 Tōhoku shows 0.06m (offshore buoy reading, not the 40m coastal runup). The nearest-neighbour query filters `waveHeightAtShoreM > 0.1` to exclude likely offshore sensor readings. Deaths and building damage are only 7–16% filled for pre-1980 events.

#### Fault Type Inference

Fault type inferred directly in Cypher — no separate script.

| Rule | Assigned Type |
|---|---|
| `hypocentralDepthKm > 150` | `subduction` (deep slab) |
| `epicentreLon > 141` AND `epicentreLat > 35` AND `depth < 100` | `subduction` (Pacific plate) |
| `epicentreLon < 136` AND `epicentreLat < 34` | `subduction` (Philippine plate) |
| `hypocentralDepthKm < 20` | `strike-slip` (shallow inland) |
| `depth 20–60km` AND inland Japan | `reverse` |

| Fault Type | Count | % |
|---|---|---|
| subduction | 26,781 | 81% |
| strike-slip | 3,489 | 11% |
| reverse | 2,706 | 8% |

81% subduction is geologically correct — Japan sits at the junction of four tectonic plates.

```cypher
CALL apoc.periodic.iterate(
  "MATCH (e:Earthquake) RETURN e",
  "SET e.faultType = CASE
     WHEN e.hypocentralDepthKm > 150 THEN 'subduction'
     WHEN e.epicentreLon > 141.0
      AND e.epicentreLat > 35.0
      AND e.hypocentralDepthKm < 100 THEN 'subduction'
     WHEN e.epicentreLon < 136.0
      AND e.epicentreLat < 34.0 THEN 'subduction'
     WHEN e.hypocentralDepthKm < 20 THEN 'strike-slip'
     WHEN e.hypocentralDepthKm >= 20
      AND e.hypocentralDepthKm <= 60
      AND e.epicentreLon >= 130.0
      AND e.epicentreLon <= 141.0 THEN 'reverse'
     ELSE 'unknown'
   END",
  {batchSize: 500}
)
```

#### Schema Migration

The original USGS dataset used different property names — these were renamed to match the ontology via APOC batch operations.

| Original | Ontology |
|---|---|
| `lat` | `epicentreLat` |
| `lon` | `epicentreLon` |
| `depth_km` | `hypocentralDepthKm` |
| `magnitude` | `momentMagnitude` |
| `time` | `occurrenceDateTime` |
| `sig` | `significanceScore` |

```cypher
CALL apoc.periodic.iterate(
  "MATCH (e:Earthquake) RETURN e",
  "SET e.occurrenceDateTime  = e.time,
       e.epicentreLat        = e.lat,
       e.epicentreLon        = e.lon,
       e.hypocentralDepthKm  = e.depth_km,
       e.momentMagnitude     = e.magnitude,
       e.significanceScore   = e.sig
   REMOVE e.time, e.lat, e.lon,
          e.depth_km, e.magnitude, e.sig",
  {batchSize: 500}
)
```

#### Vector Embeddings

**Script:** `04_embed_graph.py`  
**Model:** Voyage AI `voyage-3` (1024-dim)  
**Scope:** All node types — Earthquake, FaultZone, NuclearFacility, Prefecture, Tsunami, plus all 7 Perseus-added types  
**Total indexes:** 12 vector indexes in Neo4j Aura

---

## Perseus Knowledge Graph Enrichment

The OWL ontology was used to guide structured extraction from natural language disaster reports using [Lettria Perseus](https://docs.perseus.lettria.net).

### Source Documents

`data/japanese_earthquake_events.txt` — prose reports covering six major historical events:

| Event | Date | Magnitude |
|---|---|---|
| Tōhoku Earthquake and Tsunami | 11 March 2011 | M9.1 |
| Great Hanshin Earthquake (Kobe) | 17 January 1995 | M6.9 |
| Noto Peninsula Earthquake | 1 January 2024 | M7.6 |
| Fukushima Aftershock | 11 April 2011 | M7.1 |
| Kumamoto Earthquakes | 14–16 April 2016 | M6.2 / M7.0 |
| Tokachi-Oki Earthquake | 26 September 2003 | M8.3 |

### Extraction Pipeline

1. TTL ontology uploaded to Perseus console as the extraction schema
2. Source text file uploaded to Perseus Files
3. Graph built — Perseus extracted entities and relationships from prose
4. Graph exported as CQL and migrated to Neo4j Aura
5. 15 duplicate Prefecture nodes merged using `apoc.refactor.mergeNodes`
6. All new node types embedded with Voyage AI `voyage-3` via `04_embed_graph.py`

### Nodes Added to Neo4j

| Node label | Count | Key properties |
|---|---|---|
| `ShakingDamage` | 6 | shakingFatalities, shakingInjuries, buildingsTotallyDestroyed |
| `TsunamiEvent` | 5 | tsunamiGenerated, minutesToShore |
| `InundationZone` | 5 | inundationDistanceKm, maxInlandElevationM, inundationAreaKm2 |
| `LandslideRisk` | 5 | landslideRiskLevel, landslideOccurred, numberOfLandslides, terrainType |
| `FireAfterQuake` | 4 | numberOfFires, fireCause, areaBurnedHectares, buildingsBurnedDown |
| `TsunamiWarning` | 4 | warningLevel, minutesFromQuakeToWarning |
| `WaveProfile` | 3 | waveHeightAtSourceM, waveHeightAtShoreM, waveSpeedKmh |
| `TsunamiDamage` | 3 | tsunamiFatalities, tsunamiMissing, buildingsWashedAway |
| `NuclearIncident` | 3 | facilityName, inesLevel, scramActivated, coolingSystemIntact |
| `DamageReport` | 3 | reportDateTime, reportedBy |
| `City` | 33 | cityName, distanceFromEpicentreKm |

Perseus also added `prefectureCode` (JIS 2-digit codes) to 15 existing Prefecture nodes, enabling standard administrative lookup.

### Updated Database Statistics

| Metric | Value |
|---|---|
| Total earthquake nodes | 33,875 |
| Prefecture nodes | 47 (JIS codes on 15) |
| City nodes | 33 (sub-prefecture granularity) |
| Damage chain node types | 10 |
| Vector indexes | 12 |

---

## Live Earthquake Feed

The backend continuously ingests real seismic events, keeping the map current.

### Architecture

`backend/app/poller.py` runs as an asyncio background task, launched automatically when FastAPI starts (`backend/app/main.py` startup event). No separate process or cron required.

### Startup Backfill (USGS)

On every backend start, `backfill_24h()` queries the USGS Earthquake Hazards API for M3.0+ Japan events from the last 24 hours and writes any missing events to Neo4j. This covers the gap before the JMA polling loop catches up.

```
GET https://earthquake.usgs.gov/fdsnws/event/1/query
    ?format=geojson&minmagnitude=3.0&starttime=<24h ago>
    &minlatitude=24&maxlatitude=46&minlongitude=122&maxlongitude=148
```

Events are written with `source = 'usgs_live'` and use `MERGE` to avoid duplicates.

### Continuous Polling (JMA)

Every 60 seconds, the poller fetches the JMA high-frequency ATOM feed (`eqvol.xml`) and processes VXSE53/VXSE51 entries (震源・震度情報):

```
GET https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml
```

Each new entry triggers a fetch of the full JMA XML report. Fields extracted:

| JMA XML element | Neo4j property |
|---|---|
| `OriginTime` | `occurrenceDateTime` |
| `jmx_eb:Coordinate` | `epicentreLat`, `epicentreLon`, `hypocentralDepthKm` |
| `jmx_eb:Magnitude` | `momentMagnitude` |
| `MaxInt` | `jmaIntensity` |
| `Hypocenter/Area/Name` | `place` |

Events are written with `source = 'JMA_LIVE'`. The `/live/status` endpoint reports the last update time and count.

> **Implementation note:** JMA XML uses `elementBasis1/` as the namespace suffix (not `elementBasis/`). The parser uses local-name matching (`el.tag.split("}")[-1]`) to stay robust against JMA namespace changes.

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
WHERE abs(e.epicentreLat - $lat) < 3 AND abs(e.epicentreLon - $lon) < 3
  AND abs(e.momentMagnitude - $mag) < 1.5
OPTIONAL MATCH (e)-[:ORIGINATED_ON]->(fz:FaultZone)
OPTIONAL MATCH (e)-[:TRIGGERED]->(t:Tsunami)
RETURN e.id, e.momentMagnitude, e.year, e.place, fz.name, t.waveHeightAtShoreM
ORDER BY abs(e.momentMagnitude - $mag) + abs(e.epicentreLat - $lat) + abs(e.epicentreLon - $lon)
LIMIT 5
```

### Nearest Neighbour Tsunami Inference

For simulations with a tsunami warning, finds the most physically similar historical tsunami events using a weighted similarity score:

```cypher
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
RETURN t.waveHeightAtShoreM, t.tsunamiFatalities,
       t.buildingsWashedAway, e.momentMagnitude,
       round(magScore + depthScore + latScore, 3) AS similarity
ORDER BY similarity / log(t.numberOfRunups + 2)
LIMIT 5
```

Magnitude is weighted 2× — a M7 and M9 are fundamentally different events regardless of location.

Vector semantic search is also available over all 12 node embedding indexes using Voyage AI `voyage-3`.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite, D3 (map), react-markdown |
| Backend | FastAPI (Python 3.9) |
| Database | Neo4j Aura |
| Agent (chat) | Neo4j Aura Agent Builder (GPT-4o + text-embedding-3-large) |
| Agent (predict) | Claude Sonnet via Anthropic API |
| Embeddings | Voyage AI voyage-3 (1024-dim) |
| Live feed | JMA ATOM eqvol.xml + USGS FDSN API |
| Hosting | Cloudflare Pages (frontend) |

---

## Running Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in Neo4j + API keys
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

**Required environment variables:**

```
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
AURA_AGENT_URL=https://api.neo4j.io/v1beta5/agents/your-agent-id/chat
AURA_CLIENT_ID=your-client-id
AURA_CLIENT_SECRET=your-client-secret
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
CORS_ORIGINS=http://localhost:5173
```

**Large data files (not in git):**

```
data/enrichment/*.nc          # GEBCO NetCDF (~99MB) — download from download.gebco.net
data/historical/events.json   # NOAA tsunami events — download from ngdc.noaa.gov
```

---

*Author: Dean Foulds — deanfoulds.xyz*  
*Project: Shindo — Japanese Earthquake Impact Simulator*  
*Hackathon: Neo4j Aura Agent Hackathon 2025*
