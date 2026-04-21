import time
import traceback
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from .db import get_db, Neo4jService

router = APIRouter(prefix="/analysis")

_predict_cache: dict = {"data": None, "expires_at": 0.0}
CACHE_TTL = 3600

_CYPHER = """
MATCH (fz:FaultZone)
OPTIONAL MATCH (eq:Earthquake)-[:ORIGINATED_ON]->(fz)
WITH fz, collect(eq) AS all_events
RETURN fz.id AS fault_id, fz.name AS fault_name, fz.type AS fault_type,
       fz.predicted_max_mag AS predicted_max_mag, fz.last_major_year AS last_major_year,
       size(all_events) AS total_events,
       [e IN all_events WHERE e.magnitude >= 6.0 | e.year] AS years_m6,
       [e IN all_events WHERE e.magnitude >= 7.0 | e.year] AS years_m7,
       [e IN all_events WHERE e.magnitude >= 8.0 | e.year] AS years_m8
ORDER BY fz.name
"""

CURRENT_YEAR = 2025


def _recurrence_stats(years: list) -> dict:
    years = [y for y in (years or []) if y is not None]
    if len(years) < 2:
        return {
            "event_count": len(years),
            "avg_recurrence_years": None,
            "last_event_year": max(years) if years else None,
            "years_since_last": (CURRENT_YEAR - max(years)) if years else None,
            "overdue_score": None,
            "sample_size_warning": True,
        }
    s = sorted(years)
    gaps = [s[i + 1] - s[i] for i in range(len(s) - 1)]
    avg = round(sum(gaps) / len(gaps), 1)
    last = s[-1]
    since = CURRENT_YEAR - last
    overdue = round(since / avg, 2) if avg else None
    return {
        "event_count": len(years),
        "avg_recurrence_years": avg,
        "last_event_year": last,
        "years_since_last": since,
        "overdue_score": overdue,
        "sample_size_warning": len(years) < 3,
    }


def _build_response(rows: list[dict]) -> dict:
    fault_zones = []
    ranked = []

    for row in rows:
        tiers = {
            "m6": _recurrence_stats(row.get("years_m6") or []),
            "m7": _recurrence_stats(row.get("years_m7") or []),
            "m8": _recurrence_stats(row.get("years_m8") or []),
        }

        total = row.get("total_events", 0) or 0
        all_years = (row.get("years_m6") or []) + (row.get("years_m7") or []) + (row.get("years_m8") or [])
        all_years = [y for y in all_years if y is not None]
        if all_years and total:
            span = CURRENT_YEAR - min(all_years)
            rate = round(total / span, 3) if span > 0 else None
        else:
            rate = None

        fz = {
            "fault_id": row["fault_id"],
            "fault_name": row["fault_name"],
            "fault_type": row["fault_type"],
            "predicted_max_mag": row.get("predicted_max_mag"),
            "last_major_year": row.get("last_major_year"),
            "total_events": total,
            "seismicity_rate_per_year": rate,
            "tiers": tiers,
        }
        fault_zones.append(fz)

        # Pick the highest overdue score across tiers for ranking
        best_tier, best_score = None, None
        for tier_key, tier_data in tiers.items():
            score = tier_data["overdue_score"]
            if score is not None and (best_score is None or score > best_score):
                best_tier, best_score = tier_key, score

        if best_tier and best_score is not None:
            mag_label = best_tier.upper().replace("M", "M") + "+"
            ranked.append({
                "fault_id": row["fault_id"],
                "fault_name": row["fault_name"],
                "tier": best_tier,
                "overdue_score": best_score,
                "display_label": f"{mag_label} overdue {best_score:.1f}×",
            })

    ranked.sort(key=lambda x: x["overdue_score"], reverse=True)

    all_years = [
        y
        for row in rows
        for tier_years in [row.get("years_m6") or [], row.get("years_m7") or [], row.get("years_m8") or []]
        for y in tier_years
        if y is not None
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "Statistical estimates derived from historical seismicity data. "
            "Not a scientific prediction. Earthquake occurrence is inherently stochastic. "
            "A ratio above 1.0 indicates a fault zone has exceeded its historical average "
            "recurrence interval — this does not imply imminent occurrence."
        ),
        "data_range": {
            "from_year": min(all_years) if all_years else 1950,
            "to_year": CURRENT_YEAR,
            "total_events": sum(row.get("total_events", 0) for row in rows),
        },
        "fault_zones": fault_zones,
        "ranked_by_overdue": ranked,
    }


def get_cached_predict():
    return _predict_cache.get("data")


@router.get("/predict")
def predict(db: Neo4jService = Depends(get_db)):
    now = time.time()
    if _predict_cache["data"] and now < _predict_cache["expires_at"]:
        return _predict_cache["data"]

    try:
        rows = db.cypher_read(_CYPHER)
        data = _build_response(rows)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")

    _predict_cache["data"] = data
    _predict_cache["expires_at"] = now + CACHE_TTL
    return data
