"""Bounded due-run enumeration for a tenant-scoped worker.

Revision ID: 003_worker_dispatch
Revises: 002_tenant_policies
"""

from alembic import op

revision = "003_worker_dispatch"
down_revision = "002_tenant_policies"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""
        CREATE FUNCTION public.factledger_due_runs()
        RETURNS TABLE(run_id varchar, workspace_id varchar)
        LANGUAGE sql SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
            SELECT r.id, r.workspace_id
            FROM public.runs AS r
            WHERE r.state IN ('QUEUED', 'RUNNING', 'PAUSE_REQUESTED', 'CANCEL_REQUESTED')
              AND (r.lease_expires_at IS NULL OR r.lease_expires_at < CURRENT_TIMESTAMP)
            ORDER BY r.created_at, r.id
            LIMIT 10
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.factledger_due_runs() FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.factledger_due_runs() TO evidence_app")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION public.factledger_due_runs()")
