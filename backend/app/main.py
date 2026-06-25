"""FastAPI application entry point for the PatchPilot backend.

Run: `uvicorn app.main:app --reload` (from the backend/ directory).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .routes import dashboard, intake

settings = get_settings()

app = FastAPI(
    title="PatchPilot Backend",
    version=__version__,
    description="Agentic supply-chain security assistant — vulnerability intake.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
