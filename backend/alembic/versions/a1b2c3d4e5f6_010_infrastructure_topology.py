"""010_infrastructure_topology

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-10-04 01:45:00.000000

"""
from datetime import datetime, timezone
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create topology_nodes table
    op.create_table(
        'topology_nodes',
        sa.Column('node_id', sa.String(length=64), primary_key=True),
        sa.Column('node_name', sa.String(length=128), nullable=False),
        sa.Column('station_id', sa.String(length=32), sa.ForeignKey('stations.station_id', ondelete='SET NULL'), nullable=True),
        sa.Column('node_type', sa.String(length=32), nullable=False),
        sa.Column('classification', sa.String(length=32), server_default='DEMO_ONLY', nullable=False),
        sa.Column('source_id', sa.String(length=64), sa.ForeignKey('source_documents.source_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "node_type IN ('BOUNDARY_JOINT', 'STATION_THROAT', 'CROSSOVER_JUNCTION')",
            name='ck_topology_nodes_type_valid',
        ),
    )
    op.create_index('ix_topology_nodes_station_id', 'topology_nodes', ['station_id'], unique=False)

    # 2. Create track_endpoints table
    op.create_table(
        'track_endpoints',
        sa.Column('endpoint_id', sa.String(length=64), primary_key=True),
        sa.Column('track_id', sa.String(length=64), sa.ForeignKey('tracks.track_id', ondelete='CASCADE'), nullable=False),
        sa.Column('endpoint_type', sa.String(length=16), nullable=False),
        sa.Column('kilometrage', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('track_id', 'endpoint_type', name='uq_track_endpoints_track_type'),
        sa.CheckConstraint("endpoint_type IN ('START', 'END')", name='ck_track_endpoints_type_valid'),
    )
    op.create_index('ix_track_endpoints_track_id', 'track_endpoints', ['track_id'], unique=False)

    # 3. Create topology_connections table
    op.create_table(
        'topology_connections',
        sa.Column('connection_id', sa.String(length=64), primary_key=True),
        sa.Column('node_id', sa.String(length=64), sa.ForeignKey('topology_nodes.node_id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_endpoint_id', sa.String(length=64), sa.ForeignKey('track_endpoints.endpoint_id', ondelete='CASCADE'), nullable=False),
        sa.Column('to_endpoint_id', sa.String(length=64), sa.ForeignKey('track_endpoints.endpoint_id', ondelete='CASCADE'), nullable=False),
        sa.Column('connection_type', sa.String(length=32), nullable=False),
        sa.Column('traversal_direction', sa.String(length=32), server_default='FORWARD', nullable=False),
        sa.Column('max_diverging_speed_kmh', sa.Integer(), nullable=True),
        sa.Column('classification', sa.String(length=32), server_default='DEMO_ONLY', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('from_endpoint_id', 'to_endpoint_id', name='uq_topology_connections_endpoints'),
        sa.CheckConstraint('from_endpoint_id != to_endpoint_id', name='ck_topology_connections_distinct_endpoints'),
        sa.CheckConstraint(
            "connection_type IN ('CONTINUITY', 'TURNOUT_NORMAL', 'TURNOUT_REVERSE', 'CROSSOVER')",
            name='ck_topology_connections_type_valid',
        ),
        sa.CheckConstraint(
            "traversal_direction IN ('FORWARD', 'REVERSE', 'BIDIRECTIONAL')",
            name='ck_topology_connections_direction_valid',
        ),
    )
    op.create_index('ix_topology_connections_node_id', 'topology_connections', ['node_id'], unique=False)
    op.create_index('ix_topology_connections_from_ep', 'topology_connections', ['from_endpoint_id'], unique=False)
    op.create_index('ix_topology_connections_to_ep', 'topology_connections', ['to_endpoint_id'], unique=False)

    # 4. Deterministically seed START and END endpoints for all existing tracks
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("""
            SELECT t.track_id, s.kilometrage_start, s.kilometrage_end
            FROM tracks t
            JOIN sections s ON t.section_id = s.section_id
        """)
    ).fetchall()

    now_dt = datetime.now(timezone.utc)
    endpoint_rows = []
    for r in rows:
        track_id, km_start, km_end = r
        endpoint_rows.append({
            'endpoint_id': f'EP-{track_id}-START',
            'track_id': track_id,
            'endpoint_type': 'START',
            'kilometrage': float(km_start if km_start is not None else 0.0),
            'created_at': now_dt,
            'updated_at': now_dt,
        })
        endpoint_rows.append({
            'endpoint_id': f'EP-{track_id}-END',
            'track_id': track_id,
            'endpoint_type': 'END',
            'kilometrage': float(km_end if km_end is not None else 0.0),
            'created_at': now_dt,
            'updated_at': now_dt,
        })

    if endpoint_rows:
        ep_table = sa.table(
            'track_endpoints',
            sa.column('endpoint_id', sa.String),
            sa.column('track_id', sa.String),
            sa.column('endpoint_type', sa.String),
            sa.column('kilometrage', sa.Float),
            sa.column('created_at', sa.DateTime),
            sa.column('updated_at', sa.DateTime),
        )
        op.bulk_insert(ep_table, endpoint_rows)


def downgrade() -> None:
    op.drop_table('topology_connections')
    op.drop_table('track_endpoints')
    op.drop_table('topology_nodes')
