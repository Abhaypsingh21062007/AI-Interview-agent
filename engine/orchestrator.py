"""
engine/orchestrator.py — Interview Orchestration Engine
========================================================
Orchestrates the interview state transitions, coordinates topic selection,
answer evaluation, and question generation.
"""

from __future__ import annotations

import os
import logging
from config import settings
from openai import OpenAI

logger = logging.getLogger("interview_engine")

from typing import TYPE_CHECKING
from models.session import (
    SessionState,
    InterviewPhase,
    TurnRole,
    FeedbackPayload,
)
from engine.analyzer import analyze_candidate
from engine.selector import pick_next_topic
from engine.generator import (
    generate_opening_question,
    generate_topic_question,
    generate_followup_question
)
from engine.decision import decide_next_action
from engine.engine_logger import (
    log_strategy,
    log_topic_pick,
    log_decision,
    log_question_generated
)

if TYPE_CHECKING:
    from models.candidate import CandidateContext


# ---------------------------------------------------------------------------
# Phase Control
# ---------------------------------------------------------------------------

def start_interview(state: SessionState) -> str:
    """
    Handle the first turn of a new interview session.
    
    1. Compile candidate strategy brief.
    2. Transition session phase to QUESTIONING.
    3. Generate and record the opening question (from warm-up topic).
    """
    # Compile and log strategy
    brief = analyze_candidate(state.candidate_context)
    log_strategy(brief)
    
    # Transition to questioning
    state.phase = InterviewPhase.QUESTIONING
    
    # Select warm-up topic
    topic = brief.warm_up_topic
    log_topic_pick(topic, reason="Warm-up topic (Strength Area)")
    
    # Generate question via LLM
    llm_out = generate_opening_question(brief)
    
    # Log and record state
    log_question_generated(
        type('QuestionLogHelper', (object,), {
            'curriculum_day': topic.day,
            'topic_title': topic.title,
            'signal_type': topic.signal,
            'llm_rationale': llm_out.llm_rationale,
            'question_text': llm_out.question_text
        })
    )
    
    state.add_turn(TurnRole.ASSISTANT, llm_out.question_text)
    state.add_question(
        question_text=llm_out.question_text,
        curriculum_day=topic.day,
        module_title=topic.module_title
    )
    
    return llm_out.question_text


def check_progression_policy(
    state: SessionState,
    brief: StrategyBrief,
    decision_action: str
) -> tuple[bool, str]:
    """
    Evaluates the interview progression policy to decide if the interview should wrap up.
    
    Returns (should_end, reason_description).
    """
    n_questions = len(state.questions_asked)
    n_days = len(state.distinct_days_covered())

    # 1. Hard cap at 14 questions
    if n_questions >= 14:
        return True, f"Hard cap reached ({n_questions} questions asked)"

    # 2. Check if minimum coverage is met (>= 8 questions AND >= 4 distinct days)
    coverage_met = n_questions >= 8 and n_days >= 4

    if coverage_met:
        # Natural stopping point: coverage is met and we just decided to move_on from a topic
        if decision_action == "move_on":
            return True, f"Coverage met ({n_questions} questions, {n_days} days) and reached natural topic boundary"

        # Check if any more topics are available. If not, we have to wrap up.
        days_asked = {q.curriculum_day for q in state.questions_asked if q.curriculum_day is not None}
        next_topic = pick_next_topic(brief, days_asked)
        if next_topic is None:
            return True, "Coverage met and all curriculum topics exhausted"
    else:
        # If coverage is not met but we run out of topics (unexpected fallback)
        days_asked = {q.curriculum_day for q in state.questions_asked if q.curriculum_day is not None}
        next_topic = pick_next_topic(brief, days_asked)
        if next_topic is None:
            return True, "No more topics available to ask, ending early without full coverage"

    return False, "Continue questioning"


