"""
engine/generator.py — LLM-Powered Question Generator
=====================================================
Interacts with the OpenAI API to generate candidate-aware, curriculum-grounded
opening questions, new topic questions, and probing follow-up questions.
Uses OpenAI structured outputs to guarantee schema alignment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from pydantic import BaseModel, Field
from openai import OpenAI

from config import settings
from prompts.persona import INTERVIEWER_PERSONA
from prompts.templates import (
    get_opening_prompt,
    get_topic_prompt,
    get_followup_question_prompt
)
from engine.engine_logger import log_question_generated

if TYPE_CHECKING:
    from engine.analyzer import StrategyBrief, TopicEntry
    from models.session import ConversationTurn


# ---------------------------------------------------------------------------
# Structured Output Schema
# ---------------------------------------------------------------------------

class QuestionOutput(BaseModel):
    """Pydantic model representing the structured JSON output from the LLM."""
    question_text: str = Field(
        ...,
        description="The natural-language question or reply to send to the candidate. Exactly one question."
    )
    llm_rationale: str = Field(
        ...,
        description="Internal explanation of why this question was framed this way, and how it maps to candidate details."
    )


# ---------------------------------------------------------------------------
# LLM Generation Functions
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# LLM Generation Functions
# ---------------------------------------------------------------------------

import os

def _is_mock_mode() -> bool:
    """Return True if we should run in local dry-run / mock mode."""
    return not os.getenv("OPENAI_API_KEY")


def _get_client() -> OpenAI:
    """Lazily construct and return the OpenAI client."""
    return OpenAI(api_key=settings.openai_api_key)


def generate_opening_question(brief: StrategyBrief) -> QuestionOutput:
    """
    Generate the greeting and first warm-up question.
    """
    if _is_mock_mode():
        t = brief.warm_up_topic
        tools_str = f" using {', '.join(t.tools)}" if t.tools else ""
        return QuestionOutput(
            question_text=(
                f"Welcome, {brief.candidate_name}! I'm the Interview Agent for the 31-Day AI Engineering Cohort. "
                f"I'll be conducting your technical interview today. I see you bring experience as a {brief.job_role}, "
                f"which is highly relevant. Let's start with a warm-up topic: {t.title} (Day {t.day}). "
                f"Could you explain your general approach to this, particularly{tools_str}?"
            ),
            llm_rationale=(
                f"[MOCK LLM] Warm-up generated for candidate {brief.candidate_name}. "
                f"Targeted strength area: Day {t.day} ({t.title})."
            )
        )

    client = _get_client()
    user_prompt = get_opening_prompt(brief)

    completion = client.beta.chat.completions.parse(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": INTERVIEWER_PERSONA},
            {"role": "user", "content": user_prompt}
        ],
        temperature=settings.llm_temperature,
        response_format=QuestionOutput
    )

    result = completion.choices[0].message.parsed
    if not result:
        raise RuntimeError("Failed to parse LLM response as QuestionOutput Pydantic model.")

    return result


def generate_topic_question(
    brief: StrategyBrief,
    topic: TopicEntry,
    history: list[ConversationTurn]
) -> QuestionOutput:
    """
    Generate the transition and first question for a new curriculum topic.
    """
    if _is_mock_mode():
        # Custom mock text based on signal
        if topic.signal == "gap":
            sig_prefix = "Since you skipped the hands-on mission for this, let's test your conceptual understanding of"
        elif topic.signal == "struggle":
            sig_prefix = "I noticed you spent several attempts resolving issues on this day. What was the main technical challenge you faced with"
        else:
            sig_prefix = "Let's dive into"

        tools_str = f" using {', '.join(topic.tools)}" if topic.tools else ""
        return QuestionOutput(
            question_text=(
                f"Let's move on. {sig_prefix} Day {topic.day}: {topic.title}. "
                f"How do you typically approach this topic{tools_str}, and what are the main tradeoffs involved?"
            ),
            llm_rationale=(
                f"[MOCK LLM] Topic transition question generated for Day {topic.day} ({topic.title}). "
                f"Signal classification: {topic.signal.upper()}."
            )
        )

    client = _get_client()
    
    # Format a concise history summary so the LLM doesn't repeat itself
    history_summary = ""
    if history:
        history_lines = []
        for turn in history[-6:]:  # past 6 turns are usually enough
            history_lines.append(f"{turn.role.value.upper()}: {turn.content}")
        history_summary = "\n".join(history_lines)
    else:
        history_summary = "No conversation history yet."

    user_prompt = get_topic_prompt(brief, topic, history_summary)

    completion = client.beta.chat.completions.parse(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": INTERVIEWER_PERSONA},
            {"role": "user", "content": user_prompt}
        ],
        temperature=settings.llm_temperature,
        response_format=QuestionOutput
    )

    result = completion.choices[0].message.parsed
    if not result:
        raise RuntimeError("Failed to parse LLM response as QuestionOutput Pydantic model.")

    return result


def generate_followup_question(
    brief: StrategyBrief,
    topic: TopicEntry,
    last_question: str,
    last_answer: str,
    history: list[ConversationTurn],
    reasoning: str,
    follow_up_hint: str
) -> QuestionOutput:
    """
    Generate a probing follow-up question on the current topic.
    """
    if _is_mock_mode():
        return QuestionOutput(
            question_text=(
                f"That makes sense, but I'd like to push a bit further. "
                f"Regarding your mention of '{last_answer[:40]}...', "
                f"how would you address {follow_up_hint} specifically?"
            ),
            llm_rationale=(
                f"[MOCK LLM] Follow-up question generated for Day {topic.day}. "
                f"Reasoning: {reasoning}. Probing: {follow_up_hint}."
            )
        )

    client = _get_client()
    
    # We construct a message log for the model to see the active thread
    messages = [
        {"role": "system", "content": INTERVIEWER_PERSONA}
    ]
    
    # Append recent context turns
    for turn in history[-4:]:
        messages.append({"role": turn.role.value, "content": turn.content})

    user_prompt = get_followup_question_prompt(
        brief=brief,
        topic=topic,
        last_question=last_question,
        last_answer=last_answer,
        reasoning=reasoning,
        follow_up_hint=follow_up_hint
    )
    messages.append({"role": "user", "content": user_prompt})

    completion = client.beta.chat.completions.parse(
        model=settings.llm_model,
        messages=messages,
        temperature=settings.llm_temperature,
        response_format=QuestionOutput
    )

    result = completion.choices[0].message.parsed
    if not result:
        raise RuntimeError("Failed to parse LLM response as QuestionOutput Pydantic model.")

    return result

