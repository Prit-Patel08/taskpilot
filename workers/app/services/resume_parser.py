from __future__ import annotations

import re
from typing import TypedDict

from app.errors.domain_errors import ParseFailed

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(
    r"(?:(?:\+?\d{1,3}[\s().-]*)?(?:\d[\s().-]*){9,15})"
)
DATE_RANGE_PATTERN = re.compile(
    r"(?P<start>(?:19|20)\d{2})\s*[-–]\s*(?P<end>(?:Present|Current|Now|(?:19|20)\d{2}))",
    re.IGNORECASE,
)
EDUCATION_PATTERN = re.compile(
    r"\b(bachelor|master|phd|b\.tech|m\.tech|bsc|msc|mba|university|college|school)\b",
    re.IGNORECASE,
)
KNOWN_SKILLS = (
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "fastapi",
    "django",
    "flask",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "rabbitmq",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "terraform",
    "git",
    "linux",
    "pandas",
    "numpy",
    "scikit-learn",
    "machine learning",
    "data analysis",
    "rest api",
    "graphql",
)


class ResumeExperienceEntry(TypedDict):
    title: str | None
    company: str | None
    date_range: str
    description: str | None


class ParsedResume(TypedDict):
    name: str | None
    email: str | None
    phone: str | None
    skills: list[str]
    education: list[str]
    experience: list[ResumeExperienceEntry]
    raw_text: str


def _normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _extract_name(lines: list[str]) -> str | None:
    for line in lines[:5]:
        if "@" in line or any(char.isdigit() for char in line):
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and len(line) <= 80:
            return line
    return None


def _extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> str | None:
    for match in PHONE_PATTERN.finditer(text):
        digits_only = re.sub(r"\D", "", match.group(0))
        if 10 <= len(digits_only) <= 15:
            return match.group(0).strip()
    return None


def _extract_skills(text: str) -> list[str]:
    normalized_text = text.lower()
    found_skills = [
        skill for skill in KNOWN_SKILLS if re.search(rf"\b{re.escape(skill.lower())}\b", normalized_text)
    ]
    return sorted(set(found_skills))


def _extract_education(lines: list[str]) -> list[str]:
    education_lines = [
        line for line in lines if EDUCATION_PATTERN.search(line)
    ]
    return education_lines[:8]


def _extract_experience(lines: list[str]) -> list[ResumeExperienceEntry]:
    experiences: list[ResumeExperienceEntry] = []

    for index, line in enumerate(lines):
        if not DATE_RANGE_PATTERN.search(line):
            continue

        previous_line = lines[index - 1] if index > 0 else None
        next_lines = lines[index + 1 : index + 3]

        title = previous_line if previous_line and previous_line != line else None
        company = None
        description = " ".join(next_lines).strip() or None

        if title and " at " in title.lower():
            split_parts = re.split(r"\s+at\s+", title, maxsplit=1, flags=re.IGNORECASE)
            if len(split_parts) == 2:
                title, company = split_parts[0].strip() or None, split_parts[1].strip() or None

        experiences.append(
            ResumeExperienceEntry(
                title=title,
                company=company,
                date_range=line,
                description=description,
            )
        )

    return experiences[:10]


def parse_resume(text: str) -> ParsedResume:
    normalized_text = re.sub(r"\r\n?", "\n", text).strip()
    if not normalized_text:
        raise ParseFailed("Resume text was empty after extraction")

    lines = _normalize_lines(normalized_text)
    if not lines:
        raise ParseFailed("Resume text did not contain any parseable lines")

    return ParsedResume(
        name=_extract_name(lines),
        email=_extract_email(normalized_text),
        phone=_extract_phone(normalized_text),
        skills=_extract_skills(normalized_text),
        education=_extract_education(lines),
        experience=_extract_experience(lines),
        raw_text=normalized_text,
    )
