"""006_task_spatial_semantics

Revision ID: c7f1a9b2e043
Revises: b4e6a8c1d302
Create Date: 2026-10-03 23:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f1a9b2e043'
down_revision: Union[str, None] = 'b4e6a8c1d302'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add from_km and to_km nullable float columns to maintenance_tasks
    op.add_column(
        'maintenance_tasks',
        sa.Column('from_km', sa.Float(), nullable=True),
    )
    op.add_column(
        'maintenance_tasks',
        sa.Column('to_km', sa.Float(), nullable=True),
    )

    # 2. Add spatial check constraints
    op.create_check_constraint(
        'ck_tasks_chainage_range',
        'maintenance_tasks',
        'from_km IS NULL OR to_km IS NULL OR from_km <= to_km',
    )
    op.create_check_constraint(
        'ck_tasks_from_km_non_negative',
        'maintenance_tasks',
        'from_km IS NULL OR from_km >= 0',
    )
    op.create_check_constraint(
        'ck_tasks_to_km_non_negative',
        'maintenance_tasks',
        'to_km IS NULL OR to_km >= 0',
    )
    op.create_check_constraint(
        'ck_tasks_track_required_for_chainage',
        'maintenance_tasks',
        'track_id IS NOT NULL OR (from_km IS NULL AND to_km IS NULL)',
    )

    # 3. Deterministically seed sample track spatial assignments for SCN-DEMO-001
    # TSK-0001 (SEC-ETW-CNB): assign UP_MAIN track with no chainage
    # TSK-0002 (SEC-ARA-PNBE): assign DN_MAIN track with 12.4–15.8 km range
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE maintenance_tasks
            SET track_id = 'TRK-ETW-CNB-UP', from_km = NULL, to_km = NULL
            WHERE task_id = 'TSK-0001'
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE maintenance_tasks
            SET track_id = 'TRK-ARA-PNBE-DN', from_km = 12.4, to_km = 15.8
            WHERE task_id = 'TSK-0002'
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint('ck_tasks_track_required_for_chainage', 'maintenance_tasks', type_='check')
    op.drop_constraint('ck_tasks_to_km_non_negative', 'maintenance_tasks', type_='check')
    op.drop_constraint('ck_tasks_from_km_non_negative', 'maintenance_tasks', type_='check')
    op.drop_constraint('ck_tasks_chainage_range', 'maintenance_tasks', type_='check')
    op.drop_column('maintenance_tasks', 'to_km')
    op.drop_column('maintenance_tasks', 'from_km')
