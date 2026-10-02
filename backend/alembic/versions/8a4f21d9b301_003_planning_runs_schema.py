"""003_planning_runs_schema

Revision ID: 8a4f21d9b301
Revises: 538db451f99d
Create Date: 2026-10-02 21:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8a4f21d9b301'
down_revision: Union[str, None] = '538db451f99d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'planning_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('scenario_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('stage', sa.String(length=32), nullable=False),
        sa.Column('run_type', sa.String(length=32), nullable=False),
        sa.Column('scheduler_type', sa.String(length=32), nullable=False),
        sa.Column('scheduler_version', sa.String(length=32), nullable=False),
        sa.Column('planning_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planning_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('snapshot_id', sa.String(length=64), nullable=True),
        sa.Column('snapshot_hash', sa.String(length=64), nullable=True),
        sa.Column('input_hash', sa.String(length=64), nullable=True),
        sa.Column('configuration_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('priority_configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('optimization_configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('objective_configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('random_seed', sa.Integer(), nullable=False),
        sa.Column('solver_name', sa.String(length=64), nullable=False),
        sa.Column('solver_version', sa.String(length=32), nullable=False),
        sa.Column('dataset_version', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('validation_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_duration_ms', sa.Float(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('worker_id', sa.String(length=64), nullable=True),
        sa.Column('created_by', sa.String(length=64), nullable=False),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('schedule_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_status', sa.String(length=32), nullable=True),
        sa.Column('validation_fingerprint', sa.String(length=64), nullable=True),
        sa.Column('is_approvable', sa.Boolean(), nullable=False),
        sa.Column('validation_findings_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('diagnostics_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scenario_id'], ['operational_scenarios.scenario_id'], name=op.f('fk_planning_runs_scenario_id_operational_scenarios'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_planning_runs'))
    )
    op.create_index(op.f('ix_planning_runs_run_id'), 'planning_runs', ['run_id'], unique=True)
    op.create_index(op.f('ix_planning_runs_scenario_id'), 'planning_runs', ['scenario_id'], unique=False)
    op.create_index(op.f('ix_planning_runs_status'), 'planning_runs', ['status'], unique=False)
    op.create_index(op.f('ix_planning_runs_worker_id'), 'planning_runs', ['worker_id'], unique=False)
    op.create_index(op.f('ix_planning_runs_heartbeat_at'), 'planning_runs', ['heartbeat_at'], unique=False)
    op.create_index(op.f('ix_planning_runs_idempotency_key'), 'planning_runs', ['idempotency_key'], unique=True)
    op.create_index('ix_planning_runs_status_created', 'planning_runs', ['status', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_planning_runs_status_created', table_name='planning_runs')
    op.drop_index(op.f('ix_planning_runs_idempotency_key'), table_name='planning_runs')
    op.drop_index(op.f('ix_planning_runs_heartbeat_at'), table_name='planning_runs')
    op.drop_index(op.f('ix_planning_runs_worker_id'), table_name='planning_runs')
    op.drop_index(op.f('ix_planning_runs_status'), table_name='planning_runs')
    op.drop_index(op.f('ix_planning_runs_scenario_id'), table_name='planning_runs')
    op.drop_index(op.f('ix_planning_runs_run_id'), table_name='planning_runs')
    op.drop_table('planning_runs')
