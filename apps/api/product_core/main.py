"""Authenticated API and local web host for the evidence workspace."""

import asyncio
import json
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import UTC, timedelta
from hashlib import sha256
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import schemas, service
from .auth import Actor, DomainError, actor, dev_login, require_role, seed_development
from .config import artifact_root, get_settings
from .db import SessionLocal, init_db
from .middleware import RequestBodyLimitMiddleware
from .models import (
    Case,
    Export,
    Membership,
    ReviewRequest,
    Revision,
    Source,
    User,
    Workspace,
    now,
    uid,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app):
    if settings.mode == "development":
        init_db()
        seed_development()
    artifact_root()
    yield


app = FastAPI(title="FactLedger Evidence Workspace", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret.get_secret_value(),
    session_cookie="evidence_session",
    same_site="lax",
    https_only=settings.mode == "production",
    max_age=8 * 3600,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts.split(","))
app.add_middleware(RequestBodyLimitMiddleware)
rate_windows = defaultdict(deque)
_actor_dependency = Depends(actor)
_pdf_upload = File(...)


@app.middleware("http")
async def safe_responses(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    # Bounded per-process ingress guard; workspace/provider admission is persistent.
    if request.url.path.startswith("/v1"):
        identity = request.client.host if request.client else "unknown"
        window = rate_windows[identity]
        timestamp = now().timestamp()
        while window and window[0] < timestamp - 60:
            window.popleft()
        if len(window) >= 300:
            return JSONResponse(
                {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests. Retry shortly.",
                    "request_id": request_id,
                },
                status_code=429,
                headers={"Retry-After": "30"},
            )
        window.append(timestamp)
        if len(rate_windows) > 10000:
            for key in list(rate_windows):
                if not rate_windows[key] or rate_windows[key][-1] < timestamp - 60:
                    rate_windows.pop(key, None)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    )
    if request.url.path.startswith("/v1"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


@app.exception_handler(DomainError)
async def domain_error(request, exc):
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(request.state, "request_id", ""),
            "details": {},
        },
        status_code=exc.status,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        {
            "code": "INVALID_SCOPE",
            "message": "Check the supplied fields.",
            "request_id": getattr(request.state, "request_id", ""),
            "details": [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()],
        },
        status_code=422,
    )


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        {
            "code": "REVISION_CONFLICT",
            "message": "A concurrent change occurred. Reload and retry.",
            "request_id": getattr(request.state, "request_id", ""),
        },
        status_code=409,
    )


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready", "mode": settings.mode}


@app.post("/v1/auth/dev")
def dev(request: Request, data: dict):
    dev_login(request, data.get("user_id", "researcher"))
    return {"authenticated": True}


@app.get("/v1/session")
def session(request: Request):
    if not request.session.get("user_id") and settings.mode == "development":
        dev_login(request, "researcher")
    identity = actor(request)
    with service.transaction(identity) as db:
        workspace = db.get(Workspace, identity.workspace_id)
    return {
        "user": {"id": identity.id, "name": identity.name},
        "workspace": {"id": identity.workspace_id, "name": workspace.name},
        "role": identity.role,
        "csrf_token": request.session["csrf"],
        "mode": settings.mode,
        "providers": {
            "serpapi": bool(settings.serpapi_api_key.get_secret_value()),
            "groq": bool(settings.groq_api_key.get_secret_value()),
            "nvidia": bool(settings.nvidia_api_key.get_secret_value()),
        },
    }


@app.post("/v1/auth/logout")
def logout(request: Request, identity: Actor = _actor_dependency):
    request.session.clear()
    return {"authenticated": False}


def oauth_client():
    from authlib.integrations.starlette_client import OAuth

    oauth = OAuth()
    oauth.register(
        name="workspace",
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret.get_secret_value(),
        server_metadata_url=settings.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile", "code_challenge_method": "S256"},
    )
    return oauth.workspace


@app.get("/v1/auth/login")
async def oidc_login(request: Request):
    if not settings.oidc_issuer:
        raise DomainError("AUTH_REQUIRED", "Hosted sign-in is not configured.", 401)
    return await oauth_client().authorize_redirect(
        request, settings.public_url.rstrip("/") + "/v1/auth/callback"
    )


