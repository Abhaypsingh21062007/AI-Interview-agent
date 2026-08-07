"""
engine/orchestrator.py — Interview Orchestration Engine
========================================================
Orchestrates the interview state transitions, coordinates topic selection,
answer evaluation, and question generation.
"""

from __future__ import annotations

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
    name = state.candidate_context.member.name
    completed = state.candidate_context.signals.missionsCompleted
    first_try = state.candidate_context.signals.missionsFirstTry

    return FeedbackPayload(
        summary=(
            f"{name} demonstrated solid foundational knowledge across multiple "
            f"AI engineering modules. Completed {completed} missions with "
            f"{first_try} first-try passes. This is a stub summary — "
            f"Phase 4 will replace this with an LLM-generated assessment."
        ),
        strengths=[
            "Strong understanding of embedding fundamentals",
            "Clear explanations of vector search concepts",
            "Good grasp of the RAG pipeline architecture",
        ],
        gaps=[
            "Fine-tuning depth (LoRA/QLoRA) needs further study",
            "Advanced RAG re-ranking strategies require more practice",
        ],
        next=[
            "Review Hugging Face PEFT docs on LoRA fine-tuning",
            "Study HyDE and re-ranking patterns for advanced RAG",
            "Practice deploying a FastAPI app to Cloud Run",
        ],
    )
