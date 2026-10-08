from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RevisionInput(Input):
    expected_revision: int = Field(ge=1)


class CreateCase(Input):
    title: str = Field(min_length=1, max_length=300)
    original_claim: str = Field(min_length=1, max_length=10000)


class Claim(Input):
    id: str | None = None
    text: str = Field(min_length=1, max_length=3000)
    subject: str = Field(min_length=1, max_length=300)
    geography: str = Field(min_length=1, max_length=300)
    period: str = Field(min_length=1, max_length=100)
    stage: Literal[
        "UNKNOWN",
        "ANNOUNCED",
        "APPROVED",
        "PROCURED",
        "UNDER_CONSTRUCTION",
        "PHYSICALLY_COMPLETED",
        "INAUGURATED",
        "OPERATIONAL",
    ] = "UNKNOWN"
    measure: str = Field(default="", max_length=100)
    value: str | float | None = None
    unit: str = Field(default="", max_length=100)
    currency: Literal["INR", "USD", "EUR", "GBP"] | None = None
    denominator: str | None = Field(default=None, max_length=200)
    attribution: str | None = Field(default=None, max_length=300)


class Scope(RevisionInput):
    claims: list[Claim] = Field(min_length=1, max_length=3)


class Budget(Input):
    searches: int = Field(default=12, ge=1, le=12)
    documents: int = Field(default=30, ge=1, le=30)
    rounds: int = Field(default=3, ge=1, le=3)
    tokens: int = Field(default=60000, ge=100, le=60000)
    seconds: int = Field(default=600, ge=10, le=600)
    usd: float = Field(default=2, gt=0, le=2)


class StartRun(RevisionInput):
    plan_id: str
    mode: Literal["live", "fixture"] = "live"
    budget: Budget = Field(default_factory=Budget)


class CasePatch(RevisionInput):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    tags: list[str] | None = Field(default=None, max_length=20)
    assignee_id: str | None = None
    archived: bool | None = None


class Note(RevisionInput):
    text: str = Field(min_length=1, max_length=10000)
    attribution: str = Field(min_length=1, max_length=300)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class Override(RevisionInput):
    relation: Literal["SUPPORTS", "CONTRADICTS", "CONTEXT", "INCOMPARABLE", "INSUFFICIENT"]
    reason: str = Field(min_length=3, max_length=3000)


class LedgerOverride(RevisionInput):
    observation_id: str
    corrected_fields: dict
    reason: str = Field(min_length=3, max_length=3000)


class SubmitReview(RevisionInput):
    conclusion: str = Field(min_length=3, max_length=10000)
    citations: list[str] = Field(default_factory=list, max_length=100)


class Decision(RevisionInput):
    decision: Literal["APPROVE", "RETURN"]
    reason: str = Field(min_length=3, max_length=3000)


class SourceInput(RevisionInput):
    url: str = Field(min_length=8, max_length=4000)
    page_ranges: list[list[int]] | None = None


class ExportInput(Input):
    revision: int = Field(ge=1)
    format: Literal["md", "html", "json"]


class MemberInput(Input):
    user_id: str = Field(min_length=1, max_length=200)
    role: Literal["researcher", "editor", "owner"]


class RoleInput(Input):
    role: Literal["researcher", "editor", "owner", "removed"]