@app.get("/v1/auth/callback")
async def oidc_callback(request: Request):
    try:
        token = await oauth_client().authorize_access_token(request)
        claims = token["userinfo"]
        if claims.get("iss", "").rstrip("/") != settings.oidc_issuer.rstrip("/"):
            raise ValueError("Wrong issuer")
        user_id = sha256((claims["iss"] + "|" + claims["sub"]).encode()).hexdigest()
        with SessionLocal.begin() as db:
            user = db.get(User, user_id)
            if not user:
                db.add(User(id=user_id, name=str(claims.get("name", "Verified user"))[:200]))
                db.flush()
            membership = db.get(Membership, (settings.oidc_workspace_id, user_id))
            if not membership:
                raise DomainError("FORBIDDEN", "Ask your workspace owner to add this verified identity.", 403)
        request.session.clear()
        request.session.update(
            user_id=user_id, workspace_id=settings.oidc_workspace_id, csrf=token_urlsafe(32)
        )
        return RedirectResponse("/")
    except DomainError:
        raise
    except Exception:  # noqa: BLE001 -- provider errors must never expose token response data
        raise DomainError("AUTH_REQUIRED", "Sign-in could not be verified. Please try again.", 401) from None


@app.get("/v1/cases")
def list_cases(
    search: str = "",
    state: str = "",
    archived: bool = False,
    cursor: str = "",
    limit: int = 25,
    identity: Actor = _actor_dependency,
):
    limit = max(1, min(limit, 100))
    with service.transaction(identity) as db:
        query = select(Case).where(
            Case.workspace_id == identity.workspace_id, Case.deleted_at.is_(None), Case.archived == archived
        )
        if search:
            query = query.where(
                Case.title.ilike(
                    "%" + search[:300].replace("%", "\\%").replace("_", "\\_") + "%", escape="\\"
                )
            )
        if state:
            query = query.where(Case.state == state)
        if cursor:
            query = query.where(Case.id > cursor)
        items = list(db.scalars(query.order_by(Case.id).limit(limit + 1)))
        return {
            "items": [service.serialize(c) for c in items[:limit]],
            "next_cursor": items[limit - 1].id if len(items) > limit else None,
        }


@app.get("/v1/workspaces/{workspace_id}/cases")
def workspace_cases(workspace_id: str, identity: Actor = _actor_dependency):
    if workspace_id != identity.workspace_id:
        raise DomainError("NOT_FOUND", "Workspace unavailable.", 404)
    return list_cases(identity=identity)


@app.post("/v1/cases")
def create_case(data: schemas.CreateCase, identity: Actor = _actor_dependency):
    return service.create_case(identity, data.model_dump())


@app.get("/v1/cases/{case_id}")
def get_case(case_id: str, revision: int | None = None, identity: Actor = _actor_dependency):
    with service.transaction(identity) as db:
        return service.detail(db, service.case_for(db, identity, case_id), revision)


@app.post("/v1/cases/{case_id}/scope")
def scope(case_id: str, data: schemas.Scope, identity: Actor = _actor_dependency):
    return service.scope_case(identity, case_id, data.model_dump())


@app.patch("/v1/cases/{case_id}")
def patch_case(case_id: str, data: schemas.CasePatch, identity: Actor = _actor_dependency):
    return service.patch_case(identity, case_id, data.model_dump(exclude_unset=True))


@app.post("/v1/cases/{case_id}/plans")
def plan(case_id: str, data: schemas.RevisionInput, identity: Actor = _actor_dependency):
    return service.make_plan(identity, case_id, data.expected_revision)


@app.post("/v1/cases/{case_id}/runs", status_code=202)
def start_run(
    case_id: str,
    data: schemas.StartRun,
    idempotency_key: str = Header(default="", max_length=200),
    identity: Actor = _actor_dependency,
):
    if data.mode == "live" and not settings.serpapi_api_key.get_secret_value():
        raise DomainError(
            "PROVIDER_UNAVAILABLE", "Configure SerpApi locally before starting live research.", 503
        )
    return service.start_run(identity, case_id, data.model_dump(), idempotency_key)


