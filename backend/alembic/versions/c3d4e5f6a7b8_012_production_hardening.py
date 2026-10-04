"""012_production_hardening

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-04 16:30:00.000000

Phase 20 Production Hardening Migration:
- Adds compound index on planning_runs (scenario_id, status, created_at) for fast history lookups
- Adds compound index on maintenance_tasks (track_id, window_start, window_end) for track-level contention queries
- Adds compound index on train_movements (train_id, station_id) for rapid route and traversal expansion lookups
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Compound index on planning_runs for scenario query with status filter & date sort
    op.create_index(
        'ix_planning_runs_scenario_status_created',
        'planning_runs',
        ['scenario_id', 'status', 'created_at'],
        unique=False,
    )

    # 2. Compound index on maintenance_tasks for track-specific temporal contention
    op.create_index(
        'ix_tasks_track_window',
        'maintenance_tasks',
        ['track_id', 'window_start', 'window_end'],
        unique=False,
    )

    # 3. Compound index on train_movements for rapid train-station traversal lookup
    op.create_index(
        'ix_movements_train_station',
        'train_movements',
        ['train_id', 'station_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_movements_train_station', table_name='train_movements')
    op.drop_index('ix_tasks_track_window', table_name='maintenance_tasks')
    op.drop_index('ix_planning_runs_scenario_status_created', table_name='planning_runs')
