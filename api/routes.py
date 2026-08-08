"""
api/routes.py — POST /api/interview route
==========================================
Implements the single production endpoint specified in technical-spec.md.

Turn routing logic:
    - Start turn   : sessionId + candidate present → create session, call start_interview()
    - Continue turn: sessionId + message present   → load session, call handle_turn()
    - Invalid      : return HTTP 422 with helpful error message

The route delegates all interview logic to engine/orchestrator.py and all
state management to sessions/store.py; this file is intentionally thin.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, status

from api.schemas import InterviewRequest, InterviewResponse, FeedbackResponse
from models.candidate import build_candidate_context
from sessions.store import session_store
from engine.orchestrator import start_interview, handle_turn

router = APIRouter()
logger = logging.getLogger("interview_agent.api")


@router.post(
    "/interview",
    response_model=InterviewResponse,
    summary="Conduct a technical interview turn",
    description=(
        "Single endpoint for all interview turns. "
        "Send `candidate` to start a new session, or `message` to continue one."
    ),
)
async def interview_endpoint(payload: InterviewRequest) -> InterviewResponse:
    """
    POST /api/interview

    Turn Types
    ----------
    Start  : { sessionId, candidate: {...} }
    Continue: { sessionId, message: "..." }

    Raises HTTP 422 if neither candidate nor message is provided.
    Raises HTTP 404 if sessionId not found for a continue turn.
    Raises HTTP 409 if sessionId already exists for a start turn.
    """

    # ------------------------------------------------------------------
    # START TURN — candidate payload present
    # ------------------------------------------------------------------
    if payload.candidate is not None:
        # Reject duplicate session ids
        if session_store.get(payload.sessionId) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Session '{payload.sessionId}' already exists. "
                    "Use a new sessionId to start a fresh interview."
                ),
            )

        # Build the enriched candidate context
        from data.loader import CandidateLoader
        loader = CandidateLoader.instance()
        enriched_data = loader.get_enriched(payload.candidate.member.id) or {}

        candidate_context = build_candidate_context(
            candidate_raw=payload.candidate,
            enriched_data=enriched_data,
        )

        # Persist new session
        try:
            state = session_store.create(
                session_id=payload.sessionId,
                candidate_context=candidate_context,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(exc)
            ) from exc

        # Log start request
        logger.info(
            f"[API] START TURN REQUEST - Session: {payload.sessionId} | "
            f"Candidate: {state.candidate_context.member.name} ({state.candidate_context.member.id})"
        )

        # Delegate to the engine for the opening message
        reply = start_interview(state)

        # Persist mutated state
        session_store.update(state)

        probed_day = state.questions_asked[-1].curriculum_day if state.questions_asked else None
        logger.info(
            f"[API] START TURN RESPONSE - Session: {payload.sessionId} | "
            f"Initial Probing Day: {probed_day} | "
            f"Reply Preview: {reply[:60]}..."
        )

        return InterviewResponse(reply=reply, done=False)

    # ------------------------------------------------------------------
    # CONVERSATION TURN — message payload present
    # ------------------------------------------------------------------
    if payload.message is not None:
        if len(payload.message) > 2000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is too long. Maximum allowed length is 2000 characters."
            )
        try:
            state = session_store.get_or_raise(payload.sessionId)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc

        if state.phase.value == "done":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Session '{payload.sessionId}' is already completed. "
                    "Please start a new session."
                ),
            )

        # Log continue request
        turn_num = len(state.conversation_history)
        last_q = state.questions_asked[-1] if state.questions_asked else None
        last_probed_day = last_q.curriculum_day if last_q else None
        
        logger.info(
            f"[API] CONVERSATION REQUEST - Session: {payload.sessionId} | "
            f"Turn: {turn_num} | "
            f"Last Probing Day: {last_probed_day} | "
            f"Message: {payload.message[:60]}..."
        )

        # Delegate to the engine
        reply, is_done = handle_turn(state, payload.message)

        # Persist mutated state
        session_store.update(state)

        feedback_out: FeedbackResponse | None = None
        if is_done and state.feedback:
            f = state.feedback
            feedback_out = FeedbackResponse(
                summary=f.summary,
                strengths=f.strengths,
                gaps=f.gaps,
                next=f.next,
            )

        # Log continue response
        next_q = state.questions_asked[-1] if state.questions_asked else None
        next_probed_day = next_q.curriculum_day if next_q else None
        logger.info(
            f"[API] CONVERSATION RESPONSE - Session: {payload.sessionId} | "
            f"Done: {is_done} | "
            f"Next Probing Day: {next_probed_day} | "
            f"Reply Preview: {reply[:60]}..."
        )

        return InterviewResponse(reply=reply, done=is_done, feedback=feedback_out)

    # ------------------------------------------------------------------
    # INVALID — neither candidate nor message
    # ------------------------------------------------------------------
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
            "Request must include either 'candidate' (to start an interview) "
            "or 'message' (to continue one)."
        ),
    )
