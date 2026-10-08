"""Relational ownership and immutable version records; JSON is versioned case content."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def uid():
    return str(uuid4())


def now():
    return datetime.now(UTC)


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))


class Membership(Base):
    __tablename__ = "memberships"
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        Index("ix_case_library", "workspace_id", "archived", "updated_at", "id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"))
    title: Mapped[str] = mapped_column(String(300))
    original_claim: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(30), default="DRAFT")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Owned:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36))
    case_id: Mapped[str] = mapped_column(String(36))


def case_fk():
    return ForeignKeyConstraint(["workspace_id", "case_id"], ["cases.workspace_id", "cases.id"])


class Revision(Owned, Base):
    __tablename__ = "revisions"
    __table_args__ = (case_fk(), UniqueConstraint("workspace_id", "case_id", "number"))
    number: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Plan(Owned, Base):
    __tablename__ = "plans"
    __table_args__ = (case_fk(),)
    revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class Run(Owned, Base):
    __tablename__ = "runs"
    __table_args__ = (
        case_fk(),
        UniqueConstraint("workspace_id", "case_id", "id"),
        Index("ix_run_recovery", "state", "lease_expires_at"),
    )
    base_revision: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(30), default="QUEUED")
    mode: Mapped[str] = mapped_column(String(20))
    plan: Mapped[dict] = mapped_column(JSON)
    budget: Mapped[dict] = mapped_column(JSON)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    results: Mapped[dict] = mapped_column(JSON, default=dict)
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_generation: Mapped[int] = mapped_column(Integer, default=0)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RunEvent(Owned, Base):
    __tablename__ = "run_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "case_id", "run_id"], ["runs.workspace_id", "runs.case_id", "runs.id"]
        ),
        UniqueConstraint("run_id", "seq"),
    )
    run_id: Mapped[str] = mapped_column(String(36))
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Source(Owned, Base):
    __tablename__ = "sources"
    __table_args__ = (case_fk(), UniqueConstraint("workspace_id", "case_id", "id"))
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(40))
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    extraction_hash: Mapped[str] = mapped_column(String(64), default="")
    artifact_path: Mapped[str] = mapped_column(Text, default="")
    text_path: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Evidence(Owned, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        case_fk(),
        ForeignKeyConstraint(
            ["workspace_id", "case_id", "source_id"],
            ["sources.workspace_id", "sources.case_id", "sources.id"],
        ),
        Index("ix_evidence_claim", "case_id", "claim_id"),
    )
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    claim_id: Mapped[str] = mapped_column(String(36))
    source_id: Mapped[str] = mapped_column(String(36))
    relation: Mapped[str] = mapped_column(String(30))
    quote: Mapped[str] = mapped_column(Text)
    anchor: Mapped[dict] = mapped_column(JSON)
    comparison: Mapped[dict] = mapped_column(JSON, default=dict)
    rationale: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ReviewRequest(Owned, Base):
    __tablename__ = "review_requests"
    __table_args__ = (case_fk(),)
    revision: Mapped[int] = mapped_column(Integer)
    submitted_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    conclusion: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON)
    snapshot: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Export(Owned, Base):
    __tablename__ = "exports"
    __table_args__ = (case_fk(),)
    revision: Mapped[int] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Idempotency(Base):
    __tablename__ = "idempotency"
    workspace_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    operation: Mapped[str] = mapped_column(String(200), primary_key=True)
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(200))
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
