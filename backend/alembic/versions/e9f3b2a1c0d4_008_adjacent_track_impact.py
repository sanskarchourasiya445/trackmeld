"""008_adjacent_track_impact

Revision ID: e9f3b2a1c0d4
Revises: d8a2b3c4e5f6
Create Date: 2026-10-04 00:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9f3b2a1c0d4'
down_revision: Union[str, None] = 'd8a2b3c4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable adjacent_track_impact column to maintenance_tasks
    op.add_column(
        'maintenance_tasks',
        sa.Column('adjacent_track_impact', sa.String(length=32), nullable=True),
    )

    # 2. Seed provisional adjacent-track impact for representative tasks
    # TSK-0001 (TRK-ETW-CNB-UP track tamping): CAUTION_ORDER on adjacent DN line
    # TSK-0002 (TRK-ARA-PNBE-DN heavy mechanized screening): FULL_TRAFFIC_BLOCK on adjacent UP line
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE maintenance_tasks
            SET adjacent_track_impact = 'CAUTION_ORDER'
            WHERE task_id = 'TSK-0001'
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE maintenance_tasks
            SET adjacent_track_impact = 'FULL_TRAFFIC_BLOCK'
            WHERE task_id = 'TSK-0002'
            """
        )
    )


def downgrade() -> None:
    op.drop_column('maintenance_tasks', 'adjacent_track_impact')
