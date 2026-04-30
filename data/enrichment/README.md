# Data Enrichment Pipeline
## Shindo Seismic Intelligence System

---

## Overview

This directory contains the enrichment scripts that added new fields to the Neo4j Aura knowledge graph beyond what was available in the original ISC-GEM earthquake catalogue.

---

## Scripts

### 1. `gebco_enrichment.py` — Sea Floor Depth

**Purpose:** Adds `seaFloorDepthM` to every Earthquake node using GEBCO 2026 bathymetry data.

**Why this matters:** Sea floor depth at the epicentre is critical for tsunami simulation. A shallow shelf quake and a deep trench quake of identical magnitude produce fundamentally different waves. Without this field, tsunami inference is unreliable.

**Data source:** GEBCO 2026 Grid — `gebco_2026_n50.0_s20.0_w120.0_e150.0.nc`  
Download from: https://download.gebco.net  
Bounding box: 20°N–50°N, 120°E–150°E (Japan region)

**Method:**
- Load NetCDF file into a `RegularGridInterpolator`
- Vectorise all 32,976 lat/lon lookups as a single numpy operation
- Write results back to Aura in batches of 1,000

**Performance:** ~30 seconds for 32,976 nodes (vs ~5 hours for individual API calls)

**Results:**

| Metric | Value |
|---|---|
| Nodes enriched | 32,976 |
| Deepest ocean | -9,781m |
| Highest land | +2,620m |
| Average depth | -2,206m |
| Offshore events | 29,334 (89%) |
| Onshore events | 3,642 (11%) |

**Setup:**
```bash
pip install netCDF4 numpy scipy neo4j python-dotenv
```

**Run:**
```bash
cd data/enrichment
python gebco_enrichment.py
```

**Environment variables required** (in `.env`):
```
NEO4J_URI=neo4j+s://your-aura-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

---

### 2. `noaa_tsunami_enrichment.py` — Tsunami Wave Data

**Purpose:** Enriches existing Tsunami nodes and creates new ones using NOAA's Global Historical Tsunami Database.

**Why this matters:** The original Tsunami nodes were sparse — only `id`, `earthquake_id`, `source_mag`, `year`, and `embedding`. The NOAA database provides real measured wave heights and damage data that the nearest neighbour inference engine needs to learn from.

**Data source:** NOAA NCEI Global Historical Tsunami Database  
Download from: https://www.ngdc.noaa.gov/hazel/view/hazards/tsunami/event-search  
Filter: Country = Japan, Year = 1952–2024  
Save as: `data/historical/events.json`

**Fields added:**

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

**Matching strategy:**
1. Find Earthquake node by year (exact) + lat/lon proximity (within 1 degree)
2. Closest geographic match wins
3. If matched node has existing Tsunami node → enrich it
4. If matched node has no Tsunami node → create and link via `[:TRIGGERED]`

**Results:**

| Outcome | Count |
|---|---|
| Enriched existing Tsunami nodes | 41 |
| Created new Tsunami nodes linked to existing Earthquakes | 88 |
| Created standalone new pairs | 3 |
| Skipped (missing source data) | 3 |
| **Total processed** | **135** |

**Setup:**
```bash
pip install neo4j python-dotenv
```

**Run:**
```bash
cd data/enrichment
python noaa_tsunami_enrichment.py
```

---

## Fault Type Inference

Fault type was inferred directly in Neo4j Cypher — no separate script needed.

**Logic:**

| Rule | Assigned Type |
|---|---|
| `hypocentralDepthKm > 150` | `subduction` (deep slab) |
| `epicentreLon > 141` AND `epicentreLat > 35` AND `depth < 100` | `subduction` (Pacific plate) |
| `epicentreLon < 136` AND `epicentreLat < 34` | `subduction` (Philippine plate) |
| `hypocentralDepthKm < 20` | `strike-slip` (shallow inland) |
| `depth 20–60km` AND inland Japan | `reverse` |
| Remaining mid-depth events | `subduction` (intermediate slab) |

**Results:**

| Fault Type | Count | Percentage |
|---|---|---|
| subduction | 26,781 | 81% |
| strike-slip | 3,489 | 11% |
| reverse | 2,706 | 8% |

80% subduction is geologically correct — Japan sits at the junction of four tectonic plates.

**Cypher used:**
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

---

## Schema Migration

The original ISC-GEM dataset used different property names. These were renamed to match the ontology using APOC batch operations.

**Migration Cypher:**
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

---

## Data Quality Notes

**Tōhoku 2011 wave height** — The NOAA `maxWaterHeight` for the 2011 event shows 0.06m, which is the offshore buoy reading rather than the 40m coastal runup. The nearest neighbour query filters `waveHeightAtShoreM > 0.1` to exclude likely offshore sensor readings.

**Fault type inference** — Rules are heuristic rather than derived from a fault catalogue. A future improvement would link each Earthquake node to a `FaultZone` node via `[:ORIGINATED_ON]` and derive fault type from there (this relationship already exists in the graph for some events).

**NOAA coverage** — Deaths and building damage are only filled for 7–16% of tsunami events, reflecting incomplete historical records particularly for pre-1980 events.

---

## Files Not in Git

The following large data files are excluded from the repository via `.gitignore`:

```
data/enrichment/*.nc          # GEBCO NetCDF (~99MB)
data/historical/*.json        # NOAA events JSON
data/enrichment/events.json   # NOAA events (alternate location)
```

Download instructions are in each script's docstring.

---

*Author: Dean Foulds — deanfoulds.xyz*  
*Project: Shindo — Japanese Earthquake Impact Simulator*
