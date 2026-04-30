import os
import time
import base64
import asyncio
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .db import get_db, Neo4jService
from .analysis import get_cached_predict

from pydantic import BaseModel
from app.agent.agent import run_impact_agent

router = APIRouter()

# ── OAuth token cache ────────────────────────────────────────────
_token_cache: dict = {"token": None, "expires_at": 0}

async def get_aura_token() -> str:
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
        raise HTTPException(502, f"Aura OAuth failed: {resp.text}")

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


# ── Agent endpoint ───────────────────────────────────────────────
@router.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest):
    agent_url = os.getenv("AURA_AGENT_URL")
    if not agent_url:
        raise HTTPException(500, "AURA_AGENT_URL not set")

    # Fetch token and build context concurrently
    token, _ = await asyncio.gather(
        get_aura_token(),
        asyncio.sleep(0),  # yield to event loop
    )

    sim_context = ""
    sim = req.simulation
    if sim and sim.get("lat"):
        sim_context = (
            f"\n[ACTIVE SIMULATION] Epicentre: {sim['lat']:.2f}°N {sim['lon']:.2f}°E | "
            f"M{sim['mag']:.1f} depth {sim['depth']}km | "
            f"Fault: {sim.get('fault_zone','unknown')} | "
            f"Affected: {', '.join(sim.get('affected',[]))} | "
            f"Tsunami risk: {sim.get('tsunami_risk','none')}\n"
        )

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

    message = sim_context + risk_context + last_user

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
        raise HTTPException(502, f"Aura agent error {resp.status_code}: {resp.text}")

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


# ── Earthquakes route ────────────────────────────────────────────
@router.get("/earthquakes")
async def get_earthquakes(limit: int = 10, db: Neo4jService = Depends(get_db)):
    return await db.run(
        "MATCH (e:Earthquake) RETURN e.id AS id LIMIT $limit",
        limit=limit
    )

class PredictRequest(BaseModel):
    lat: float
    lon: float
    magnitude: float = 7.5  # default if not provided

@router.post("/agent/predict")
async def agent_predict(req: PredictRequest):
    result = await run_impact_agent(
        latitude  = req.lat,
        longitude = req.lon,
        magnitude = req.magnitude
    )
    return result