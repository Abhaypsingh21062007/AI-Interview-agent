"""
engine/analyzer.py — Candidate Signal Analyzer
===============================================
Parses a CandidateContext and compiles a StrategyBrief detailing
the candidate's strengths, struggle areas, gaps, and role relevance.
Exposes the strategy brief to the rest of the interview engine.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

from models.candidate import CandidateContext, EnrichedMission


# ---------------------------------------------------------------------------
# Static Job Role Topic Mapping
# ---------------------------------------------------------------------------

# Maps normalized job role names to set of curriculum days highly relevant to that role
ROLE_TOPIC_WEIGHTS: dict[str, set[int]] = {
    "ml engineer": {9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 23, 24, 25, 26, 27},
    "ai engineer": {9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 23, 24, 25, 26, 27},
    "nlp engineer": {7, 9, 11, 12, 14, 15, 16, 17},
    "data scientist": {5, 6, 7, 8, 9, 10, 11, 12, 14, 17, 27},
    "backend developer": {3, 4, 5, 6, 8, 19, 20, 21, 22, 29, 30},
    "software engineer": {3, 4, 5, 6, 8, 19, 20, 21, 22, 29, 30},
    "full stack developer": {3, 4, 5, 8, 19, 20, 21, 22, 29},
    "devops engineer": {4, 27, 28, 29, 30},
    "ml ops engineer": {4, 17, 18, 27, 28, 29, 30},
    "cloud architect": {4, 27, 28, 29, 30},
    "data engineer": {5, 6, 7, 8, 10, 22},
    "frontend developer": {20, 21, 22},
    "research engineer": {9, 14, 15, 16, 17, 18, 23, 24, 25, 26},
    "ai researcher": {9, 14, 15, 16, 17, 18, 23, 24, 25, 26},
    "product engineer": {3, 4, 19, 20, 21, 23, 24, 29},
    "ai product manager": {15, 18, 19, 21, 22, 23, 27, 28, 31},
    "systems engineer": {4, 6, 20, 24, 29, 30}
}


def get_role_relevant_days(role_name: str) -> set[int]:
    """Return the set of day numbers relevant to a job role (case-insensitive substring match)."""
    norm = role_name.strip().lower()
    # Direct match
    if norm in ROLE_TOPIC_WEIGHTS:
        return ROLE_TOPIC_WEIGHTS[norm]
    
    # Substring match
    for role, days in ROLE_TOPIC_WEIGHTS.items():
        if role in norm or norm in role:
            return days
            
    # Default set (core AI/FastAPI engineering foundational days)
    return {3, 9, 11, 15, 23, 29}


# ---------------------------------------------------------------------------
# Strategy Brief Models
# ---------------------------------------------------------------------------

class TopicEntry(BaseModel):
    """A curriculum topic analyzed for interview strategy."""
    day: int
    title: str
    module_title: str
    tools: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    signal: Literal["strength", "struggle", "gap", "neutral"]
    priority: int  # 1 = highest, 4 = lowest
    is_role_relevant: bool


class StrategyBrief(BaseModel):
    """
    Personalized interview plan for a candidate.
    """
    candidate_id: str
    candidate_name: str
    job_role: str
    years_experience: int
    education: str
    
    warm_up_topic: TopicEntry
    ordered_topics: list[TopicEntry] = Field(default_factory=list)
    
    # Summary list of categories for ease of reference/logging
    strengths: list[int] = Field(default_factory=list)
    struggles: list[int] = Field(default_factory=list)
    gaps: list[int] = Field(default_factory=list)
    role_relevant_days: list[int] = Field(default_factory=list)
    
    summary_for_llm: str


# ---------------------------------------------------------------------------
# Analyzer Function
# ---------------------------------------------------------------------------

def analyze_candidate(ctx: CandidateContext) -> StrategyBrief:
    """
    Analyze CandidateContext to produce a personalized StrategyBrief.
    
    Rules:
    - Categorize days based on signals:
      * gap: mission skipped (skipped=True)
      * struggle: attempts >= 3 (regardless of passed/failed)
      * strength: passed with attempts == 1
      * neutral: any other day in missions (passed with attempts == 2, or no details)
    - Determine role relevance.
    - Set priorities:
      * Priority 1: Gaps (skipped days) - we want to probe if they understand the concepts
      * Priority 2: Struggles (attempts >= 3) - high interest for debugging/problem-solving probe
      * Priority 3: Neutral days that are role-relevant
      * Priority 4: Everything else
    - Select a warm-up topic:
      * Pick a strength day (attempts == 1) that is also role-relevant.
      * Fall back to any strength day.
      * Fall back to a neutral role-relevant day.
      * Fall back to Day 1 (Environment Setup).
      * Remove the selected warm-up day from ordered_topics so it isn't repeated.
    """
    role = ctx.member.jobRole
    relevant_days = get_role_relevant_days(role)
    
    all_entries: dict[int, TopicEntry] = {}
    
    # Process all missions from context
    for m in ctx.enriched_missions:
        day_num = m.day
        day_meta = m.curriculum
        
        # Tools & objectives from joined curriculum meta
        tools = day_meta.tools if day_meta else []
        objectives = day_meta.objectives if day_meta else []
        mod_title = day_meta.module["title"] if (day_meta and day_meta.module) else "General"
        
        # Classification
        if m.skipped:
            sig = "gap"
            pri = 1
        elif m.attempts is not None and m.attempts >= 3:
            sig = "struggle"
            pri = 2
        elif m.passed and m.attempts == 1:
            sig = "strength"
            pri = 4  # Default, but could be warm-up
        else:
            sig = "neutral"
            pri = 3 if day_num in relevant_days else 4
            
        is_relevant = day_num in relevant_days
        
        all_entries[day_num] = TopicEntry(
            day=day_num,
            title=m.title,
            module_title=mod_title,
            tools=tools,
            objectives=objectives,
            signal=sig,
            priority=pri,
            is_role_relevant=is_relevant
        )

    # Compile lists of day numbers for the brief
    gaps = [day for day, entry in all_entries.items() if entry.signal == "gap"]
    struggles = [day for day, entry in all_entries.items() if entry.signal == "struggle"]
    strengths = [day for day, entry in all_entries.items() if entry.signal == "strength"]
    role_relevant = sorted(list(relevant_days))

    # Pick warm-up day
    warm_up_candidates = [entry for entry in all_entries.values() if entry.signal == "strength" and entry.is_role_relevant]
    if not warm_up_candidates:
        warm_up_candidates = [entry for entry in all_entries.values() if entry.signal == "strength"]
    if not warm_up_candidates:
        warm_up_candidates = [entry for entry in all_entries.values() if entry.is_role_relevant]
    
    if warm_up_candidates:
        # Sort by day number to be deterministic, pick the lowest day number
        warm_up_candidates.sort(key=lambda x: x.day)
        warm_up_entry = warm_up_candidates[0]
    else:
        # Fallback to Day 1
        warm_up_entry = all_entries.get(1) or TopicEntry(
            day=1,
            title="Environment Setup & Python Tooling",
            module_title="Environment & Tooling",
            tools=["pyenv", "venv", "pip"],
            objectives=["Set up a reproducible Python environment"],
            signal="neutral",
            priority=4,
            is_role_relevant=1 in relevant_days
        )

    # Compile remaining ordered topics, excluding the warm-up day
    ordered_topics = [
        entry for day, entry in all_entries.items()
        if day != warm_up_entry.day
    ]
    
    # Sort topics:
    # 1. By priority ascending (1 is highest, e.g. gaps first, then struggles)
    # 2. Within same priority, role-relevant first (True before False -> so is_role_relevant desc)
    # 3. By day number ascending
    ordered_topics.sort(key=lambda x: (x.priority, not x.is_role_relevant, x.day))

    # Build the prose summary for the LLM prompt
    summary_parts = [
        f"Candidate Profile: {ctx.member.name} ({role}, {ctx.member.yearsExperience} yrs exp, {ctx.member.education})",
        f"- Commit Days: {ctx.signals.commitDays}/31",
        f"- Missions Completed: {ctx.signals.missionsCompleted}",
        f"- First-try Passes: {ctx.signals.missionsFirstTry}",
        f"Gaps (skipped days, priority for testing conceptual reasoning): {', '.join(map(str, gaps)) if gaps else 'None'}",
        f"Struggles (attempts >= 3, probe for debugging/resolution skills): {', '.join(map(str, struggles)) if struggles else 'None'}",
        f"Role-Relevant Areas: {', '.join(map(str, role_relevant))}"
    ]
    
    summary_for_llm = "\n".join(summary_parts)

    return StrategyBrief(
        candidate_id=ctx.member.id,
        candidate_name=ctx.member.name,
        job_role=role,
        years_experience=ctx.member.yearsExperience,
        education=ctx.member.education,
        warm_up_topic=warm_up_entry,
        ordered_topics=ordered_topics,
        strengths=strengths,
        struggles=struggles,
        gaps=gaps,
        role_relevant_days=role_relevant,
        summary_for_llm=summary_for_llm
    )
