# Japanese Earthquake Ontology
## Shindo Seismic Intelligence System

---

## Overview

This ontology defines the formal schema for the Shindo Japanese earthquake impact simulator. It covers seismic events, tsunami chains, damage assessment, and emergency response — modelled in OWL/Turtle format and implemented as a Neo4j knowledge graph.

**Base URI:** `http://deanfoulds.xyz/ontology/earthquake#`  
**Format:** Turtle (TTL) — W3C standard RDF serialisation  
**Language:** OWL 2 with RDFS annotations  
**Bilingual:** All classes and properties labelled in English (`@en`) and Japanese (`@ja`)

---

## File

| File | Description |
|---|---|
| `japanese_earthquake.ttl` | Full OWL ontology in Turtle format |

---

## Classes (13)

### Seismic Event Classes

| Class | Japanese | Description |
|---|---|---|
| `Earthquake` | 地震 | Core seismic event |
| `TsunamiEvent` | 津波 | Tsunami triggered by an earthquake |
| `TsunamiWarning` | 津波警報 | JMA-issued warning (Advisory / Warning / Major Warning) |
| `WaveProfile` | 津波波形 | Physical wave characteristics at source and shore |
| `InundationZone` | 浸水域 | Area of land flooded by tsunami inland penetration |
| `TsunamiDamage` | 津波被害 | Damage caused by water (separate from shaking damage) |

### Geographic Classes

| Class | Japanese | Description |
|---|---|---|
| `Prefecture` | 都道府県 | Administrative division of Japan |
| `City` | 市区町村 | City, town or village |

### Damage Classes (all subclasses of DamageReport)

| Class | Japanese | Description |
|---|---|---|
| `DamageReport` | 被害報告 | Parent damage assessment class |
| `ShakingDamage` | 揺れによる被害 | Ground shaking damage — casualties and buildings |
| `FireAfterQuake` | 地震後火災 | Post-earthquake fires from gas lines, electrical faults |
| `LandslideRisk` | 土砂災害リスク | Landslide triggered by shaking in mountainous terrain |
| `NuclearIncident` | 原子力事故 | Nuclear facility impact or risk (INES scale) |

---

## Key Object Properties (Relationships)

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

---

## Key Data Properties (Fields)

### Earthquake Node

| Property | Type | Description | Source |
|---|---|---|---|
| `occurrenceDateTime` | xsd:dateTime | Event date and time (JST) | ISC-GEM / JMA |
| `epicentreLat` | xsd:decimal | Epicentre latitude | ISC-GEM / JMA |
| `epicentreLon` | xsd:decimal | Epicentre longitude | ISC-GEM / JMA |
| `hypocentralDepthKm` | xsd:decimal | Depth below surface (km) | ISC-GEM / JMA |
| `momentMagnitude` | xsd:decimal | Moment magnitude (Mw) | ISC-GEM / JMA |
| `jmaIntensity` | xsd:string | JMA seismic intensity (0–7) | JMA |
| `faultType` | xsd:string | subduction / strike-slip / reverse | Inferred |
| `seaFloorDepthM` | xsd:decimal | GEBCO sea floor depth at epicentre (m) | GEBCO 2026 |
| `significanceScore` | xsd:integer | USGS significance score | ISC-GEM |

### Tsunami Node

| Property | Type | Description | Source |
|---|---|---|---|
| `waveHeightAtShoreM` | xsd:decimal | Maximum observed wave height at shore (m) | NOAA NCEI |
| `tsunamiIntensity` | xsd:decimal | Iida-Imamura tsunami intensity | NOAA NCEI |
| `iidaMagnitude` | xsd:decimal | Iida tsunami magnitude | NOAA NCEI |
| `tsunamiFatalities` | xsd:integer | Deaths directly from tsunami | NOAA NCEI |
| `buildingsWashedAway` | xsd:integer | Buildings destroyed by water | NOAA NCEI |
| `numberOfRunups` | xsd:integer | Number of observation points | NOAA NCEI |
| `oceanicTsunami` | xsd:boolean | Whether wave crossed open ocean | NOAA NCEI |

---

## JMA Tsunami Warning Levels

