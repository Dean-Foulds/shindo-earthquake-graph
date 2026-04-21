from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .routes import router
from .analysis import router as analysis_router

load_dotenv()

app = FastAPI(title="Shindo API")

import os

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(analysis_router)

@app.get("/")
def root():
    return {"message": "Shindo API running"}
