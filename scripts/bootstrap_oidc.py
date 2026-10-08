"""Provision a manually verified OIDC user using a privileged maintenance connection."""

import argparse
from hashlib import sha256
from urllib.parse import urlsplit

from product_core.db import SessionLocal
from product_core.models import Membership, User, Workspace
from sqlalchemy import text


def identity_id(issuer: str, subject: str) -> str:
    parsed = urlsplit(issuer)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
    ):
        raise ValueError("Issuer must be an exact HTTPS OIDC issuer without credentials/query/fragment")
    if not subject or len(subject) > 500 or "\n" in subject or "\r" in subject:
        raise ValueError("Supply the verified nonempty OIDC subject")
    return sha256((issuer + "|" + subject).encode()).hexdigest()


def provision(issuer, subject, display_name, workspace_id, workspace_name, role):
    user_id = identity_id(issuer, subject)
    if role not in {"researcher", "editor", "owner"}:
        raise ValueError("Unsupported workspace role")
    if (
        not display_name.strip()
        or len(display_name) > 200
        or not workspace_name.strip()
        or len(workspace_name) > 200
    ):
        raise ValueError("Display and workspace names must contain 1–200 characters")
    if not workspace_id or len(workspace_id) > 36:
        raise ValueError("Workspace id must contain 1–36 characters")
    with SessionLocal.begin() as session:
        if session.bind.dialect.name != "postgresql":
            raise ValueError("Production identity provisioning requires PostgreSQL")
        privileged = session.scalar(
            text(
                "SELECT rolsuper OR rolbypassrls OR pg_has_role(current_user, (SELECT tableowner FROM pg_tables WHERE schemaname='public' AND tablename='cases'), 'MEMBER') FROM pg_roles WHERE rolname=current_user"
            )
        )
        if not privileged:
            raise ValueError(
                "Use a separately privileged maintenance identity; runtime credentials cannot bootstrap users"
            )
        workspace = session.get(Workspace, workspace_id)
        if workspace is None:
            session.add(Workspace(id=workspace_id, name=workspace_name))
            session.flush()
        if session.get(User, user_id) is None:
            session.add(User(id=user_id, name=display_name))
            session.flush()
        membership = session.get(Membership, (workspace_id, user_id))
        if membership is not None and membership.role != role:
            raise ValueError(
                "Membership already exists with another role; use audited membership administration"
            )
        if membership is None:
            session.add(Membership(workspace_id=workspace_id, user_id=user_id, role=role))
    return user_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--issuer", required=True, help="Exact iss from the verified identity-provider account"
    )
    parser.add_argument(
        "--subject", required=True, help="Verified OIDC sub; never supply an access token or secret"
    )
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--workspace-name", required=True)
    parser.add_argument("--role", choices=["owner", "editor", "researcher"], required=True)
    args = parser.parse_args()
    provision(args.issuer, args.subject, args.display_name, args.workspace_id, args.workspace_name, args.role)
    print("Verified-input identity membership provisioned. No credential or subject is printed.")
