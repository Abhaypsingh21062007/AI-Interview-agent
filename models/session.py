"""
models/session.py — Session State Pydantic Models
===================================================
Defines the data shapes for an in-memory interview session.

SessionState is the canonical state object stored in the session store.
It is designed to be the single source of truth for one interview run
and must contain everything the engine needs to continue a conversation.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from models.candidate import CandidateContext


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class InterviewPhase(str, Enum):
    """
    The current stage of the interview.

    Phases advance linearly:
        GREETING → QUESTIONING → CLOSING → DONE

    - GREETING   : Opening message sent, candidate not yet answering.
    - QUESTIONING: Active Q&A loop in progress.
    - CLOSING    : Minimum coverage met; winding down.
    - DONE       : Interview ended; feedback generated and returned.
    """
    GREETING = "greeting"
    QUESTIONING = "questioning"
    CLOSING = "closing"
    DONE = "done"


class TurnRole(str, Enum):
    """Participant role in a conversation turn."""
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class ConversationTurn(BaseModel):
    """A single message in the conversation history."""
    role: TurnRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QuestionRecord(BaseModel):
    """
    Tracks a question the agent has asked.

    `curriculum_day` links the question back to the cohort curriculum
    for coverage tracking; None means the question was meta/general.
    """
    question_text: str
    curriculum_day: Optional[int] = None
    module_title: Optional[str] = None
    asked_at_turn: int   # index into conversation history when asked


class FeedbackPayload(BaseModel):
    """
    Structured feedback returned in the final done=True response.
    Populated by the engine's feedback generator (Phase 3+).
    """
    summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    next: list[str] = Field(default_factory=list)     # "next steps" for the candidate


# ---------------------------------------------------------------------------
# Primary session state
# ---------------------------------------------------------------------------

class SessionState(BaseModel):
    """
    The canonical state object for one interview session.

    Keyed by `session_id` in the session store.  All fields are mutable
    across turns; the engine updates them after every exchange.

    Coverage rules
    --------------
    Minimum 8 questions asked AND at least 4 distinct curriculum days
    covered before the interview may close.

    `coverage_met` is a cached flag — the engine must update it
    whenever `questions_asked` changes.
    """

    # Identity
    session_id: str

    # The fully-joined candidate data (set once at session creation)
    candidate_context: CandidateContext

    # Conversation log — append-only ordered list
    conversation_history: list[ConversationTurn] = Field(default_factory=list)

    # Questions the agent has asked (for coverage tracking)
    questions_asked: list[QuestionRecord] = Field(default_factory=list)

    # Current phase of the interview
    phase: InterviewPhase = InterviewPhase.GREETING

    # Coverage flag: True when ≥ 8 questions AND ≥ 4 distinct days covered
    coverage_met: bool = False

    # Optional: feedback populated when phase reaches DONE
    feedback: Optional[FeedbackPayload] = None

    # Lifecycle timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # -----------------------------------------------------------------
    # Derived helpers (methods, not stored fields)
    # -----------------------------------------------------------------

    def distinct_days_covered(self) -> set[int]:
        """Return the set of curriculum day numbers that have been questioned."""
        return {
            q.curriculum_day
            for q in self.questions_asked
            if q.curriculum_day is not None
        }

    def check_coverage(self) -> bool:
        """
        Evaluate whether minimum coverage has been met.

        Updates and returns `coverage_met`:
            True  if ≥ 8 questions asked AND ≥ 4 distinct days covered.
            False otherwise.
        """
        n_questions = len(self.questions_asked)
        n_days = len(self.distinct_days_covered())
        self.coverage_met = n_questions >= 8 and n_days >= 4
        return self.coverage_met

    def add_turn(self, role: TurnRole, content: str) -> None:
        """Append a turn to the conversation history and bump last_updated."""
        self.conversation_history.append(
            ConversationTurn(role=role, content=content)
        )
        self.last_updated = datetime.now(timezone.utc)

    def add_question(
        self,
        question_text: str,
        curriculum_day: Optional[int] = None,
        module_title: Optional[str] = None,
    ) -> None:
        """
        Record a question the agent asked and refresh the coverage flag.

        Should be called by the engine every time it generates a new question
        so coverage is always up-to-date.
        """
        turn_index = len(self.conversation_history) - 1
        self.questions_asked.append(
            QuestionRecord(
                question_text=question_text,
                curriculum_day=curriculum_day,
                module_title=module_title,
                asked_at_turn=max(turn_index, 0),
            )
        )
        self.check_coverage()

    class Config:
        use_enum_values = False   # keep Enum instances, not string values
