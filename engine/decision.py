"""
engine/decision.py — LLM Answer Evaluation and Turn Decision Engine
=====================================================================
Analyzes the candidate's last answer and decides whether to continue
probing the current curriculum topic or transition to a new one.
Uses OpenAI structured outputs to guarantee JSON formatting.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field
from openai import OpenAI

from config import settings
from prompts.templates import get_followup_decision_prompt
from engine.engine_logger import log_decision

# ---------------------------------------------------------------------------
# Turn Decision Output Schema
# ---------------------------------------------------------------------------

class TurnDecision(BaseModel):
    """Structured evaluation of a candidate's turn."""
    action: Literal["followup", "move_on"] = Field(
        ...,
        description="Whether to ask a follow-up probing question ('followup') or transition to a new topic ('move_on')."
    )
    reasoning: str = Field(
        ...,
        description="Detailed assessment of answer accuracy, depth, relevance, and any gaps detected."
    )
    follow_up_hint: Optional[str] = Field(
        None,
        description="A prompt/guideline for what to probe next if action is 'followup'. Must be null if 'move_on'."
    )
    confidence: float = Field(
        ...,
        description="Confidence score in the evaluation between 0.0 and 1.0."
    )


# ---------------------------------------------------------------------------
# Decision Logic
# ---------------------------------------------------------------------------

import os

def decide_next_action(
    topic: Any,
    last_question: str,
    last_answer: str,
    follow_ups_on_this_day: int,
    max_follow_ups: int = 2
) -> TurnDecision:
    """
    Evaluate candidate's response to decide whether to probe deeper or move to next topic.
    
    If follow_ups_on_this_day >= max_follow_ups, we force a transition to "move_on" without
    making an LLM call to save time/cost.
    """
    if follow_ups_on_this_day >= max_follow_ups:
        # Avoid unnecessary LLM calls when we are at the turn limit
        return TurnDecision(
            action="move_on",
            reasoning=f"Reached maximum follow-ups ({max_follow_ups}) on curriculum Day {topic.day}.",
            follow_up_hint=None,
            confidence=1.0
        )
        
    if not os.getenv("OPENAI_API_KEY"):
        # MOCK DECISION LOGIC:
        # If the answer is short (< 15 words) or contains specific mock trigger keywords,
        # request a follow-up probe. Otherwise move on.
        words_count = len(last_answer.split())
        needs_probe = words_count < 15 or "brief" in last_answer.lower() or "guess" in last_answer.lower()
        
        if needs_probe:
            return TurnDecision(
                action="followup",
                reasoning=f"[MOCK Grader] Candidate answer is relatively short ({words_count} words). Probing for deeper implementation details.",
                follow_up_hint="specific tradeoffs and low-level mechanics of cohort tools",
                confidence=0.9
            )
        else:
            return TurnDecision(
                action="move_on",
                reasoning=f"[MOCK Grader] Candidate provided a detailed response ({words_count} words). Move on to next topic.",
                follow_up_hint=None,
                confidence=0.95
            )

    client = OpenAI(api_key=settings.openai_api_key)
    user_prompt = get_followup_decision_prompt(
        topic=topic,
        last_question=last_question,
        last_answer=last_answer,
        follow_ups_count=follow_ups_on_this_day,
        max_follow_ups=max_follow_ups
    )

    completion = client.beta.chat.completions.parse(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": "You are a senior technical interviewer evaluation engine. Evaluate technical accuracy and completeness."},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0,  # Deterministic grading
        response_format=TurnDecision
    )

    result = completion.choices[0].message.parsed
    if not result:
        raise RuntimeError("Failed to parse LLM response as TurnDecision Pydantic model.")

    # Guard: if action is move_on, follow_up_hint must be None
    if result.action == "move_on":
        result.follow_up_hint = None
        
    return result

