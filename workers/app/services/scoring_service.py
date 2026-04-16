from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any

from app.errors import ScoringFailed

TOKEN_PATTERN = re.compile(r"[a-z0-9]{4,}")
EXPERIENCE_PATTERN = re.compile(
    r"(?P<start>(?:19|20)\d{2})\s*[-–]\s*(?P<end>present|current|now|(?:19|20)\d{2})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ScoreComputationResult:
    score: int
    breakdown: dict[str, float]


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        normalized_item = str(item).strip().lower()
        if normalized_item and normalized_item not in normalized:
            normalized.append(normalized_item)
    return normalized


def _safe_ratio(matches: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return max(0.0, min(matches / total, 1.0))


def _extract_years_of_experience(resume_extraction: dict[str, Any]) -> float:
    parsed = resume_extraction.get("parsed_json", resume_extraction)
    experience_entries = parsed.get("experience")
    if not isinstance(experience_entries, list):
        return 0.0

    start_years: list[int] = []
    end_years: list[int] = []
    current_year = datetime.now(UTC).year

    for entry in experience_entries:
        if not isinstance(entry, dict):
            continue
        date_range = str(entry.get("date_range", "")).strip()
        match = EXPERIENCE_PATTERN.search(date_range)
        if match is None:
            continue
        start_year = int(match.group("start"))
        raw_end = match.group("end").lower()
        end_year = current_year if raw_end in {"present", "current", "now"} else int(raw_end)
        if end_year < start_year:
            continue
        start_years.append(start_year)
        end_years.append(end_year)

    if not start_years or not end_years:
        return 0.0
    return float(max(0, max(end_years) - min(start_years)))


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return set(TOKEN_PATTERN.findall(text.lower()))


def compute_score(
    resume_extraction: dict[str, Any],
    job_listing: dict[str, Any],
) -> dict[str, Any]:
    try:
        parsed = resume_extraction.get("parsed_json", resume_extraction)
        resume_skills = set(_normalize_string_list(parsed.get("skills")))
        required_skills = set(_normalize_string_list(job_listing.get("required_skills")))
        nice_to_have_skills = set(_normalize_string_list(job_listing.get("nice_to_have_skills")))

        required_matches = len(resume_skills & required_skills)
        nice_to_have_matches = len(resume_skills & nice_to_have_skills)
        skill_score = _safe_ratio(required_matches, len(required_skills))
        nice_to_have_score = _safe_ratio(
            nice_to_have_matches,
            len(nice_to_have_skills),
        )

        estimated_years = _extract_years_of_experience(parsed)
        min_experience_years_raw = job_listing.get("min_experience_years")
        min_experience_years = (
            int(min_experience_years_raw)
            if isinstance(min_experience_years_raw, int)
            else None
        )
        if min_experience_years is None or min_experience_years <= 0:
            experience_score = 1.0
        elif estimated_years <= 0:
            experience_score = 0.5
        else:
            experience_score = min(estimated_years / float(min_experience_years), 1.0)

        resume_tokens = _tokenize(str(parsed.get("raw_text", "")))
        job_tokens = _tokenize(str(job_listing.get("description", "")))
        keyword_matches = len(resume_tokens & job_tokens)
        keyword_score = _safe_ratio(
            keyword_matches,
            max(min(len(job_tokens), 50), 1),
        )

        final_score = int(
            (
                0.5 * skill_score
                + 0.2 * nice_to_have_score
                + 0.2 * experience_score
                + 0.1 * keyword_score
            )
            * 100
        )

        return {
            "score": max(0, min(final_score, 100)),
            "breakdown": {
                "skills": round(skill_score, 4),
                "nice_to_have": round(nice_to_have_score, 4),
                "experience": round(experience_score, 4),
                "keywords": round(keyword_score, 4),
            },
        }
    except Exception as exc:
        raise ScoringFailed("Deterministic scoring computation failed") from exc
