"""Tenant row policies and a non-owner production application role.

Revision ID: 002_tenant_policies
Revises: 7907130e2424
"""

from alembic import op

revision = "002_tenant_policies"
down_revision = "7907130e2424"
branch_labels = None
depends_on = None
TENANT_TABLES = (
    "cases",
    "revisions",
    "plans",
    "runs",
    "run_events",
    "sources",
    "evidence",
    "review_requests",
    "exports",
    "idempotency",
    "audit",
)


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'evidence_app') THEN CREATE ROLE evidence_app NOLOGIN NOSUPERUSER NOBYPASSRLS; END IF; END $$"
    )
    op.execute("GRANT USAGE ON SCHEMA public TO evidence_app")
    op.execute("REVOKE ALL ON TABLE alembic_version FROM evidence_app")
    for table in (*TENANT_TABLES, "workspaces", "users", "memberships"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO evidence_app")
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_scope ON {table} TO evidence_app USING (workspace_id = nullif(current_setting('app.workspace_id', true), '')) WITH CHECK (workspace_id = nullif(current_setting('app.workspace_id', true), ''))"
        )


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_scope ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    # Keep role: externally provisioned login roles may depend on its grants.
