"""
data/loader.py — Data Access Layer
====================================
Loads curriculum.json and candidates.json, then exposes
singleton accessor objects used by the rest of the application.

Curriculum lookup:
    day_number (int) → DayMeta (topic, module, objectives, tools, type)

Candidate lookups:
    candidate_id (str) → CandidateRaw (full profile)
    candidate_id → derived helpers:
        - passed_with_struggle   : missions where passed=True AND attempts >= 3
        - skipped_days           : missions where skipped=True
        - first_try_passes       : missions where passed=True AND attempts == 1
        - enriched_missions      : each mission joined with its curriculum day metadata
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths — resolve relative to this file so the app can be run from any cwd
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent
CURRICULUM_PATH = _DATA_DIR / "curriculum.json"
CANDIDATES_PATH = _DATA_DIR / "candidates.json"


# ---------------------------------------------------------------------------
# Curriculum Loader
# ---------------------------------------------------------------------------

class CurriculumLoader:
    """
    Singleton that parses curriculum.json and builds fast lookup structures.

    Attributes
    ----------
    modules : list[dict]
        Raw module list: [{n, title, days:[startDay, endDay]}, ...]
    days_raw : list[dict]
        Raw day list: [{day, title, type, tools[], objectives[]}, ...]
    day_lookup : dict[int, dict]
        Primary lookup: day number → enriched day dict (includes `module` key).
    module_lookup : dict[int, dict]
        Module number → module dict.
    """

    _instance: "CurriculumLoader | None" = None

    def __init__(self) -> None:
        raw = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
        self.modules: list[dict] = raw["modules"]
        self.days_raw: list[dict] = raw["days"]

        # Build module lookup: n → module
        self.module_lookup: dict[int, dict] = {m["n"]: m for m in self.modules}

        # Build day → module mapping (day number → module dict)
        self._day_to_module: dict[int, dict] = {}
        for mod in self.modules:
            start, end = mod["days"]
            for d in range(start, end + 1):
                self._day_to_module[d] = mod

        # Primary day lookup: enrich each day with its module info
        self.day_lookup: dict[int, dict] = {}
        for day in self.days_raw:
            day_num = day["day"]
            enriched = {
                **day,
                "module": self._day_to_module.get(day_num),
            }
            self.day_lookup[day_num] = enriched

    @classmethod
    def instance(cls) -> "CurriculumLoader":
        """Return the singleton, constructing it on first call."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_day(self, day_number: int) -> dict | None:
        """Look up a curriculum day by day number. Returns None if not found."""
        return self.day_lookup.get(day_number)

    def get_module(self, module_number: int) -> dict | None:
        """Look up a module by its ordinal number."""
        return self.module_lookup.get(module_number)

    def all_days(self) -> list[dict]:
        """Return all curriculum days sorted by day number."""
        return sorted(self.day_lookup.values(), key=lambda d: d["day"])


# ---------------------------------------------------------------------------
# Candidate Loader
# ---------------------------------------------------------------------------

class CandidateLoader:
    """
    Singleton that parses candidates.json and builds lookup structures.

    For each candidate the loader pre-computes:
        - passed_with_struggle : missions passed after >= 3 attempts
        - skipped_days         : days the candidate skipped
        - first_try_passes     : missions passed on the first attempt
        - enriched_missions    : missions joined with curriculum day metadata

    Attributes
    ----------
    candidates_raw : list[dict]
        Raw candidate list from JSON.
    candidate_lookup : dict[str, dict]
        candidate id → raw candidate dict.
    enriched_lookup : dict[str, dict]
        candidate id → candidate dict augmented with derived fields.
    """

    _instance: "CandidateLoader | None" = None

    def __init__(self) -> None:
        raw = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
        self.candidates_raw: list[dict] = raw["candidates"]
        curriculum = CurriculumLoader.instance()

        self.candidate_lookup: dict[str, dict] = {}
        self.enriched_lookup: dict[str, dict] = {}

        for cand in self.candidates_raw:
            cid = cand["member"]["id"]
            self.candidate_lookup[cid] = cand

            missions = cand.get("missions", [])

            passed_with_struggle: list[dict] = []
            skipped_days: list[dict] = []
            first_try_passes: list[dict] = []
            enriched_missions: list[dict] = []

            for m in missions:
                day_num = m["day"]
                day_meta = curriculum.get_day(day_num) or {}

                enriched = {**m, "curriculum": day_meta}
                enriched_missions.append(enriched)

                if m.get("skipped"):
                    skipped_days.append(enriched)
                elif m.get("passed"):
                    attempts = m.get("attempts", 1)
                    if attempts >= 3:
                        passed_with_struggle.append(enriched)
                    if attempts == 1:
                        first_try_passes.append(enriched)

            self.enriched_lookup[cid] = {
                **cand,
                "passed_with_struggle": passed_with_struggle,
                "skipped_days": skipped_days,
                "first_try_passes": first_try_passes,
                "enriched_missions": enriched_missions,
            }

    @classmethod
    def instance(cls) -> "CandidateLoader":
        """Return the singleton, constructing it on first call."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_candidate(self, candidate_id: str) -> dict | None:
        """Return raw candidate dict by id. Returns None if not found."""
        return self.candidate_lookup.get(candidate_id)

    def get_enriched(self, candidate_id: str) -> dict | None:
        """Return enriched candidate dict (with derived fields) by id."""
        return self.enriched_lookup.get(candidate_id)

    def all_candidates(self) -> list[dict]:
        """Return all raw candidate records."""
        return self.candidates_raw

    def list_ids(self) -> list[str]:
        """Return sorted list of all candidate IDs."""
        return sorted(self.candidate_lookup.keys())