@app.get("/v1/runs/{run_id}")
def get_run(run_id: str, identity: Actor = _actor_dependency):
    with service.transaction(identity) as db:
        return service.run_detail(db, service.run_for(db, identity, run_id))


@app.post("/v1/runs/{run_id}/{action}")
def run_command(run_id: str, action: str, data: dict | None = None, identity: Actor = _actor_dependency):
    if action == "integrate":
        try:
            validated = schemas.RevisionInput.model_validate(data or {})
        except ValidationError:
            raise DomainError(
                "INVALID_SCOPE", "Supply a valid expected_revision to integrate research.", 422
            ) from None
        return service.integrate(identity, run_id, validated.expected_revision)
    if action not in {"pause", "resume", "cancel"}:
        raise DomainError("NOT_FOUND", "Unknown run command.", 404)
    return service.control_run(identity, run_id, action)


@app.get("/v1/runs/{run_id}/events")
async def events(
    run_id: str,
    request: Request,
    last_event_id: str = Header(default="0"),
    identity: Actor = _actor_dependency,
):
    try:
        after = max(0, int(last_event_id))
    except ValueError:
        raise DomainError("INVALID_SCOPE", "Invalid event cursor.", 422) from None
    get_run(run_id, identity)

    async def stream():
        nonlocal after
        for _ in range(300):
            if await request.is_disconnected():
                return
            current_actor = actor(request)
            result = get_run(run_id, current_actor)
            for item in result["events"]:
                if item["seq"] > after:
                    after = item["seq"]
                    yield f"id: {after}\ndata: {json.dumps(item)}\n\n"
            yield ": heartbeat\n\n"
            if result["state"] in {"COMPLETED", "PARTIAL", "CANCELLED", "FAILED"}:
                return
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})


@app.post("/v1/cases/{case_id}/notes")
def add_note(case_id: str, data: schemas.Note, identity: Actor = _actor_dependency):
    return service.add_note(identity, case_id, data.model_dump())


@app.patch("/v1/evidence/{evidence_id}/relation")
def override(evidence_id: str, data: schemas.Override, identity: Actor = _actor_dependency):
    return service.override_evidence(identity, evidence_id, data.model_dump())


@app.get("/v1/cases/{case_id}/ledger")
def ledger(case_id: str, revision: int | None = None, identity: Actor = _actor_dependency):
    return get_case(case_id, revision, identity)["payload"]["ledger"]


@app.post("/v1/cases/{case_id}/ledger-overrides")
def ledger_override(case_id: str, data: schemas.LedgerOverride, identity: Actor = _actor_dependency):
    if set(data.corrected_fields) - {
        "event_date",
        "reference_period",
        "denominator",
        "attributed_to",
        "limitations",
    }:
        raise DomainError(
            "INVALID_SCOPE",
            "Only anchored mapping metadata can be corrected; re-analyze stage/value changes.",
            422,
        )
    with service.transaction(identity) as db:
        case = service.case_for(db, identity, case_id)
        service.expected(case, data.expected_revision)
        payload = service.snapshot(db, case)
        observation = next(
            (
                o
                for group in ("stages", "funding", "metrics")
                for o in payload["ledger"][group]
                if o["id"] == data.observation_id
            ),
            None,
        )
        if not observation:
            raise DomainError("NOT_FOUND", "Observation unavailable.", 404)
        observation.update(data.corrected_fields)
        observation["override"] = {"actor_id": identity.id, "reason": data.reason}
        service.persist_revision(db, identity, case, payload, "ledger.corrected")
        return service.detail(db, case)


