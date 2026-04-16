from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


def _normalize_skills(skills: list[str]) -> list[str]:
    normalized: list[str] = []
    for skill in skills:
        trimmed = skill.strip().lower()
        if trimmed and trimmed not in normalized:
            normalized.append(trimmed)
    return normalized


class JobListingBase(BaseModel):
    title: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    location: str | None = None
    description: str | None = None
    required_skills: list[str] = Field(min_length=1)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    min_experience_years: int | None = Field(default=None, ge=0)
    max_experience_years: int | None = Field(default=None, ge=0)
    employment_type: str | None = None
    remote: bool = False
    source: str = "manual"
    external_url: str | None = None

    @field_validator("title", "company_name", "location", "description", "employment_type", "source", "external_url", mode="before")
    @classmethod
    def _strip_optional_strings(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("required_skills", "nice_to_have_skills", mode="before")
    @classmethod
    def _validate_skill_lists(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("skills must be a list of strings")
        normalized = _normalize_skills([str(item) for item in value])
        return normalized

    @model_validator(mode="after")
    def _validate_experience_range(self) -> "JobListingBase":
        if not self.required_skills:
            raise ValueError("required_skills cannot be empty")
        if (
            self.min_experience_years is not None
            and self.max_experience_years is not None
            and self.min_experience_years > self.max_experience_years
        ):
            raise ValueError(
                "min_experience_years cannot be greater than max_experience_years"
            )
        return self


class JobListingCreateRequest(JobListingBase):
    pass


class JobListingCreateData(JobListingBase):
    pass


class JobListingUpdateRequest(BaseModel):
    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    description: str | None = None
    required_skills: list[str] | None = None
    nice_to_have_skills: list[str] | None = None
    min_experience_years: int | None = Field(default=None, ge=0)
    max_experience_years: int | None = Field(default=None, ge=0)
    employment_type: str | None = None
    remote: bool | None = None
    source: str | None = None
    external_url: str | None = None

    @field_validator("title", "company_name", "location", "description", "employment_type", "source", "external_url", mode="before")
    @classmethod
    def _strip_update_strings(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("required_skills", "nice_to_have_skills", mode="before")
    @classmethod
    def _normalize_update_skills(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("skills must be a list of strings")
        return _normalize_skills([str(item) for item in value])

    @model_validator(mode="after")
    def _validate_update(self) -> "JobListingUpdateRequest":
        if self.required_skills is not None and not self.required_skills:
            raise ValueError("required_skills cannot be empty")
        if (
            self.min_experience_years is not None
            and self.max_experience_years is not None
            and self.min_experience_years > self.max_experience_years
        ):
            raise ValueError(
                "min_experience_years cannot be greater than max_experience_years"
            )
        return self


class JobListingUpdateData(JobListingUpdateRequest):
    pass


class JobListingResponse(BaseModel):
    id: UUID
    title: str
    company_name: str
    location: str | None
    description: str | None
    required_skills: list[str]
    nice_to_have_skills: list[str]
    min_experience_years: int | None
    max_experience_years: int | None
    employment_type: str | None
    remote: bool
    source: str
    external_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListingListResponse(BaseModel):
    job_listings: list[JobListingResponse]
