"""
scripts/test_engine.py — Standalone Test Script for Phase 2 Engine
==================================================================
Loads three distinct candidates, builds contexts, analyzes strategy,
and runs a simulated 3-turn conversation loop to verify candidate-aware
personalization, topic selection, follow-up decisions, and question generation.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add root folder to python path so we can import packages correctly
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

import json
from models.candidate import CandidateRaw, build_candidate_context
from models.session import SessionState, TurnRole
from data.loader import CurriculumLoader, CandidateLoader
from engine.orchestrator import start_interview, handle_turn
from engine.analyzer import analyze_candidate


def run_test_for_candidate(candidate_id: str, candidate_data: dict, simulated_answers: list[str]) -> None:
    """Run a simulated interview loop for a candidate to demonstrate engine functionality."""
    print("=" * 80)
    print(f"TESTING CANDIDATE: {candidate_data['member']['name']} ({candidate_data['member']['jobRole']})")
    print("=" * 80)
    
    # 1. Parsing candidate
    cand_raw = CandidateRaw(**candidate_data)
    
    # 2. Loading curriculum metadata & building enriched context
    loader = CandidateLoader.instance()
    enriched_data = loader.get_enriched(candidate_id) or {}
    
    context = build_candidate_context(cand_raw, enriched_data)
    
    # 3. Strategy brief compilation and inspection
    brief = analyze_candidate(context)
    print(f"[Strategy Brief Summary for LLM]\n{brief.summary_for_llm}\n")
    print(f"Warm-up Topic (Strength): Day {brief.warm_up_topic.day} - {brief.warm_up_topic.title}")
    print(f"First 3 remaining prioritized topics:")
    for t in brief.ordered_topics[:3]:
        print(f"  - Day {t.day} ({t.signal.upper()}): {t.title} [Role Relevant: {t.is_role_relevant}]")
    print()
    
    # 4. Creating a fresh mock session
    session = SessionState(
        session_id=f"test-session-{candidate_id}",
        candidate_context=context
    )
    
    # 5. Starting the interview (Greeting + Warm-up Question)
    print("--- STARTING INTERVIEW (Turn 0: Greeting & Warm-up Question) ---")
    greeting = start_interview(session)
    print(f"Assistant: {greeting}\n")
    
    # 6. Simulated multi-turn dialogue
    # We will simulate 2 responses from the candidate.
    # Answer 1: Short / vague response -> should trigger a follow-up.
    # Answer 2: Detailed response -> should trigger moving on.
    
    for idx, answer in enumerate(simulated_answers):
        print(f"--- CANDIDATE RESPONSE (Turn {idx + 1}) ---")
        print(f"Candidate: {answer}")
        
        reply, is_done = handle_turn(session, answer)
        print(f"Assistant: {reply}")
        print(f"is_done={is_done} | Current Phase: {session.phase.value}")
        print(f"Questions asked: {len(session.questions_asked)} | Days covered: {len(session.distinct_days_covered())}\n")
        
        if is_done:
            break


def main() -> None:
    # Set mock mode warning if no API key
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("!" * 80)
        print("WARNING: OPENAI_API_KEY environment variable is not set.")
        print("The engine will run in mock/dry-run mode with local rule-based generators.")
        print("!" * 80)
        print()

    # Load candidates from data layer
    loader = CandidateLoader.instance()
    
    # Candidate 1: c004 David Kim (AI Researcher - near perfect profile)
    c004_data = loader.get_candidate("c004")
    answers_c004 = [
        "Embeddings are just vectors.",  # Short answer -> triggers follow-up
        "An embedding space maps tokens into dense, continuous high-dimensional vectors. In our cohort day 9, we used sentence-transformers to capture semantic similarity. The vectors are learned during training so that words with similar contexts are mapped closer to each other, allowing us to compute cosine similarity." # Long answer -> moves on
    ]
    
    # Candidate 2: c006 Alex Thompson (DevOps Engineer - multiple skipped RAG/AI days)
    c006_data = loader.get_candidate("c006")
    answers_c006 = [
        "I guess environment setup is just setting up python and virtual environments.", # Short answer -> triggers follow-up
        "Environment setup is critical for reproducibility. We configured virtual environments using venv and pyenv to handle conflicting Python versions across projects, and configured pip for package locking. This prevents dependency drift between local development and production environments." # Long answer -> moves on
    ]
    
    # Candidate 3: c013 Emma Liu (AI Product Manager - skipped fine-tuning, struggled FastAPI/Docker)
    c013_data = loader.get_candidate("c013")
    answers_c013 = [
        "Prompt engineering is writing instructions for ChatGPT.", # Short answer -> triggers follow-up
        "Prompt engineering is the systematic design of inputs to get predictable outputs from LLMs. In our day 15 exercises, we explored zero-shot and few-shot templates. Few-shot is crucial when you need structured formats or want the model to adhere to specific style guides, as it grounds the model's output in concrete examples." # Long answer -> moves on
    ]
    
    # Run simulation for all three candidates
    run_test_for_candidate("c004", c004_data, answers_c004)
    run_test_for_candidate("c006", c006_data, answers_c006)
    run_test_for_candidate("c013", c013_data, answers_c013)


if __name__ == "__main__":
    main()
