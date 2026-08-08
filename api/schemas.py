"""
api/schemas.py — Request & Response Pydantic Schemas for POST /api/interview
==============================================================================
These are the wire-format models that FastAPI validates on every request.
They are intentionally separate from the internal domain models (models/)
so the API contract can be versioned independently.
"""

from __future__ import annotations

from typing import Optional, Any
from pydantic import BaseModel, Field

from models.candidate import CandidateRaw


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class InterviewRequest(BaseModel):
    """
    Unified request body for POST /api/interview.

    Either `candidate` (start turn) or `message` (conversation turn) must
    be present.  The route handler distinguishes the turn type based on
    which fields are present.

    Start turn   : sessionId + candidate  (no message)
    Conversation : sessionId + message    (no candidate)
    """
    sessionId: str = Field(..., description="UUID identifying the interview session.")
    candidate: Optional[CandidateRaw] = Field(
        default=None,
        description="Full candidate profile. Required only on the start turn.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Candidate's reply. Required on every conversation turn.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class FeedbackResponse(BaseModel):
    """Structured feedback included in the final done=True response."""
    summary: str
    strengths: list[str]
    gaps: list[str]
    next: list[str]


class InterviewResponse(BaseModel):
    """
    Response body for POST /api/interview.

    - Ongoing turns  : {reply, done: false}
    - Final turn     : {reply, done: true, feedback: {...}}
    """
    reply: str
    done: bool
    feedback: Optional[FeedbackResponse] = None
