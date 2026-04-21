import os
import time
import base64
import requests
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .db import get_db, Neo4jService
from .analysis import get_cached_predict

router = APIRouter()

# ── OAuth token cache ────────────────────────────────────────────
_token_cache: dict = {"token": None, "expires_at": 0}

def get_aura_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["token"]

    client_id = os.getenv("AURA_CLIENT_ID")
    client_secret = os.getenv("AURA_CLIENT_SECRET")
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    resp = requests.post(
        "https://api.neo4j.io/oauth/token",
        data={"grant_type": "client_credentials"},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
        timeout=10,
    )
    if not resp.ok:
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
def agent_chat(req: ChatRequest):
    agent_url = os.getenv("AURA_AGENT_URL")
    if not agent_url:
        raise HTTPException(500, "AURA_AGENT_URL not set")

    token = get_aura_token()

    # Build context block if simulation is active
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

    # Send the latest user message (Aura agents are stateless per call)
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

    payload = {"input": message}

    resp = requests.post(
        agent_url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )

    if not resp.ok:
        raise HTTPException(502, f"Aura agent error {resp.status_code}: {resp.text}")

    data = resp.json()
    # Response: {"type":"message","role":"assistant","content":[{"type":"text","text":"..."},{"type":"thinking",...}]}
    reply = ""
    if "content" in data and isinstance(data["content"], list):
        reply = " ".join(
            block["text"] for block in data["content"]
            if block.get("type") == "text" and block.get("text")
        )
    if not reply:
        reply = data.get("response") or data.get("output") or data.get("text") or str(data)

    return ChatResponse(reply=reply, tool_calls_made=[])


# ── Original route ───────────────────────────────────────────────
@router.get("/earthquakes")
def get_earthquakes(limit: int = 10, db: Neo4jService = Depends(get_db)):
    return db.run(
        "MATCH (e:Earthquake) RETURN e.id AS id LIMIT $limit",
        limit=limit
    )
