"""Dashboard endpoint — serves the payload the Sentinel frontend renders."""

from __future__ import annotations

from fastapi import APIRouter

from ..dashboard import seed
from ..dashboard.models import DashboardPayload
from ..orchestrator import runner

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardPayload)
async def get_dashboard() -> DashboardPayload:
    """Return KPIs, the pull-request list (with per-PR detail + timeline), and
    the repo list used by the filters.

    Returns the most recently completed remediation run's real payload if one
    exists; otherwise falls back to seeded demo data."""

    return runner.latest_payload() or seed.build_payload()
