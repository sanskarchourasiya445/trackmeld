"""005_tracks_schema

Revision ID: b4e6a8c1d302
Revises: 9c2d1e4f7a01
Create Date: 2026-10-03 22:30:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e6a8c1d302'
down_revision: Union[str, None] = '9c2d1e4f7a01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tracks table
    op.create_table(
        'tracks',
        sa.Column('track_id', sa.String(length=64), nullable=False),
        sa.Column('section_id', sa.String(length=64), nullable=False),
        sa.Column('track_code', sa.String(length=32), nullable=False),
        sa.Column('direction', sa.String(length=32), nullable=False),
        sa.Column('electrified', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('max_speed_kmh', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['section_id'], ['sections.section_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('track_id'),
        sa.UniqueConstraint('section_id', 'track_code', name='uq_tracks_section_track_code'),
        sa.CheckConstraint("direction IN ('UP', 'DOWN', 'BIDIRECTIONAL')", name='ck_tracks_direction_valid'),
    )
    op.create_index('ix_tracks_section_id', 'tracks', ['section_id'], unique=False)

    # 2. Add nullable track_id to maintenance_tasks
    op.add_column(
        'maintenance_tasks',
        sa.Column('track_id', sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        'fk_maintenance_tasks_track_id',
        'maintenance_tasks',
        'tracks',
        ['track_id'],
        ['track_id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_tasks_track_id', 'maintenance_tasks', ['track_id'], unique=False)

    # 3. Seed default tracks for existing sections
    connection = op.get_bind()
    sections = connection.execute(
        sa.text('SELECT section_id, section_code, track_count, electrified FROM sections')
    ).fetchall()

    now_iso = datetime.now(timezone.utc)
    track_rows = []
    for sec in sections:
        sec_id, sec_code, trk_cnt, electrified = sec
        if trk_cnt and trk_cnt >= 2:
            track_rows.append({
                'track_id': f'TRK-{sec_code}-UP',
                'section_id': sec_id,
                'track_code': 'UP_MAIN',
                'direction': 'UP',
                'electrified': bool(electrified),
                'max_speed_kmh': 130,
                'created_at': now_iso,
                'updated_at': now_iso,
            })
            track_rows.append({
                'track_id': f'TRK-{sec_code}-DN',
                'section_id': sec_id,
                'track_code': 'DN_MAIN',
                'direction': 'DOWN',
                'electrified': bool(electrified),
                'max_speed_kmh': 130,
                'created_at': now_iso,
                'updated_at': now_iso,
            })
        else:
            track_rows.append({
                'track_id': f'TRK-{sec_code}-SL',
                'section_id': sec_id,
                'track_code': 'SINGLE_LINE',
                'direction': 'BIDIRECTIONAL',
                'electrified': bool(electrified),
                'max_speed_kmh': 100,
                'created_at': now_iso,
                'updated_at': now_iso,
            })

    if track_rows:
        tracks_table = sa.table(
            'tracks',
            sa.column('track_id', sa.String),
            sa.column('section_id', sa.String),
            sa.column('track_code', sa.String),
            sa.column('direction', sa.String),
            sa.column('electrified', sa.Boolean),
            sa.column('max_speed_kmh', sa.Integer),
            sa.column('created_at', sa.DateTime),
            sa.column('updated_at', sa.DateTime),
        )
        op.bulk_insert(tracks_table, track_rows)


def downgrade() -> None:
    op.drop_index('ix_tasks_track_id', table_name='maintenance_tasks')
    op.drop_constraint('fk_maintenance_tasks_track_id', 'maintenance_tasks', type_='foreignkey')
    op.drop_column('maintenance_tasks', 'track_id')
    op.drop_index('ix_tracks_section_id', table_name='tracks')
    op.drop_table('tracks')
