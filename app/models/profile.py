from datetime import UTC, datetime

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    start_year: int | None = None
    start_month: int | None = None
    end_year: int | None = None
    end_month: int | None = None
    is_current: bool = False


class Location(BaseModel):
    city: str | None = None
    state: str | None = None
    country: str | None = None
    display: str | None = None


class Position(BaseModel):
    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    description: str | None = None
    employment_type: str | None = None
    date_range: DateRange | None = None


class Education(BaseModel):
    school_name: str | None = None
    degree_name: str | None = None
    field_of_study: str | None = None
    grade: str | None = None
    activities: str | None = None
    description: str | None = None
    date_range: DateRange | None = None


class Skill(BaseModel):
    name: str


class Certification(BaseModel):
    name: str | None = None
    authority: str | None = None
    url: str | None = None
    issue_date: str | None = None


class Language(BaseModel):
    name: str | None = None
    proficiency: str | None = None


class TreasuryItem(BaseModel):
    title: str | None = None
    url: str | None = None
    provider: str | None = None
    kind: str | None = None  # "url" | "document"


class ProfileResponse(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    public_identifier: str | None = None
    profile_url: str | None = None
    urn: str | None = None
    location: Location | None = None
    profile_picture_url: str | None = None
    cover_picture_url: str | None = None
    positions: list[Position] = Field(default_factory=list)
    educations: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    skills_total: int | None = None  # Voyager paging.total when skills are truncated
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    treasury_media: list[TreasuryItem] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
