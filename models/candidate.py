"""
models/candidate.py — Candidate & context Pydantic models
==========================================================
Defines the data shapes mirroring candidates.json plus the
`CandidateContext` model that joins candidate data with
curriculum metadata — the primary input to the interview engine.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Raw candidate shapes (mirror candidates.json exactly)
# ---------------------------------------------------------------------------

class MemberProfile(BaseModel):
    """The `member` sub-object of a candidate record."""
    id: str
    name: str
    jobRole: str
    yearsExperience: int
    education: str
    status: str


class MissionRecord(BaseModel):
    """
    A single mission entry.  Either a completed attempt or a skip.

    - passed + attempts: normal result
    - skipped: True marks a day the candidate did not attempt
    """
    day: int
    title: str
    passed: Optional[bool] = None
    attempts: Optional[int] = None
    skipped: Optional[bool] = None


class CandidateSignals(BaseModel):
    """Aggregate engagement metrics for a candidate."""
    commitDays: int
    missionsCompleted: int
    missionsFirstTry: int


class CandidateRaw(BaseModel):
    """
    Full raw candidate record — matches the shape of candidates.json.
    This is what arrives in the POST /api/interview start payload.
    """
    member: MemberProfile
    missions: list[MissionRecord]
    signals: CandidateSignals


# ---------------------------------------------------------------------------
# Enriched / joined models
# ---------------------------------------------------------------------------

class CurriculumDayMeta(BaseModel):
    """
    Metadata about a single curriculum day, extracted from curriculum.json.
    Attached to each mission entry in the enriched context.
    """
    day: int
    title: str
    type: str                       # e.g. SETUP, BUILD, CONCEPT, CAPSTONE
    tools: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    module: Optional[dict[str, Any]] = None   # {n, title, days}


class EnrichedMission(BaseModel):
    """
    A mission record joined with its curriculum day metadata.
    Used inside CandidateContext for the engine to query.
    """
    day: int
    title: str
    passed: Optional[bool] = None
    attempts: Optional[int] = None
    skipped: Optional[bool] = None
    curriculum: Optional[CurriculumDayMeta] = None


class CandidateContext(BaseModel):
    """
    The primary input to the interview engine.

    Combines the candidate's raw profile with pre-computed derived
    fields and curriculum joins so the engine never needs to re-query
    the data layer mid-interview.

    Derived fields
    --------------
    enriched_missions   : all missions joined with curriculum metadata
    passed_with_struggle: missions passed after ≥ 3 attempts  (probe for understanding gaps)
    skipped_days        : missions where skipped=True           (known blind spots)
    first_try_passes    : missions passed on attempt 1          (demonstrated strengths)
    """

    # Core identity
    member: MemberProfile
    signals: CandidateSignals

    # Raw mission list (preserved for completeness)
    missions: list[MissionRecord] = Field(default_factory=list)

    # Joined / enriched fields (populated by build_candidate_context)
    enriched_missions: list[EnrichedMission] = Field(default_factory=list)
    passed_with_struggle: list[EnrichedMission] = Field(default_factory=list)
    skipped_days: list[EnrichedMission] = Field(default_factory=list)
    first_try_passes: list[EnrichedMission] = Field(default_factory=list)

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# Factory — builds a CandidateContext from a CandidateRaw + data layer
# ---------------------------------------------------------------------------

def build_candidate_context(
    candidate_raw: CandidateRaw,
    enriched_data: dict[str, Any],
) -> CandidateContext:
    """
    Construct a CandidateContext by merging raw candidate data with
    the pre-computed enriched dict produced by CandidateLoader.

    Parameters
    ----------
    candidate_raw : CandidateRaw
        The parsed payload received from the API start-turn request.
    enriched_data : dict
        The pre-computed enriched candidate dict from CandidateLoader
        (may be None if the candidate id is not in the preloaded data,
        in which case we fall back to runtime joining).

    Returns
    -------
    CandidateContext
        Ready-to-use context for the interview engine.
    """
    from data.loader import CurriculumLoader

    curriculum = CurriculumLoader.instance()

    def _enrich_mission(m: MissionRecord) -> EnrichedMission:
        day_meta_raw = curriculum.get_day(m.day)
        day_meta = CurriculumDayMeta(**day_meta_raw) if day_meta_raw else None
        return EnrichedMission(
            day=m.day,
            title=m.title,
            passed=m.passed,
            attempts=m.attempts,
            skipped=m.skipped,
            curriculum=day_meta,
        )

    present_days = {m.day for m in candidate_raw.missions}
    enriched_missions = [_enrich_mission(m) for m in candidate_raw.missions]

    # Fill in any missing curriculum days as skipped / conceptual gaps
    for day_num in range(1, 32):
        if day_num not in present_days:
            day_meta_raw = curriculum.get_day(day_num)
            day_meta = CurriculumDayMeta(**day_meta_raw) if day_meta_raw else None
            enriched_missions.append(
                EnrichedMission(
                    day=day_num,
                    title=day_meta.title if day_meta else f"Day {day_num}",
                    passed=False,
                    attempts=None,
                    skipped=True,
                    curriculum=day_meta,
                )
            )

    passed_with_struggle = [
        em for em in enriched_missions
        if em.passed and em.attempts is not None and em.attempts >= 3
    ]
    skipped_days = [em for em in enriched_missions if em.skipped]
    first_try_passes = [
        em for em in enriched_missions
        if em.passed and em.attempts == 1
    ]

    return CandidateContext(
        member=candidate_raw.member,
        signals=candidate_raw.signals,
        missions=candidate_raw.missions,
        enriched_missions=enriched_missions,
        passed_with_struggle=passed_with_struggle,
        skipped_days=skipped_days,
        first_try_passes=first_try_passes,
    )
