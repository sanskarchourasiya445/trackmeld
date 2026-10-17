"""014_governance_audit_immutability

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-17 18:30:00.000000

P1 Audit Table Hardening:
- Creates PL/pgSQL trigger function to unconditionally deny UPDATE and DELETE on governance_audit_events
- Creates statement-level trigger function to unconditionally deny TRUNCATE on governance_audit_events
- Uses both primary key 'id' and business key 'event_id' in immutability exception messages
- Preserves INSERT and SELECT for operational workflows
- Conditionally applies least-privilege grants if unprivileged trackmeld_app role is provisioned
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Row-level trigger function: Unconditionally deny UPDATE and DELETE
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_prevent_governance_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                RAISE EXCEPTION 'GOV-AUDIT-IMMUTABLE: UPDATE operation denied on table governance_audit_events. Audit records are strictly immutable (id=%, event_id=%).', OLD.id, OLD.event_id
                    USING ERRCODE = 'restrict_violation';
            ELSIF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'GOV-AUDIT-IMMUTABLE: DELETE operation denied on table governance_audit_events. Audit records are append-only (id=%, event_id=%).', OLD.id, OLD.event_id
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 2. Statement-level trigger function: Unconditionally deny TRUNCATE
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_prevent_governance_audit_truncate()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'GOV-AUDIT-IMMUTABLE: TRUNCATE operation denied on table governance_audit_events. Audit table is append-only and cannot be truncated.'
                USING ERRCODE = 'restrict_violation';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 3. Attach row-level trigger to public.governance_audit_events
    op.execute("""
        DROP TRIGGER IF EXISTS trg_audit_events_no_update_delete ON public.governance_audit_events;
        CREATE TRIGGER trg_audit_events_no_update_delete
        BEFORE UPDATE OR DELETE ON public.governance_audit_events
        FOR EACH ROW
        EXECUTE FUNCTION trg_prevent_governance_audit_modification();
    """)

    # 4. Attach statement-level trigger to public.governance_audit_events
    op.execute("""
        DROP TRIGGER IF EXISTS trg_audit_events_no_truncate ON public.governance_audit_events;
        CREATE TRIGGER trg_audit_events_no_truncate
        BEFORE TRUNCATE ON public.governance_audit_events
        FOR EACH STATEMENT
        EXECUTE FUNCTION trg_prevent_governance_audit_truncate();
    """)

    # 5. Idempotent least-privilege grants for unprivileged runtime role (if provisioned)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'trackmeld_app') THEN
                GRANT SELECT, INSERT ON TABLE public.governance_audit_events TO trackmeld_app;
                GRANT USAGE, SELECT ON SEQUENCE public.governance_audit_events_id_seq TO trackmeld_app;
                REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.governance_audit_events FROM trackmeld_app;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_truncate ON public.governance_audit_events;")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_update_delete ON public.governance_audit_events;")
    op.execute("DROP FUNCTION IF EXISTS trg_prevent_governance_audit_truncate();")
    op.execute("DROP FUNCTION IF EXISTS trg_prevent_governance_audit_modification();")
