"""004_plan_versions_and_audit

Revision ID: 9c2d1e4f7a01
Revises: 8a4f21d9b301
Create Date: 2026-10-02 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c2d1e4f7a01'
down_revision: Union[str, None] = '8a4f21d9b301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create plan_versions table
    op.create_table(
        'plan_versions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plan_version_id', sa.String(length=64), nullable=False),
        sa.Column('scenario_id', sa.String(length=64), nullable=False),
        sa.Column('planning_run_id', sa.String(length=64), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('schedule_identity', sa.String(length=64), nullable=False),
        sa.Column('snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('schedule_result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('result_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('validation_status', sa.String(length=32), nullable=False),
        sa.Column('is_approvable', sa.Boolean(), nullable=False),
        sa.Column('validation_findings_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('diagnostics_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('scheduler_type', sa.String(length=32), nullable=False),
        sa.Column('scheduler_version', sa.String(length=32), nullable=False),
        sa.Column('solver_name', sa.String(length=64), nullable=False),
        sa.Column('solver_version', sa.String(length=32), nullable=False),
        sa.Column('dataset_version', sa.String(length=32), nullable=False),
        sa.Column('configuration_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('priority_configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('optimization_configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.String(length=64), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(length=64), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by', sa.String(length=64), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('previous_plan_version_id', sa.String(length=64), nullable=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by', sa.String(length=64), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scenario_id'], ['operational_scenarios.scenario_id'], name=op.f('fk_plan_versions_scenario_id_operational_scenarios'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['planning_run_id'], ['planning_runs.run_id'], name=op.f('fk_plan_versions_planning_run_id_planning_runs'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_plan_versions')),
        sa.UniqueConstraint('scenario_id', 'version_number', name='uq_plan_versions_scenario_version'),
        sa.UniqueConstraint('planning_run_id', name='uq_plan_versions_planning_run'),
    )
    op.create_index(op.f('ix_plan_versions_plan_version_id'), 'plan_versions', ['plan_version_id'], unique=True)
    op.create_index(op.f('ix_plan_versions_scenario_id'), 'plan_versions', ['scenario_id'], unique=False)
    op.create_index(op.f('ix_plan_versions_status'), 'plan_versions', ['status'], unique=False)
    op.create_index('ix_plan_versions_scenario_status', 'plan_versions', ['scenario_id', 'status'], unique=False)
    op.create_index('ix_plan_versions_created_at', 'plan_versions', ['created_at'], unique=False)
    op.create_index('ix_plan_versions_approved_at', 'plan_versions', ['approved_at'], unique=False)

    # 2. Create plan_review_comments table
    op.create_table(
        'plan_review_comments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('review_id', sa.String(length=64), nullable=False),
        sa.Column('plan_version_id', sa.String(length=64), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('actor_username', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=32), nullable=False),
        sa.Column('comment', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['plan_version_id'], ['plan_versions.plan_version_id'], name=op.f('fk_plan_review_comments_plan_version_id_plan_versions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_plan_review_comments'))
    )
    op.create_index(op.f('ix_plan_review_comments_review_id'), 'plan_review_comments', ['review_id'], unique=True)
    op.create_index(op.f('ix_plan_review_comments_plan_version_id'), 'plan_review_comments', ['plan_version_id'], unique=False)

    # 3. Create governance_audit_events table
    op.create_table(
        'governance_audit_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=32), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('actor_username', sa.String(length=64), nullable=False),
        sa.Column('actor_role', sa.String(length=32), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('previous_state', sa.String(length=32), nullable=True),
        sa.Column('new_state', sa.String(length=32), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('schedule_identity', sa.String(length=64), nullable=True),
        sa.Column('snapshot_hash', sa.String(length=64), nullable=True),
        sa.Column('input_hash', sa.String(length=64), nullable=True),
        sa.Column('event_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_governance_audit_events'))
    )
    op.create_index(op.f('ix_governance_audit_events_event_id'), 'governance_audit_events', ['event_id'], unique=True)
    op.create_index('ix_audit_events_entity', 'governance_audit_events', ['entity_type', 'entity_id'], unique=False)
    op.create_index('ix_audit_events_actor', 'governance_audit_events', ['actor_id'], unique=False)
    op.create_index('ix_audit_events_timestamp', 'governance_audit_events', ['timestamp'], unique=False)
    op.create_index('ix_audit_events_type', 'governance_audit_events', ['event_type'], unique=False)


def downgrade() -> None:
    op.drop_table('governance_audit_events')
    op.drop_table('plan_review_comments')
    op.drop_table('plan_versions')
