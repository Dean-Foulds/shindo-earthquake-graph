// ================================================================
// SHINDO — Sample Cypher queries
// Paste these into Neo4j Aura Console → Query tab
// ================================================================


// ── 1. THE CASCADE TRACE ────────────────────────────────────────
// Trace the full 2011 Tohoku disaster through the graph
// Fault zone → earthquake → tsunami → prefecture → nuclear facility
MATCH path =
    (fz:FaultZone)<-[:ORIGINATED_ON]-(eq:Earthquake)
    -[:TRIGGERED]->(t:Tsunami)
    -[:INUNDATED]->(pf:Prefecture)
    <-[:LOCATED_IN]-(nf:NuclearFacility)
WHERE eq.magnitude >= 8.5
RETURN fz.name        AS fault_zone,
       eq.magnitude   AS magnitude,
       eq.time        AS time,
       t.max_height_m AS tsunami_height_m,
       pf.name        AS prefecture,
       nf.name        AS nuclear_facility,
       nf.status      AS facility_status
ORDER BY eq.magnitude DESC;


// ── 2. COMPOUNDED RISK CORRIDORS ────────────────────────────────
// Prefectures that sit on a subduction fault AND have a nuclear
// facility AND face the Pacific (tsunami exposure)
MATCH (fz:FaultZone)-[:UNDERLIES]->(pf:Prefecture)
      <-[:CONTAINS]-(nf:NuclearFacility)
WHERE fz.type = 'subduction'
  AND pf.coast IN ['pacific', 'both']
RETURN pf.name        AS prefecture,
       pf.region      AS region,
       fz.name        AS fault_zone,
       nf.name        AS nuclear_facility,
       nf.status      AS npp_status,
       fz.predicted_max_mag AS predicted_max_mag
ORDER BY fz.predicted_max_mag DESC;


// ── 3. HISTORICAL ANALOG FINDER ─────────────────────────────────
// Find past earthquakes similar to a predicted Nankai Trough event
// (subduction, depth 10-40km, magnitude 8.0+)
MATCH (eq:Earthquake)-[:ORIGINATED_ON]->(fz:FaultZone)
WHERE fz.type = 'subduction'
  AND eq.magnitude >= 7.5
  AND eq.depth_km BETWEEN 10 AND 60
WITH eq, fz
MATCH (eq)-[:STRUCK]->(pf:Prefecture)
OPTIONAL MATCH (eq)-[:TRIGGERED]->(t:Tsunami)
RETURN eq.time             AS time,
       eq.magnitude        AS magnitude,
       eq.depth_km         AS depth_km,
       fz.name             AS fault_zone,
       pf.name             AS nearest_prefecture,
       eq.deaths           AS deaths,
       t.max_height_m      AS tsunami_height_m
ORDER BY eq.magnitude DESC
LIMIT 20;


// ── 4. NUCLEAR PROXIMITY RISK ───────────────────────────────────
// Every M6.5+ earthquake that struck within 50km of a nuclear plant
MATCH (eq:Earthquake)-[:WITHIN_50KM_OF]->(nf:NuclearFacility)
WHERE eq.magnitude >= 6.5
MATCH (eq)-[:ORIGINATED_ON]->(fz:FaultZone)
RETURN eq.time          AS time,
       eq.magnitude     AS magnitude,
       eq.depth_km      AS depth_km,
       nf.name          AS nuclear_facility,
       nf.status        AS status,
       fz.name          AS fault_zone
ORDER BY eq.magnitude DESC;


// ── 5. DECADE PATTERN ANALYSIS ──────────────────────────────────
// Which decades had the most seismic activity and tsunami events?
MATCH (eq:Earthquake)-[:IN_DECADE]->(d:Decade)
OPTIONAL MATCH (eq)-[:TRIGGERED]->(t:Tsunami)
RETURN d.label                      AS decade,
       count(eq)                    AS total_quakes,
       round(avg(eq.magnitude), 2)  AS avg_magnitude,
       max(eq.magnitude)            AS max_magnitude,
       count(t)                     AS tsunamis,
       sum(CASE WHEN eq.deaths IS NOT NULL THEN eq.deaths ELSE 0 END) AS known_deaths
ORDER BY d.year;


// ── 6. FAULT ZONE LETHALITY ─────────────────────────────────────
// Rank fault zones by total documented deaths
MATCH (eq:Earthquake)-[:ORIGINATED_ON]->(fz:FaultZone)
WHERE eq.deaths IS NOT NULL
RETURN fz.name                   AS fault_zone,
       fz.type                   AS fault_type,
       count(eq)                 AS major_events,
       sum(eq.deaths)            AS total_deaths,
       max(eq.magnitude)         AS max_magnitude,
       fz.predicted_max_mag      AS predicted_future_max
ORDER BY total_deaths DESC;


// ── 7. THE HAMAOKA QUESTION ─────────────────────────────────────
// How many historical quakes struck within 50km of Hamaoka
// (the plant directly above the Nankai Trough)?
MATCH (eq:Earthquake)-[:WITHIN_50KM_OF]->(nf:NuclearFacility {id: 'hamaoka'})
MATCH (eq)-[:ORIGINATED_ON]->(fz:FaultZone)
RETURN eq.time        AS time,
       eq.magnitude   AS magnitude,
       eq.depth_km    AS depth_km,
       fz.name        AS fault_zone,
       eq.tsunami     AS tsunami_flagged
ORDER BY eq.magnitude DESC;


// ── 8. REGION VULNERABILITY SCORE ───────────────────────────────
// Score each prefecture by: quake count + tsunami count + NPP count
// on subduction faults — a simple composite risk index
MATCH (eq:Earthquake)-[:STRUCK]->(pf:Prefecture)
WITH pf, count(eq) AS quake_count, max(eq.magnitude) AS max_mag
OPTIONAL MATCH (t:Tsunami)-[:INUNDATED]->(pf)
WITH pf, quake_count, max_mag, count(t) AS tsunami_count
OPTIONAL MATCH (pf)-[:CONTAINS]->(nf:NuclearFacility)
WITH pf, quake_count, max_mag, tsunami_count, count(nf) AS npp_count
OPTIONAL MATCH (fz:FaultZone {type:'subduction'})-[:UNDERLIES]->(pf)
WITH pf, quake_count, max_mag, tsunami_count, npp_count, count(fz) AS subduction_zones
RETURN pf.name          AS prefecture,
       pf.region        AS region,
       quake_count,
       max_mag,
       tsunami_count,
       npp_count,
       subduction_zones,
       (quake_count * 1 + tsunami_count * 10 + npp_count * 5 + subduction_zones * 8)
           AS composite_risk_score
ORDER BY composite_risk_score DESC
LIMIT 15;


// ── 9. GRAPH SUMMARY (run this first to check your load) ────────
MATCH (n)
RETURN labels(n)[0] AS node_type, count(n) AS count
UNION
MATCH ()-[r]->()
RETURN type(r) AS node_type, count(r) AS count
ORDER BY count DESC;
