"""013_gov003_scenario_approved_unique_index

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-16 11:30:00.000000

GOV-003B Migration:
- Pre-flight check asserting at most one APPROVED plan version exists per scenario (fail closed on duplicate)
- Partial unique index on plan_versions (scenario_id) WHERE status = 'APPROVED'
- Prevents concurrent or race conditions from creating multiple active approved plan versions for the same scenario
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Pre-flight check: ensure no duplicate APPROVED plan versions exist for any scenario.
    # Fail closed with an explicit diagnostic error rather than silently deleting or modifying records.
    bind = op.get_bind()
    dup_query = sa.text("""
        SELECT scenario_id, COUNT(*) as cnt
        FROM plan_versions
        WHERE status = 'APPROVED'
        GROUP BY scenario_id
        HAVING COUNT(*) > 1
    """)
    duplicates = bind.execute(dup_query).fetchall()
    if duplicates:
        dup_details = ", ".join(f"scenario '{row[0]}' ({row[1]} approved versions)" for row in duplicates)
        raise ValueError(
            f"Cannot apply migration d4e5f6a7b8c9: Found duplicate APPROVED plan versions: {dup_details}. "
            f"Manual operational resolution required before creating partial unique index."
        )

    # 2. Create partial unique index on plan_versions (scenario_id) WHERE status = 'APPROVED'
    op.create_index(
        'uq_plan_versions_one_approved_per_scenario',
        'plan_versions',
        ['scenario_id'],
        unique=True,
        postgresql_where=sa.text("status = 'APPROVED'"),
    )


def downgrade() -> None:
    op.drop_index('uq_plan_versions_one_approved_per_scenario', table_name='plan_versions')
