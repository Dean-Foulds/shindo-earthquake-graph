"""
Server-side seismic simulation.

The frontend used to call api.anthropic.com directly, which meant shipping the
API key inside the JavaScript bundle where any visitor could read it. The call
lives here instead: the key never leaves the server, and every request is
attributed to an account and counted against its quota.
"""

import json
import os
import sqlite3
from typing import Optional

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIStatusError,
    RateLimitError,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import check_quota, current_user, record_usage

router = APIRouter(prefix="/agent")

MODEL      = os.getenv("SHINDO_MODEL", "claude-sonnet-5")
MAX_TOKENS = 8192

PREF_IDS = (
    "hokkaido,aomori,iwate,miyagi,akita,yamagata,fukushima,ibaraki,tochigi,gunma,"
    "saitama,chiba,tokyo,kanagawa,niigata,toyama,ishikawa,fukui,yamanashi,nagano,"
    "gifu,shizuoka,aichi,mie,shiga,kyoto,osaka,hyogo,nara,wakayama,tottori,shimane,"
    "okayama,hiroshima,yamaguchi,tokushima,kagawa,ehime,kochi,fukuoka,saga,nagasaki,"
    "kumamoto,oita,miyazaki,kagoshima,okinawa"
)
NUCLEAR_IDS = (
    "fukushima_daiichi,fukushima_daini,onagawa,tokai_daini,kashiwazaki_kariwa,shika,"
    "mihama,ohi,takahama,hamaoka,shimane_npp,ikata,genkai,sendai_npp,tomari"
)

# Mirrors ANA_SCHEMA in frontend/src/shindo_live.jsx — keep the two in step.
ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "fault_zone", "fault_type", "severity", "estimated_casualties",
        "estimated_displaced", "affected_prefectures", "tsunami",
        "nuclear_risk", "historical_analogs", "cascade_chain", "insight",
    ],
    "properties": {
        "fault_zone": {"type": "string"},
        "fault_type": {"type": "string", "enum": ["subduction", "crustal", "intraslab"]},
        "severity": {
            "type": "string",
            "enum": ["minor", "moderate", "strong", "major", "catastrophic"],
        },
        "estimated_casualties": {"type": "number"},
        "estimated_displaced": {"type": ["number", "null"]},
        "affected_prefectures": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name", "intensity", "distance_km",
                             "shindo", "risk", "tsunami_height_m"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "intensity": {"type": "integer"},
                    "distance_km": {"type": "number"},
                    "shindo": {"type": "string"},
                    "risk": {"type": "string", "enum": ["shaking", "tsunami", "both"]},
                    "tsunami_height_m": {"type": ["number", "null"]},
                },
            },
        },
        "tsunami": {
            "type": "object",
            "additionalProperties": False,
            "required": ["risk", "max_height_m", "warning_min", "estimated_casualties"],
            "properties": {
                "risk": {
                    "type": "string",
                    "enum": ["none", "low", "moderate", "high", "extreme"],
                },
                "max_height_m": {"type": ["number", "null"]},
                "warning_min": {"type": ["number", "null"]},
                "estimated_casualties": {"type": ["number", "null"]},
            },
        },
        "nuclear_risk": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name", "distance_km", "risk"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "distance_km": {"type": "number"},
                    "risk": {
                        "type": "string",
                        "enum": ["none", "monitoring", "elevated", "critical"],
                    },
                },
            },
        },
        "historical_analogs": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "year", "magnitude", "deaths"],
                "properties": {
                    "name": {"type": "string"},
                    "year": {"type": "integer"},
                    "magnitude": {"type": "number"},
                    "deaths": {"type": "integer"},
                },
            },
        },
        "cascade_chain": {"type": "array", "items": {"type": "string"}},
        "insight": {"type": "string"},
    },
}

_client: Optional[Anthropic] = None


def _anthropic() -> Anthropic:
    global _client
    if _client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise HTTPException(503, "Simulation is unavailable — ANTHROPIC_API_KEY is not set")
        _client = Anthropic()
    return _client


class SimulationRequest(BaseModel):
    lat:       float = Field(ge=-90,  le=90)
    lon:       float = Field(ge=-180, le=180)
    magnitude: float = Field(ge=1,    le=10)
    depth:     float = Field(ge=0,    le=700)


@router.post("/analyze")
def analyze(body: SimulationRequest, user: sqlite3.Row = Depends(current_user)):
    check_quota(user)

    prompt = (
        f"Earthquake: {body.lat:.2f}°N {body.lon:.2f}°E "
        f"M{body.magnitude:.1f} depth {body.depth:.0f}km.\n"
        'intensity is shindo 1-10. shindo is the JMA scale "1"-"7".\n'
        f"Pref IDs: {PREF_IDS}\n"
        f"Nuclear IDs: {NUCLEAR_IDS}\n"
        "4-8 prefectures. Always include tsunami_height_m for coastal prefs if "
        "tsunami risk exists.\n"
        "ALWAYS give a top-level estimated_casualties (expected fatalities from ALL "
        "hazards combined — shaking, building collapse, landslide, fire, tsunami), "
        "never null. For shaking-dominant inland events this is driven by collapse "
        "and landslide, not tsunami. Also give historical_analogs[].deaths for every "
        "analog."
    )

    try:
        message = _anthropic().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system="You are Shindo, Japan seismic risk AI backed by a Neo4j graph.",
            messages=[{"role": "user", "content": prompt}],
            # Sent via extra_body so this works on older SDK releases that don't yet
            # type these fields. `thinking` matters because Sonnet 5 thinks by default
            # when it is omitted, and max_tokens caps thinking and output together —
            # which truncated this JSON object mid-write.
            extra_body={
                "thinking": {"type": "disabled"},
                "output_config": {
                    "format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}
                },
            },
        )
    except RateLimitError:
        raise HTTPException(503, "Model is rate limited — try again shortly")
    except APIConnectionError:
        raise HTTPException(503, "Could not reach the model API")
    except APIStatusError as e:
        raise HTTPException(502, f"Model API error ({e.status_code})")

    if message.stop_reason == "refusal":
        raise HTTPException(422, "The model declined to analyse this scenario")
    if message.stop_reason == "max_tokens":
        raise HTTPException(502, "Model response was truncated")

    record_usage(user["id"], message.usage.input_tokens, message.usage.output_tokens)

    text = "".join(b.text for b in message.content if b.type == "text")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(502, "Model returned unparseable output")
