"""
api/health.py — Health check & dev convenience routes
======================================================
These routes are NOT part of the production API contract.
They exist for local development, CI smoke tests, and quick
data inspection during development.

Routes:
    GET /health      → liveness check, returns loaded data counts
    GET /candidates  → list all loaded candidate summaries
    GET /sessions    → list active session ids (dev only)
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from data.loader import CurriculumLoader, CandidateLoader
from sessions.store import session_store

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    curriculum_days_loaded: int
    curriculum_modules_loaded: int
    candidates_loaded: int
    active_sessions: int
    version: str


class CandidateSummary(BaseModel):
    id: str
    name: str
    jobRole: str
    yearsExperience: int
    education: str
    status: str
    missionsCompleted: int
    missionsFirstTry: int
    commitDays: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    tags=["Health"],
)
async def health() -> HealthResponse:
    """
    Returns app health and counts of loaded data.
    Useful for verifying the data layer loaded correctly on startup.
    """
    curriculum = CurriculumLoader.instance()
    candidates = CandidateLoader.instance()

    return HealthResponse(
        status="ok",
        curriculum_days_loaded=len(curriculum.day_lookup),
        curriculum_modules_loaded=len(curriculum.module_lookup),
        candidates_loaded=len(candidates.candidate_lookup),
        active_sessions=session_store.count(),
        version="0.1.0",
    )


@router.get(
    "/candidates",
    response_model=list[CandidateSummary],
    summary="List all loaded candidates (dev only)",
    tags=["Dev"],
)
async def list_candidates() -> list[CandidateSummary]:
    """
    Returns a summary of all candidates loaded from candidates.json.
    Useful for picking a candidate id to use in a start-turn curl test.
    """
    loader = CandidateLoader.instance()
    results = []
    for cand in loader.all_candidates():
        m = cand["member"]
        s = cand["signals"]
        results.append(
            CandidateSummary(
                id=m["id"],
                name=m["name"],
                jobRole=m["jobRole"],
                yearsExperience=m["yearsExperience"],
                education=m["education"],
                status=m["status"],
                missionsCompleted=s["missionsCompleted"],
                missionsFirstTry=s["missionsFirstTry"],
                commitDays=s["commitDays"],
            )
        )
    return results


@router.get(
    "/sessions",
    summary="List active session IDs (dev only)",
    tags=["Dev"],
)
async def list_sessions() -> dict:
    """
    Returns all active session IDs and total count.
    Useful for debugging persistent session state during development.
    """
    return {
        "active_sessions": session_store.count(),
        "session_ids": session_store.list_session_ids(),
    }
