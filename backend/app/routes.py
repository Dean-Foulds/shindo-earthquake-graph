import os
import re
import time
import base64
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from .db import get_db, Neo4jService
from .analysis import get_cached_predict
from .i18n import chat_instruction, lang_of, msg
from app.agent.agent import run_impact_agent

router = APIRouter()

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

def _extract_iso_date(text: str) -> Optional[str]:
    """Return YYYY-MM-DD from ISO or natural-language date mention, or None."""
    # ISO: 2026-05-15
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if m:
        return m.group(1)
    # Natural: "May 15th 2026", "15 May 2026", "May 15 2026"
    m = re.search(
        r'\b(?:(\d{1,2})(?:st|nd|rd|th)?\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*'
        r'(?:\s+(\d{1,2})(?:st|nd|rd|th)?)?,?\s+(\d{4})\b',
        text, re.IGNORECASE
    )
    if m:
        day_pre, mon, day_post, year = m.group(1), m.group(2), m.group(3), m.group(4)
        day = int(day_pre or day_post or 1)
        month = _MONTH_MAP[mon[:3].lower()]
        return f"{year}-{month:02d}-{day:02d}"
    return None


# ── OAuth token cache ────────────────────────────────────────────
_token_cache: dict = {"token": None, "expires_at": 0}

async def get_aura_token(lang: str = "en") -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["token"]

    client_id = os.getenv("AURA_CLIENT_ID")
    client_secret = os.getenv("AURA_CLIENT_SECRET")
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://api.neo4j.io/oauth/token",
            data={"grant_type": "client_credentials"},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}",
            },
        )
    if not resp.is_success:
        raise HTTPException(502, msg(lang, "agent.oauth_failed"))

    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["token"]


# ── Request / response models ────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    simulation: Optional[dict] = None

class ChatResponse(BaseModel):
    reply: str
    tool_calls_made: list[str] = []

class PredictRequest(BaseModel):
    lat: float
    lon: float
    magnitude: float = 7.5