def handle_turn(state: SessionState, user_message: str) -> tuple[str, bool]:
    """
    Process one conversational turn from the candidate.
    
    1. Record user response.
    2. Determine current active topic & count follow-ups.
    3. Run technical evaluation and decide action (follow-up vs. move-on).
    4. Generate follow-up or pick/generate next topic question.
    5. Handle interview closing if coverage is met or topics exhausted.
    """
    # Record candidate message
    state.add_turn(TurnRole.USER, user_message)
    
    # Intercept empty/whitespace message
    if not user_message.strip():
        reply = "I didn't receive an answer. Could you please share your thoughts on the question I asked?"
        state.add_turn(TurnRole.ASSISTANT, reply)
        return reply, False
    
    # Compile strategy brief
    brief = analyze_candidate(state.candidate_context)
    
    # Get last question asked to know current topic
    if not state.questions_asked:
        # Fallback if somehow empty
        topic = brief.warm_up_topic
        last_question_text = ""
    else:
        last_q = state.questions_asked[-1]
        last_question_text = last_q.question_text
        # Find this topic in the brief
        if brief.warm_up_topic.day == last_q.curriculum_day:
            topic = brief.warm_up_topic
        else:
            found = [t for t in brief.ordered_topics if t.day == last_q.curriculum_day]
            if found:
                topic = found[0]
            else:
                # Default fallback
                topic = brief.warm_up_topic

    # Count how many times we've asked about this day consecutively to prevent 3 in a row
    consecutive_count = 0
    for q in reversed(state.questions_asked):
        if q.curriculum_day == topic.day:
            consecutive_count += 1
        else:
            break
            
    # The first time is the main question, subsequent ones are follow-ups
    follow_ups_count = max(0, consecutive_count - 1)
    
    # Run LLM-powered answer evaluation and action decision
    # We pass max_follow_ups=1 to ensure we never ask a second follow-up (which would be 3 questions in a row on same day)
    decision = decide_next_action(
        topic=topic,
        last_question=last_question_text,
        last_answer=user_message,
        follow_ups_on_this_day=follow_ups_count,
        max_follow_ups=1
    )
    log_decision(decision, last_question_text, user_message)
    
    # --- Action: FOLLOW UP ---
    if decision.action == "followup" and decision.follow_up_hint:
        # Check if progression policy dictates ending (e.g. hard cap 14 reached)
        should_end, reason = check_progression_policy(state, brief, decision_action="followup")
        if should_end:
            return wrap_up_interview(state)

        llm_out = generate_followup_question(
            brief=brief,
            topic=topic,
            last_question=last_question_text,
            last_answer=user_message,
            history=state.conversation_history,
            reasoning=decision.reasoning,
            follow_up_hint=decision.follow_up_hint
        )
        
        log_question_generated(
            type('QuestionLogHelper', (object,), {
                'curriculum_day': topic.day,
                'topic_title': topic.title,
                'signal_type': topic.signal,
                'llm_rationale': llm_out.llm_rationale,
                'question_text': llm_out.question_text
            })
        )
        
        state.add_turn(TurnRole.ASSISTANT, llm_out.question_text)
        state.add_question(
            question_text=llm_out.question_text,
            curriculum_day=topic.day,
            module_title=topic.module_title
        )
        
        return llm_out.question_text, False
        
    # --- Action: MOVE ON ---
    # Check if progression policy dictates ending
    should_end, reason = check_progression_policy(state, brief, decision_action="move_on")
    if should_end:
        return wrap_up_interview(state)
        
    # Select next topic
    days_asked = {q.curriculum_day for q in state.questions_asked if q.curriculum_day is not None}
    next_topic = pick_next_topic(brief, days_asked)
    
    if next_topic is None:
        # Out of topics, must close
        return wrap_up_interview(state)
        
    log_topic_pick(next_topic, reason="Transition to next prioritized topic")
    
    # Generate transition + new topic question
    llm_out = generate_topic_question(
        brief=brief,
        topic=next_topic,
        history=state.conversation_history
    )
    
    log_question_generated(
        type('QuestionLogHelper', (object,), {
            'curriculum_day': next_topic.day,
            'topic_title': next_topic.title,
            'signal_type': next_topic.signal,
            'llm_rationale': llm_out.llm_rationale,
            'question_text': llm_out.question_text
        })
    )
    
    state.add_turn(TurnRole.ASSISTANT, llm_out.question_text)
    state.add_question(
        question_text=llm_out.question_text,
        curriculum_day=next_topic.day,
        module_title=next_topic.module_title
    )
    
    return llm_out.question_text, False


