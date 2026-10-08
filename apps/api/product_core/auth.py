from dataclasses import dataclass
from secrets import compare_digest, token_urlsafe
from urllib.parse import urlparse

from fastapi import Request

from .config import get_settings
from .db import SessionLocal, set_workspace
from .models import Membership, User, Workspace


class DomainError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code, self.message, self.status = code, message, status


@dataclass(frozen=True)
class Actor:
    id: str
    workspace_id: str
    role: str
    name: str


def seed_development():
    if get_settings().mode != "development":
        return
    with SessionLocal.begin() as db:
        if not db.get(Workspace, "local-newsroom"):
            db.add(Workspace(id="local-newsroom", name="Local newsroom"))
            db.flush()
        for user_id, name in [
            ("researcher", "Researcher"),
            ("editor", "Editor"),
            ("owner", "Workspace owner"),
        ]:
            if not db.get(User, user_id):
                db.add(User(id=user_id, name=name))
                db.flush()
            if not db.get(Membership, ("local-newsroom", user_id)):
                db.add(Membership(workspace_id="local-newsroom", user_id=user_id, role=user_id))


def dev_login(request: Request, user_id: str):
    if get_settings().mode != "development" or request.url.hostname not in {
        "localhost",
        "127.0.0.1",
        "testserver",
    }:
        raise DomainError("AUTH_REQUIRED", "Local identity is disabled on this host.", 401)
    if user_id not in {"researcher", "editor", "owner"}:
        raise DomainError("AUTH_REQUIRED", "Unknown local identity.", 401)
    validate_origin(request)
    request.session.clear()
    request.session.update(user_id=user_id, workspace_id="local-newsroom", csrf=token_urlsafe(32))


def validate_origin(request: Request):
    origin = request.headers.get("origin")
    approved_origins = {str(request.base_url).rstrip("/"), get_settings().public_url.rstrip("/")}
    local_development = get_settings().mode == "development" and urlparse(origin or "").hostname in {
        "localhost",
        "127.0.0.1",
    }
    if origin and origin.rstrip("/") not in approved_origins and not local_development:
        raise DomainError("FORBIDDEN", "Request origin is not authorized.", 403)


def actor(request: Request) -> Actor:
    user_id, workspace_id = request.session.get("user_id"), request.session.get("workspace_id")
    if not user_id or not workspace_id:
        raise DomainError("AUTH_REQUIRED", "Sign in to access this workspace.", 401)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        validate_origin(request)
        if not compare_digest(
            request.headers.get("x-csrf-token", ""), request.session.get("csrf", "_invalid_")
        ):
            raise DomainError("FORBIDDEN", "Refresh your session before making this change.", 403)
    with SessionLocal() as db:
        set_workspace(db, workspace_id)
        membership = db.get(Membership, (workspace_id, user_id))
        user = db.get(User, user_id)
        if membership is None or user is None:
            raise DomainError("AUTH_REQUIRED", "Workspace access has been revoked.", 401)
        return Actor(user_id, workspace_id, membership.role, user.name)


def require_role(actor: Actor, *roles: str):
    if actor.role not in roles:
        raise DomainError("FORBIDDEN", "Your workspace role cannot perform this action.", 403)