@app.patch("/v1/lineage/{lineage_id}")
def lineage_override(lineage_id: str, data: dict, identity: Actor = _actor_dependency):
    if (
        data.get("status") not in {"POSSIBLE", "HUMAN_CONFIRMED", "REJECTED"}
        or len(data.get("reason", "")) < 3
    ):
        raise DomainError("INVALID_SCOPE", "Choose a lineage status and give a reason.", 422)
    with service.transaction(identity) as db:
        case = service.case_for(db, identity, data.get("case_id"))
        service.expected(case, data.get("expected_revision"))
        payload = service.snapshot(db, case)
        edge = next((e for e in payload["lineage"] if e["id"] == lineage_id), None)
        if not edge:
            raise DomainError("NOT_FOUND", "Lineage unavailable.", 404)
        edge.update(status=data["status"], override={"actor_id": identity.id, "reason": data["reason"]})
        service.persist_revision(db, identity, case, payload, "lineage.corrected")
        return service.detail(db, case)


def private_path(path):
    root = artifact_root()
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise DomainError(
            "SOURCE_UNAVAILABLE", "The full source artifact has expired or is unavailable.", 404
        )
    return resolved


@app.get("/v1/sources/{source_id}")
def get_source(source_id: str, identity: Actor = _actor_dependency):
    with service.transaction(identity) as db:
        source = db.scalar(
            select(Source).where(Source.id == source_id, Source.workspace_id == identity.workspace_id)
        )
        if not source:
            raise DomainError("NOT_FOUND", "Source unavailable.", 404)
        service.case_for(db, identity, source.case_id)
        result = service.serialize(source)
        result["text"] = private_path(source.text_path).read_text("utf-8") if source.text_path else ""
        return result


@app.get("/v1/sources/{source_id}/download")
def source_download(source_id: str, identity: Actor = _actor_dependency):
    with service.transaction(identity) as db:
        source = db.scalar(
            select(Source).where(Source.id == source_id, Source.workspace_id == identity.workspace_id)
        )
        if not source:
            raise DomainError("NOT_FOUND", "Source unavailable.", 404)
        service.case_for(db, identity, source.case_id)
        path = private_path(source.artifact_path)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename="preserved-source",
        headers={"Cache-Control": "private, no-store"},
    )


def persist_manual(identity, case_id, expected_revision, url, document):
    from .investigation.storage import store_document

    with service.transaction(identity) as db:
        case = service.case_for(db, identity, case_id)
        service.expected(case, expected_revision)
        try:
            stored = store_document(identity.workspace_id, case_id, document, root=artifact_root())
        except ValueError as exc:
            if str(exc) in {"STORAGE_LIMIT_EXCEEDED", "STORAGE_BUSY"}:
                raise DomainError(
                    str(exc), "Workspace artifact storage is full or busy. Free space or retry later.", 429
                ) from None
            raise
        source = Source(
            workspace_id=identity.workspace_id,
            case_id=case.id,
            url=url,
            title=document.title,
            status="AVAILABLE",
            metadata_json=stored.pop("metadata"),
            **stored,
        )
        db.add(source)
        db.flush()
        payload = service.snapshot(db, case)
        payload["sources"].append(service.serialize(source))
        service.persist_revision(db, identity, case, payload, "source.added")
        return service.detail(db, case)


@app.post("/v1/cases/{case_id}/sources")
def add_source(case_id: str, data: schemas.SourceInput, identity: Actor = _actor_dependency):
    from .investigation.acquisition import acquire

    with service.transaction(identity) as db:
        service.expected(service.case_for(db, identity, case_id), data.expected_revision)
    try:
        document = acquire(data.url, data.page_ranges)
    except (ValueError, OSError, TimeoutError) as exc:
        raise DomainError(
            "SOURCE_UNAVAILABLE",
            "Source acquisition failed: " + type(exc).__name__ + ". Try a lawful PDF copy or another source.",
            422,
        ) from None
    return persist_manual(identity, case_id, data.expected_revision, data.url, document)


