"""
sessions/store.py — In-Memory Session Store
=============================================
A simple thread-safe dict-backed store keyed by sessionId (str/UUID).

Provides create / get / update / delete operations on SessionState objects.
Survives across HTTP requests for the lifetime of the process — exactly what
the spec requires (no persistent DB, no external cache).

In Phase 4+ this module can be swapped for a Redis backend without changing
any call-sites; the interface stays the same.
"""

from __future__ import annotations

import threading
from typing import Optional

from models.session import SessionState, InterviewPhase
from models.candidate import CandidateContext


# ---------------------------------------------------------------------------
# Session Store
# ---------------------------------------------------------------------------

class SessionStore:
    """
    Thread-safe, in-memory store of SessionState objects.

    All public methods acquire `_lock` so the store is safe to use with
    FastAPI's default threadpool workers.

    Attributes
    ----------
    _store : dict[str, SessionState]
        The underlying dictionary mapping session_id → SessionState.
    _lock : threading.Lock
        Reentrant lock for concurrent access.
    """

    def __init__(self) -> None:
        self._store: dict[str, SessionState] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        session_id: str,
        candidate_context: CandidateContext,
    ) -> SessionState:
        """
        Create and persist a new SessionState.

        Parameters
        ----------
        session_id : str
            Caller-supplied UUID string (from the API request payload).
        candidate_context : CandidateContext
            Fully-built candidate context (profile + curriculum joins).

        Returns
        -------
        SessionState
            The newly created (and stored) session.

        Raises
        ------
        ValueError
            If a session with `session_id` already exists.
        """
        with self._lock:
            if session_id in self._store:
                raise ValueError(
                    f"Session '{session_id}' already exists. "
                    "Use a fresh sessionId to start a new interview."
                )
            state = SessionState(
                session_id=session_id,
                candidate_context=candidate_context,
            )
            self._store[session_id] = state
            return state

    def get(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieve a session by id.

        Returns None if the session does not exist.
        """
        with self._lock:
            return self._store.get(session_id)

    def update(self, state: SessionState) -> SessionState:
        """
        Persist an updated SessionState object back into the store.

        The caller mutates the SessionState in-place (the object is
        shared by reference) then calls update() to make the mutation
        visible to future get() calls.

        Returns
        -------
        SessionState
            The same object that was passed in.

        Raises
        ------
        KeyError
            If the session does not exist (prevents phantom updates).
        """
        with self._lock:
            if state.session_id not in self._store:
                raise KeyError(
                    f"Cannot update non-existent session '{state.session_id}'."
                )
            self._store[state.session_id] = state
            return state

    def delete(self, session_id: str) -> bool:
        """
        Remove a session from the store.

        Returns True if the session existed and was removed, False otherwise.
        """
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Introspection helpers (useful for /health and tests)
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return the total number of active sessions."""
        with self._lock:
            return len(self._store)

    def list_session_ids(self) -> list[str]:
        """Return a snapshot list of all active session IDs."""
        with self._lock:
            return list(self._store.keys())

    def get_or_raise(self, session_id: str) -> SessionState:
        """
        Retrieve a session or raise a 404-appropriate exception.

        Raises
        ------
        KeyError
            If session does not exist — the API layer converts this
            to an HTTP 404.
        """
        state = self.get(session_id)
        if state is None:
            raise KeyError(f"Session '{session_id}' not found.")
        return state


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

# All routers and the engine import this single instance.
# It is constructed once at module import time.
session_store = SessionStore()
