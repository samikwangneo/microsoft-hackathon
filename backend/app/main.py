"""FastAPI application entry point for the PatchPilot backend.

Run: `uvicorn app.main:app --reload` (from the backend/ directory).
"""

from __future__ import annotations

import asyncio
import sys

# On Windows, asyncio subprocesses (git/npm, used by the agents) require the
# Proactor event loop; the Selector loop raises NotImplementedError. Set this
# before uvicorn creates its loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from ._env import load_root_env  # noqa: E402

load_root_env()  # populate os.environ from the root .env before anything reads it

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from . import __version__  # noqa: E402
from .config import get_settings  # noqa: E402
from .routes import dashboard, intake, run  # noqa: E402

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
app.include_router(run.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
