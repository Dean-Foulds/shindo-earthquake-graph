from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .routes import router
from .analysis import router as analysis_router
from .live import router as live_router
import os

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

@app.on_event("startup")
async def startup():
    from .db import get_db
    get_db()

@app.get("/")
def root():
    return {"message": "Shindo API running", "version": "2.1.0"}