@app.post("/v1/cases/{case_id}/uploads")
async def upload(
    case_id: str,
    expected_revision: int = Form(...),
    file: UploadFile = _pdf_upload,
    identity: Actor = _actor_dependency,
):
    from .investigation.acquisition import extract_document

    with service.transaction(identity) as db:
        service.expected(service.case_for(db, identity, case_id), expected_revision)
    raw = await file.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024 or not raw.startswith(b"%PDF-"):
        raise DomainError("INVALID_SCOPE", "Upload a PDF no larger than 20 MB.", 422)
    try:
        document = await asyncio.to_thread(extract_document, raw, "application/pdf")
    except (ValueError, OSError, TimeoutError):
        raise DomainError(
            "SOURCE_UNAVAILABLE", "PDF extraction failed or exceeded its resource limits.", 422
        ) from None
    document.metadata["provenance"] = "User upload; authenticity not independently verified"
    return persist_manual(identity, case_id, expected_revision, "upload://" + uid(), document)


@app.post("/v1/cases/{case_id}/review-requests")
def submit_review(case_id: str, data: schemas.SubmitReview, identity: Actor = _actor_dependency):
    return service.submit_review(identity, case_id, data.model_dump())


@app.get("/v1/review-requests")
def review_queue(identity: Actor = _actor_dependency):
    with service.transaction(identity) as db:
        reviews = db.scalars(
            select(ReviewRequest)
            .join(Case, Case.id == ReviewRequest.case_id)
            .where(ReviewRequest.workspace_id == identity.workspace_id, Case.deleted_at.is_(None))
            .order_by(ReviewRequest.created_at.desc())
            .limit(100)
        )
        return {
            "items": [
                dict(service.serialize(r), title=r.snapshot.get("_case", {}).get("title", "Case"))
                for r in reviews
            ]
        }


@app.get("/v1/review-requests/{review_id}")
def get_review(review_id: str, identity: Actor = _actor_dependency):
    with service.transaction(identity) as db:
        review, case = service.review_for(db, identity, review_id)
        return {
            **service.serialize(review),
            "payload": review.snapshot,
            "title": review.snapshot.get("_case", {}).get("title", case.title),
            "current_revision": case.revision,
        }


@app.post("/v1/review-requests/{review_id}/decisions")
def decision(review_id: str, data: schemas.Decision, identity: Actor = _actor_dependency):
    return service.decide_review(identity, review_id, data.model_dump())


@app.post("/v1/cases/{case_id}/exports")
def export(case_id: str, data: schemas.ExportInput, identity: Actor = _actor_dependency):
    return service.export_case(identity, case_id, data.revision, data.format)


@app.get("/v1/exports/{export_id}/download")
def download(export_id: str, identity: Actor = _actor_dependency):
    with service.transaction(identity) as db:
        pack = db.scalar(
            select(Export).where(Export.id == export_id, Export.workspace_id == identity.workspace_id)
        )
        if not pack:
            raise DomainError("NOT_FOUND", "Pack unavailable.", 404)
        service.case_for(db, identity, pack.case_id)
        media_type = {"md": "text/markdown", "html": "text/html", "json": "application/json"}[pack.format]
        return Response(
            pack.content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="evidence-pack-r{pack.revision}.{pack.format}"',
                "Cache-Control": "private, no-store",
            },
        )


@app.get("/v1/cases/{case_id}/revisions")
def revisions(case_id: str, identity: Actor = _actor_dependency):
    with service.transaction(identity) as db:
        service.case_for(db, identity, case_id)
        return {
            "items": [
                {"id": r.id, "number": r.number, "created_at": r.created_at.isoformat()}
                for r in db.scalars(
                    select(Revision).where(Revision.case_id == case_id).order_by(Revision.number.desc())
                )
            ]
        }


@app.get("/v1/cases/{case_id}/revisions/{revision}/diff")
def diff(case_id: str, revision: int, from_revision: int = 1, identity: Actor = _actor_dependency):
    with service.transaction(identity) as db:
        case = service.case_for(db, identity, case_id)
        before, after = service.snapshot(db, case, from_revision), service.snapshot(db, case, revision)
        changed = {
            key: {"before": before.get(key), "after": after.get(key)}
            for key in after
            if before.get(key) != after.get(key)
        }
        return {"from_revision": from_revision, "to_revision": revision, "changes": changed}


