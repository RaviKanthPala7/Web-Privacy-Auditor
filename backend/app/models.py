from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Category(str, Enum):
    """Types of third-party / tracker buckets shown in the report."""

    ANALYTICS = "Analytics"
    ADVERTISING = "Advertising"
    SOCIAL = "Social"
    CDN = "CDN"
    UNKNOWN = "Unknown"


class AuditRequest(BaseModel):
    """What the frontend sends when user clicks Run audit."""

    url: HttpUrl


class TrackerMatch(BaseModel):
    """One known tracker we recognized (e.g. Google Analytics)."""

    name: str
    category: Category
    matched_url: str
    why_it_matters: str


class ThirdPartyRequest(BaseModel):
    """One external domain the page talked to over the network."""

    domain: str
    url: str
    resource_type: str


class CookieFinding(BaseModel):
    """One cookie set during the browser visit."""

    name: str
    domain: str
    path: str = "/"
    secure: bool = False
    http_only: bool = False
    same_site: Optional[str] = None


class ScriptFinding(BaseModel):
    """One third-party script tag loaded by the page."""

    src: str
    domain: str
    async_attr: bool = False
    defer_attr: bool = False


class CategorySummary(BaseModel):
    """Count per category for the summary cards in the UI."""

    category: Category
    count: int


class AuditReport(BaseModel):
    """Full JSON report returned to the Vue app."""

    url: str
    scanned_at: str
    duration_ms: int
    summary: list[CategorySummary] = Field(default_factory=list)
    trackers: list[TrackerMatch] = Field(default_factory=list)
    third_parties: list[ThirdPartyRequest] = Field(default_factory=list)
    cookies: list[CookieFinding] = Field(default_factory=list)
    scripts: list[ScriptFinding] = Field(default_factory=list)
    page_title: Optional[str] = None
    notes: list[str] = Field(default_factory=list)
