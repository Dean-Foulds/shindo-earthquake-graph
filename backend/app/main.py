import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .routes import router
from .analysis import router as analysis_router
from .live import router as live_router
from .auth import router as auth_router, init_db
from .simulate import router as simulate_router

load_dotenv()

app = FastAPI(title="Shindo API")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(analysis_router)
app.include_router(live_router)
app.include_router(auth_router)
app.include_router(simulate_router)

_poller_task: asyncio.Task = None


@app.on_event("startup")
async def startup():
    init_db()
    from .db import get_db
    from .poller import run_poller
    db = get_db()
    global _poller_task
    _poller_task = asyncio.create_task(run_poller(db))


@app.on_event("shutdown")
async def shutdown():
    if _poller_task:
        _poller_task.cancel()
        try:
            await _poller_task
        except asyncio.CancelledError:
            pass


@app.get("/")
def root():
    return {"message": "Shindo API running", "version": "2.1.0"}