@app.delete("/v1/cases/{case_id}")
def delete_case(case_id: str, expected_revision: int, identity: Actor = _actor_dependency):
    return service.delete_case(identity, case_id, expected_revision)


@app.post("/v1/cases/{case_id}/restore")
def restore(case_id: str, identity: Actor = _actor_dependency):
    require_role(identity, "owner")
    with service.transaction(identity) as db:
        case = service.case_for(db, identity, case_id, include_deleted=True)
        deleted = (
            case.deleted_at.replace(tzinfo=UTC)
            if case.deleted_at and case.deleted_at.tzinfo is None
            else case.deleted_at
        )
        if case.state == "PURGED" or not deleted or now() - deleted > timedelta(days=7):
            raise DomainError("INVALID_STATE", "Case is outside its recovery period.")
        ledger = artifact_root().parent / "deletion-ledger.jsonl"
        with ledger.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {
                        "workspace_id": identity.workspace_id,
                        "case_id": case.id,
                        "restored_at": now().isoformat(),
                    }
                )
                + "\n"
            )
            file.flush()
            import os

            os.fsync(file.fileno())
        case.deleted_at = None
        case.state = "DRAFT"
        service.audit(db, identity, case, "case.restored")
        return service.detail(db, case)


@app.get("/v1/workspaces/{workspace_id}/members")
def members(workspace_id: str, identity: Actor = _actor_dependency):
    if workspace_id != identity.workspace_id:
        raise DomainError("NOT_FOUND", "Workspace unavailable.", 404)
    with service.transaction(identity) as db:
        return {
            "items": [
                {"user_id": m.user_id, "role": m.role, "name": u.name}
                for m, u in db.execute(
                    select(Membership, User)
                    .join(User, User.id == Membership.user_id)
                    .where(Membership.workspace_id == workspace_id)
                )
            ]
        }


def membership_change(identity, user_id, role):
    require_role(identity, "owner")
    with service.transaction(identity) as db:
        # Serialize all ownership changes on the workspace to protect the final owner.
        db.scalar(select(Workspace).where(Workspace.id == identity.workspace_id).with_for_update())
        if not db.get(User, user_id):
            raise DomainError("INVALID_SCOPE", "Add an existing verified user; no invitation is sent.", 422)
        membership = db.get(Membership, (identity.workspace_id, user_id))
        if membership and membership.role == "owner" and role != "owner":
            owners = db.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.workspace_id == identity.workspace_id, Membership.role == "owner")
            )
            if owners <= 1:
                raise DomainError("REVISION_CONFLICT", "The workspace must retain an owner.")
        if role == "removed":
            if membership:
                db.delete(membership)
        elif membership:
            membership.role = role
        else:
            db.add(Membership(workspace_id=identity.workspace_id, user_id=user_id, role=role))
        return {"user_id": user_id, "role": role}


@app.post("/v1/workspaces/{workspace_id}/members")
def add_member(workspace_id: str, data: schemas.MemberInput, identity: Actor = _actor_dependency):
    if workspace_id != identity.workspace_id:
        raise DomainError("NOT_FOUND", "Workspace unavailable.", 404)
    return membership_change(identity, data.user_id, data.role)


@app.patch("/v1/workspaces/{workspace_id}/members/{user_id}")
def patch_member(
    workspace_id: str, user_id: str, data: schemas.RoleInput, identity: Actor = _actor_dependency
):
    if workspace_id != identity.workspace_id:
        raise DomainError("NOT_FOUND", "Workspace unavailable.", 404)
    return membership_change(identity, user_id, data.role)


@app.get("/{path:path}", include_in_schema=False)
def web(path: str):
    if path.startswith(("v1/", "health/")):
        raise DomainError("NOT_FOUND", "Endpoint unavailable.", 404)
    root = Path(settings.web_dist).resolve()
    file = (root / path).resolve()
    if file.is_relative_to(root) and file.is_file():
        return FileResponse(file)
    if (root / "index.html").is_file():
        return FileResponse(root / "index.html")
    return JSONResponse(
        {
            "message": "Build apps/web with pnpm build, or use the Vite development server.",
            "api_docs": "/docs",
        }
    )