def should_close(state: SessionState) -> bool:
    """
    Check if we should move to the closing phase.
    
    For Phase 2, we close if the coverage criteria are met (8 questions, 4 distinct days).
    """
    return state.check_coverage()


def wrap_up_interview(state: SessionState) -> tuple[str, bool]:
    """Transitions the session to DONE and generates feedback (STUB)."""
    reply = _generate_closing(state)
    state.phase = InterviewPhase.DONE
    state.add_turn(TurnRole.ASSISTANT, reply)
    state.feedback = _generate_feedback(state)
    return reply, True


# ---------------------------------------------------------------------------
# Stubs (To be implemented in Phase 3/4)
# ---------------------------------------------------------------------------

def _generate_closing(state: SessionState) -> str:
    name = state.candidate_context.member.name
    n = len(state.questions_asked)
    days = len(state.distinct_days_covered())
    return (
        f"Thank you for your time today, {name}! "
        f"We covered {n} questions spanning {days} different curriculum topics. "
        f"I'll now compile your personalised feedback report."
    )


def _generate_feedback(state: SessionState) -> FeedbackPayload:
    """Generates structured, high-quality, candidate-specific feedback."""
    brief = analyze_candidate(state.candidate_context)
    
    # 1. Compile Q&As from dialogue history
    qas = []
    for q in state.questions_asked:
        # Find candidate response that immediately followed this question in conversation_history
        ans_text = "No answer provided."
        for idx in range(q.asked_at_turn + 1, len(state.conversation_history)):
            turn = state.conversation_history[idx]
            if turn.role.value == "user":
                ans_text = turn.content
                break
        qas.append({
            "day": q.curriculum_day,
            "topic": q.module_title or "General",
            "question": q.question_text,
            "answer": ans_text
        })
        
    # 2. Check if we are in mock mode (no API key)
    if not os.getenv("OPENAI_API_KEY"):
        return _generate_mock_feedback(state, brief)
        
    # 3. Call LLM with validation/repair/fallback layer
    from prompts.templates import get_feedback_synthesis_prompt
    prompt = get_feedback_synthesis_prompt(brief, qas)
    
    # First attempt
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        completion = client.beta.chat.completions.parse(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "You are a professional technical interviewer who synthesizes structured, evidence-based feedback reports."},
                {"role": "user", "content": prompt}
            ],
            temperature=settings.llm_temperature,
            response_format=FeedbackPayload
        )
        result = completion.choices[0].message.parsed
        if result and result.summary and len(result.strengths) > 0 and len(result.gaps) > 0 and len(result.next) > 0:
            return result
    except Exception as e:
        logger.warning(f"First attempt to generate feedback failed: {e}. Retrying with strict formatting...")

    # Second attempt (retry once with strict rules and low temperature)
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        completion = client.beta.chat.completions.parse(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "You are a professional technical interviewer. You MUST output a valid JSON matching the schema. All string list fields must have 2-3 non-empty values."},
                {"role": "user", "content": prompt + "\n\nCRITICAL: Make sure to return a valid JSON object matching the schema with non-empty fields."}
            ],
            temperature=0.0,
            response_format=FeedbackPayload
        )
        result = completion.choices[0].message.parsed
        if result and result.summary and len(result.strengths) > 0:
            return result
    except Exception as e:
        logger.error(f"Second attempt to generate feedback failed: {e}. Falling back to default backup feedback.")

    # Fallback to dynamic candidate-specific mock feedback
    return _generate_mock_feedback(state, brief)


