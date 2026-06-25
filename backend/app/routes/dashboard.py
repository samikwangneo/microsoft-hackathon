"""Dashboard endpoint — serves the payload the Sentinel frontend renders."""

from __future__ import annotations

from fastapi import APIRouter

from ..dashboard import seed
from ..dashboard.models import DashboardPayload

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardPayload)
async def get_dashboard() -> DashboardPayload:
    """Return KPIs, the pull-request list (with per-PR detail + timeline), and
    the repo list used by the filters. Currently seeded mock data."""

    return seed.build_payload()