| Level | Japanese | Magnitude Threshold | Expected Wave |
|---|---|---|---|
| Major Tsunami Warning | 大津波警報 | M ≥ 8.0 | > 3m |
| Tsunami Warning | 津波警報 | M ≥ 7.0 | 1–3m |
| Tsunami Advisory | 津波注意報 | M ≥ 6.0 | < 1m |

JMA issues warnings within 3 minutes of detection based on magnitude and epicentre location alone.

---

## Integration with Neo4j

This ontology was implemented as a Neo4j property graph. The TTL classes map to Neo4j node labels, object properties map to relationships, and data properties map to node properties.

### Migration from original schema

The original ISC-GEM dataset used different property names. These were migrated to match the ontology:

| Original | Ontology |
|---|---|
| `lat` | `epicentreLat` |
| `lon` | `epicentreLon` |
| `depth_km` | `hypocentralDepthKm` |
| `magnitude` | `momentMagnitude` |
| `time` | `occurrenceDateTime` |
| `sig` | `significanceScore` |

### Enrichment pipeline

Three enrichment scripts added fields not in the original dataset:

| Script | Field added | Data source |
|---|---|---|
| `data/enrichment/gebco_enrichment.py` | `seaFloorDepthM` | GEBCO 2026 NetCDF |
| `data/enrichment/noaa_tsunami_enrichment.py` | `waveHeightAtShoreM` + 7 more | NOAA NCEI Historical Tsunami DB |
| Cypher (inline) | `faultType` | Inferred from location + depth |

---

## Nearest Neighbour Inference

The ontology enables nearest neighbour tsunami inference — finding the most similar historical events for a simulated earthquake:

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

Magnitude is weighted 2× — because a M7 and M9 are fundamentally different events regardless of location.

---

## Database Statistics

| Metric | Value |
|---|---|
| Total earthquake nodes | 32,976 |
| Date range | 1950–2024 |
| Tsunami nodes | ~180 |
| Offshore events | 29,334 (89%) |
| Onshore events | 3,642 (11%) |
| Deepest ocean event | -9,781m |
| Fault type distribution | 81% subduction, 11% strike-slip, 8% reverse |

---

## Perseus Knowledge Graph Enrichment

The ontology was used to build a knowledge graph via [Lettria Perseus](https://docs.perseus.lettria.net), enriching the database with detailed damage chain data extracted from natural language event reports.

### Source document

`data/japanese_earthquake_events.txt` — prose reports covering six major historical earthquakes:

| Event | Date | Magnitude |
|---|---|---|
| Tōhoku Earthquake and Tsunami | 11 March 2011 | M9.1 |
| Great Hanshin Earthquake (Kobe) | 17 January 1995 | M6.9 |
| Noto Peninsula Earthquake | 1 January 2024 | M7.6 |
| Fukushima Aftershock | 11 April 2011 | M7.1 |
| Kumamoto Earthquakes | 14–16 April 2016 | M6.2 / M7.0 |
| Tokachi-Oki Earthquake | 26 September 2003 | M8.3 |

### Extraction pipeline

1. TTL ontology uploaded to Perseus console as the extraction schema
2. Source text file uploaded to Perseus Files
3. Graph built — Perseus extracted entities and relationships from prose
4. Graph exported as CQL and migrated to Neo4j Aura
5. 15 duplicate Prefecture nodes merged using `apoc.refactor.mergeNodes`
6. All new node types embedded with Voyage AI `voyage-3` via `04_embed_graph.py`

### Nodes added to Neo4j

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

### Prefecture enrichment

Perseus also added `prefectureCode` (JIS 2-digit codes) to 15 existing Prefecture nodes, enabling standard administrative lookup by code.

### Updated database statistics

| Metric | Value |
|---|---|
| Total earthquake nodes | 33,875 |
| Prefecture nodes | 47 (with JIS codes on 15) |
| City nodes | 33 (new — sub-prefecture granularity) |
| Damage chain node types | 10 |
| Vector indexes | 12 (5 original + 7 new) |

---

## Author

Dean Foulds — deanfoulds.xyz  
Project: Shindo — Japanese Earthquake Impact Simulator  
Hackathon: Neo4j Aura Agent Hackathon 2025