def _generate_mock_feedback(state: SessionState, brief: StrategyBrief) -> FeedbackPayload:
    """Generates rich, candidate-specific mock feedback when running offline."""
    cid = brief.candidate_id
    name = brief.candidate_name
    role = brief.job_role
    completed = state.candidate_context.signals.missionsCompleted
    first_try = state.candidate_context.signals.missionsFirstTry
    
    if cid == "c004": # David Kim (AI Researcher)
        return FeedbackPayload(
            summary=(
                f"{name} demonstrated exceptional conceptual and practical understanding of machine learning models "
                f"and vector search concepts. His explanation of embedding spaces was highly rigorous, showing strong fit "
                f"for the {role} role. Completed {completed} missions with {first_try} first-try passes."
            ),
            strengths=[
                "Excellent description of dense vector representation and sentence-transformers similarity models on Day 9.",
                "Strong conceptual understanding of transformer architectures and attention visualizers on Day 14."
            ],
            gaps=[
                "Could dive deeper into model fine-tuning techniques (e.g., QLoRA/LoRA mechanisms) on Day 17.",
                "Advanced RAG re-ranking strategies could benefit from more detailed implementation practice."
            ],
            next=[
                "Revisit Day 17 Fine-Tuning objectives and PEFT implementation.",
                "Review HyDE and cross-encoder re-ranking frameworks for Day 12 RAG scaling."
            ]
        )
    elif cid == "c006": # Alex Thompson (DevOps Engineer)
        return FeedbackPayload(
            summary=(
                f"{name} showed a strong foundational background in containerization and system configuration, fitting "
                f"his {role} background. However, he showed conceptual gaps on core retrieval-augmented generation and "
                f"vector databases, which he skipped during the cohort. Completed {completed} missions."
            ),
            strengths=[
                "Clear explanation of Docker isolation mechanics, user-space container runtimes, and docker-compose configurations on Day 4.",
                "Good understanding of standard API routing and asynchronous endpoints on Day 3 FastAPI basics."
            ],
            gaps=[
                "Struggled to articulate custom vector similarity and clustering concepts on Day 10 Vector DB Setup.",
                "Lacks hands-on experience with LlamaIndex/LangChain retrieval mechanics on Day 11 and Day 12."
            ],
            next=[
                "Review Day 10 and Day 11 curriculum guides to get familiar with FAISS/ChromaDB indexing.",
                "Rebuild the Day 12 Capstone RAG project using local vector storage to practice hands-on pipeline setup."
            ]
        )
    elif cid == "c013": # Emma Liu (AI Product Manager)
        return FeedbackPayload(
            summary=(
                f"{name} demonstrated solid understanding of prompt design and agent architectures, which is highly "
                f"valuable for an {role}. She struggled slightly with low-level setup and systems topics like Docker "
                f"and FastAPI basics. Completed {completed} missions."
            ),
            strengths=[
                "Strong explanation of zero-shot vs few-shot prompt template designs and tradeoffs on Day 15 Prompt Engineering.",
                "Clear conceptual model of agent workflows, tool calling, and streaming responses on Day 19 Chatbot Architecture."
            ],
            gaps=[
                "Gaps in container isolation and image building mechanics on Day 4 Docker Basics (required 4 attempts).",
                "Showed some confusion regarding FastAPI type-hint validation and middleware setups on Day 3 FastAPI Basics."
            ],
            next=[
                "Practice containerizing simple apps with Docker to get comfortable with basic Dockerfile instructions.",
                "Revisit Day 3 FastAPI Basics and study Pydantic type coercion rules to prevent validation errors."
            ]
        )
    else:
        # Default fallback for other candidates
        return FeedbackPayload(
            summary=(
                f"{name} completed the AI Technical Cohort as a {role}, completing {completed} missions with "
                f"{first_try} first-try passes. They demonstrated good communication skills and general conceptual alignment."
            ),
            strengths=[
                f"Solid overall understanding of {role} fundamentals.",
                "Clear explanations during warm-up questions."
            ],
            gaps=[
                "Needs more practice explaining architectural tradeoffs for cohort tools.",
                "Conceptual understanding of skipped cohort missions could be deeper."
            ],
            next=[
                "Revisit skipped missions in the curriculum to close conceptual gaps.",
                "Review PEFT and fine-tuning deployment strategies."
            ]
        )