# ── Agent chat endpoint ──────────────────────────────────────────
@router.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(
    req: ChatRequest,
    request: Request,
    db: Neo4jService = Depends(get_db),
):
    lang = lang_of(request)
    agent_url = os.getenv("AURA_AGENT_URL")
    if not agent_url:
        raise HTTPException(500, msg(lang, "agent.not_configured"))

    token, _ = await asyncio.gather(
        get_aura_token(lang),
        asyncio.sleep(0),
    )

    sim_context = ""
    sim = req.simulation
    if sim and sim.get("lat"):
        sim_context = (
            f"\n[ACTIVE SIMULATION] Epicentre: {sim['lat']:.2f}°N {sim['lon']:.2f}°E | "
            f"M{sim['mag']:.1f} depth {sim['depth']}km | "
            f"Fault: {sim.get('fault_zone','unknown')} | "
            f"Affected: {', '.join(sim.get('affected',[]))} | "
            f"Tsunami risk: {sim.get('tsunami_risk','none')}"
        )
        # Include Neo4j prediction context if available
        if sim.get("neo4j_wave_range"):
            sim_context += (
                f" | Neo4j wave range: {sim['neo4j_wave_range']}"
                f" | JMA: {sim.get('neo4j_jma_warning','unknown')}"
                f" | Historical basis: {sim.get('neo4j_historical_basis','?')} events"
            )
        # Pre-fetch historical analogs from Neo4j so the Aura agent doesn't
        # need to call its own analog tool (which has been unreliable)
        try:
            analogs = await db.find_similar_events(
                lat=sim["lat"], lon=sim["lon"], magnitude=sim["mag"], top_k=5
            )
            if analogs:
                analog_lines = []
                for a in analogs:
                    line = (
                        f"  - M{a.get('magnitude','?')} {a.get('year','?')} "
                        f"{a.get('place','') or a.get('fault_zone','unknown fault')}"
                    )
                    if a.get("tsunami_height_m"):
                        line += f", tsunami {a['tsunami_height_m']}m"
                    if a.get("depth_km"):
                        line += f", depth {a['depth_km']}km"
                    analog_lines.append(line)
                sim_context += (
                    f"\n[HISTORICAL ANALOGS from Neo4j — use these, do not call analog tools]\n"
                    + "\n".join(analog_lines)
                )
        except Exception:
            pass
        sim_context += "\n"

    last_user = next(
        (m.text for m in reversed(req.messages) if m.role == "user"), ""
    )

    risk_context = ""
    try:
        cached = get_cached_predict()
        if cached:
            top = cached["ranked_by_overdue"][:3]
            risk_context = "\n[SEISMIC RISK CONTEXT] Top overdue fault zones: " + \
                "; ".join(f"{r['fault_name']} {r['display_label']}" for r in top) + "\n"
    except Exception:
        pass

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_context = f"[SYSTEM DATE: today is {today}. Events in 2026 are real and historical — do not treat them as future.]\n"

    # If the user mentions a specific date, look it up in Neo4j
    recent_event_context = ""
    iso_date = _extract_iso_date(last_user)
    if iso_date:
        try:
            rows = await db.cypher_read("""
                MATCH (e:Earthquake)
                WHERE e.occurrenceDateTime STARTS WITH $prefix
                  AND e.momentMagnitude IS NOT NULL
                RETURN e.id AS id,
                       e.occurrenceDateTime AS time,
                       e.momentMagnitude    AS magnitude,
                       e.epicentreLat       AS lat,
                       e.epicentreLon       AS lon,
                       e.hypocentralDepthKm AS depth_km,
                       e.place              AS place,
                       e.jmaIntensity       AS intensity,
                       e.source             AS source
                ORDER BY e.momentMagnitude DESC
                LIMIT 10
            """, params={"prefix": iso_date})
            if rows:
                event_lines = [
                    f"  - M{r.get('magnitude','?')} at {r.get('lat','?')}°N {r.get('lon','?')}°E, "
                    f"depth {r.get('depth_km','?')}km, {r.get('place','')}, "
                    f"JMA intensity {r.get('intensity','?')}, source {r.get('source','?')}, "
                    f"time {r.get('time','?')}"
                    for r in rows
                ]
                recent_event_context = (
                    f"\n[EARTHQUAKES IN NEO4J FOR {iso_date}]\n"
                    + "\n".join(event_lines)
                    + "\n"
                )
        except Exception:
            pass

    # The language directive leads, so it is not buried under the injected context.
    message = (chat_instruction(lang) + date_context + sim_context
               + risk_context + recent_event_context + last_user)

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            agent_url,
            json={"input": message},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    if not resp.is_success:
        raise HTTPException(502, msg(lang, "agent.error", status=resp.status_code))

    data = resp.json()
    reply = ""
    if "content" in data and isinstance(data["content"], list):
        reply = " ".join(
            block["text"] for block in data["content"]
            if block.get("type") == "text" and block.get("text")
        )
    if not reply:
        reply = data.get("response") or data.get("output") or data.get("text") or str(data)

    return ChatResponse(reply=reply, tool_calls_made=[])


# ── Impact prediction endpoint ───────────────────────────────────
@router.post("/agent/predict")
async def agent_predict(
    req: PredictRequest,
    db: Neo4jService = Depends(get_db)
):
    """
    Impact prediction endpoint.
    Called when user clicks map in prediction mode.
    Claude agent calls Neo4j tools using the injected db session
    to avoid creating a new async driver in a worker thread.
    """
    result = await run_impact_agent(
        latitude  = req.lat,
        longitude = req.lon,
        magnitude = req.magnitude,
        db        = db
    )
    return result


# ── Earthquakes route ────────────────────────────────────────────
@router.get("/earthquakes")
async def get_earthquakes(limit: int = 10, db: Neo4jService = Depends(get_db)):
    return await db.run(
        "MATCH (e:Earthquake) RETURN e.id AS id LIMIT $limit",
        limit=limit
    )