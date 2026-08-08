"""
engine/engine_logger.py — Structured Engine Logging/Tracing
============================================================
Provides tracing functions for engine decisions, including topic picks,
LLM grader assessments, and question generation context.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Configure logging to stdout/stderr
logger = logging.getLogger("interview_engine")
logger.setLevel(logging.DEBUG)

# Add custom handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [ENGINE] %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def _log_structured(event_type: str, data: dict[str, Any]) -> None:
    """Helper to log event-driven data in a structured, grepable JSON-like format."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **data
    }
    # Print as clean formatted JSON so it can be easily inspected
    logger.info(json.dumps(payload, indent=2))


def log_strategy(brief: Any) -> None:
    """Logs the compiled strategy brief for a candidate."""
    _log_structured("strategy_brief_compiled", {
        "candidate_id": brief.candidate_id,
        "candidate_name": brief.candidate_name,
        "job_role": brief.job_role,
        "warm_up_day": brief.warm_up_topic.day,
        "ordered_topics": [t.day for t in brief.ordered_topics],
        "struggle_days": brief.struggles,
        "gap_days": brief.gaps
    })


def log_topic_pick(topic: Any, reason: str) -> None:
    """Logs selection of a curriculum topic."""
    _log_structured("topic_selected", {
        "day": topic.day,
        "title": topic.title,
        "signal": topic.signal,
        "reason": reason
    })


def log_decision(decision: Any, question: str, answer: str) -> None:
    """Logs the LLM grader's follow-up vs transition decision."""
    _log_structured("grader_decision", {
        "action": decision.action,
        "reasoning": decision.reasoning,
        "follow_up_hint": decision.follow_up_hint,
        "confidence": decision.confidence,
        "last_question": question[:60] + "..." if len(question) > 60 else question,
        "last_answer_preview": answer[:60] + "..." if len(answer) > 60 else answer
    })


def log_question_generated(output: Any) -> None:
    """Logs the generated question metadata."""
    _log_structured("question_generated", {
        "day": output.curriculum_day,
        "topic": output.topic_title,
        "signal_type": output.signal_type,
        "llm_rationale": output.llm_rationale,
        "question_text": output.question_text[:80] + "..." if len(output.question_text) > 80 else output.question_text
    })
