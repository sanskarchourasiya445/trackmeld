"""011_curated_demo_topology

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-04 14:00:00.000000

Curated DEMO_ONLY infrastructure topology connectivity fixture for Phase 16K.
Connects the NDLS -> GZB -> KRJ -> ALJN corridor across 3 contiguous block sections:
- SEC-NDLS-GZB (km 0.0 - 25.0)
- SEC-GZB-KRJ (km 25.0 - 95.0)
- SEC-KRJ-ALJN (km 95.0 - 126.0)

Nodes:
- NODE-GZB-THROAT (Ghaziabad Station Junction Throat, km 25.0)
- NODE-KRJ-THROAT (Khurja Junction Throat, km 95.0)

Connections:
- CONN-GZB-DN-THROUGH: CONTINUITY on DN_MAIN at GZB
- CONN-GZB-UP-THROUGH: CONTINUITY on UP_MAIN at GZB
- CONN-GZB-CROSSOVER-DN-UP: CROSSOVER from DN to UP line at GZB throat (30 km/h)
- CONN-KRJ-DN-THROUGH: CONTINUITY on DN_MAIN at KRJ
- CONN-KRJ-UP-THROUGH: CONTINUITY on UP_MAIN at KRJ

All records are explicitly marked classification = 'DEMO_ONLY'.
Zero existing endpoints, tracks, or sections are modified.
"""
from datetime import datetime, timezone
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CURATED_NODE_IDS = ['NODE-GZB-THROAT', 'NODE-KRJ-THROAT']
CURATED_CONN_IDS = [
    'CONN-GZB-DN-THROUGH',
    'CONN-GZB-UP-THROUGH',
    'CONN-GZB-CROSSOVER-DN-UP',
    'CONN-KRJ-DN-THROUGH',
    'CONN-KRJ-UP-THROUGH',
]


def upgrade() -> None:
    now_dt = datetime.now(timezone.utc)
    bind = op.get_bind()

    # 1. Insert curated DEMO_ONLY topology nodes
    node_table = sa.table(
        'topology_nodes',
        sa.column('node_id', sa.String),
        sa.column('node_name', sa.String),
        sa.column('station_id', sa.String),
        sa.column('node_type', sa.String),
        sa.column('classification', sa.String),
        sa.column('source_id', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    node_rows = [
        {
            'node_id': 'NODE-GZB-THROAT',
            'node_name': 'Ghaziabad Station Junction Throat',
            'station_id': 'STN-GZB',
            'node_type': 'STATION_THROAT',
            'classification': 'DEMO_ONLY',
            'source_id': 'SRC-TAG-2023-TBL-01',
            'created_at': now_dt,
            'updated_at': now_dt,
        },
        {
            'node_id': 'NODE-KRJ-THROAT',
            'node_name': 'Khurja Junction Throat',
            'station_id': 'STN-KRJ',
            'node_type': 'STATION_THROAT',
            'classification': 'DEMO_ONLY',
            'source_id': 'SRC-TAG-2023-TBL-01',
            'created_at': now_dt,
            'updated_at': now_dt,
        },
    ]
    op.bulk_insert(node_table, node_rows)

    # 2. Insert curated DEMO_ONLY topology connections
    conn_table = sa.table(
        'topology_connections',
        sa.column('connection_id', sa.String),
        sa.column('node_id', sa.String),
        sa.column('from_endpoint_id', sa.String),
        sa.column('to_endpoint_id', sa.String),
        sa.column('connection_type', sa.String),
        sa.column('traversal_direction', sa.String),
        sa.column('max_diverging_speed_kmh', sa.Integer),
        sa.column('classification', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    conn_rows = [
        # Ghaziabad DN Through Continuity: NDLS-GZB-DN (km 25.0 END) -> GZB-KRJ-DN (km 25.0 START)
        {
            'connection_id': 'CONN-GZB-DN-THROUGH',
            'node_id': 'NODE-GZB-THROAT',
            'from_endpoint_id': 'EP-TRK-NDLS-GZB-DN-END',
            'to_endpoint_id': 'EP-TRK-GZB-KRJ-DN-START',
            'connection_type': 'CONTINUITY',
            'traversal_direction': 'FORWARD',
            'max_diverging_speed_kmh': None,
            'classification': 'DEMO_ONLY',
            'created_at': now_dt,
            'updated_at': now_dt,
        },
        # Ghaziabad UP Through Continuity: GZB-KRJ-UP (km 25.0 START) -> NDLS-GZB-UP (km 25.0 END)
        {
            'connection_id': 'CONN-GZB-UP-THROUGH',
            'node_id': 'NODE-GZB-THROAT',
            'from_endpoint_id': 'EP-TRK-GZB-KRJ-UP-START',
            'to_endpoint_id': 'EP-TRK-NDLS-GZB-UP-END',
            'connection_type': 'CONTINUITY',
            'traversal_direction': 'FORWARD',
            'max_diverging_speed_kmh': None,
            'classification': 'DEMO_ONLY',
            'created_at': now_dt,
            'updated_at': now_dt,
        },
        # Ghaziabad Throat Crossover: NDLS-GZB-DN (km 25.0 END) -> GZB-KRJ-UP (km 25.0 START) with 30 km/h turnout speed
        {
            'connection_id': 'CONN-GZB-CROSSOVER-DN-UP',
            'node_id': 'NODE-GZB-THROAT',
            'from_endpoint_id': 'EP-TRK-NDLS-GZB-DN-END',
            'to_endpoint_id': 'EP-TRK-GZB-KRJ-UP-START',
            'connection_type': 'CROSSOVER',
            'traversal_direction': 'FORWARD',
            'max_diverging_speed_kmh': 30,
            'classification': 'DEMO_ONLY',
            'created_at': now_dt,
            'updated_at': now_dt,
        },
        # Khurja DN Through Continuity: GZB-KRJ-DN (km 95.0 END) -> KRJ-ALJN-DN (km 95.0 START)
        {
            'connection_id': 'CONN-KRJ-DN-THROUGH',
            'node_id': 'NODE-KRJ-THROAT',
            'from_endpoint_id': 'EP-TRK-GZB-KRJ-DN-END',
            'to_endpoint_id': 'EP-TRK-KRJ-ALJN-DN-START',
            'connection_type': 'CONTINUITY',
            'traversal_direction': 'FORWARD',
            'max_diverging_speed_kmh': None,
            'classification': 'DEMO_ONLY',
            'created_at': now_dt,
            'updated_at': now_dt,
        },
        # Khurja UP Through Continuity: KRJ-ALJN-UP (km 95.0 START) -> GZB-KRJ-UP (km 95.0 END)
        {
            'connection_id': 'CONN-KRJ-UP-THROUGH',
            'node_id': 'NODE-KRJ-THROAT',
            'from_endpoint_id': 'EP-TRK-KRJ-ALJN-UP-START',
            'to_endpoint_id': 'EP-TRK-GZB-KRJ-UP-END',
            'connection_type': 'CONTINUITY',
            'traversal_direction': 'FORWARD',
            'max_diverging_speed_kmh': None,
            'classification': 'DEMO_ONLY',
            'created_at': now_dt,
            'updated_at': now_dt,
        },
    ]
    op.bulk_insert(conn_table, conn_rows)


def downgrade() -> None:
    bind = op.get_bind()
    # Explicitly remove only the curated fixture records
    conn_list_str = "', '".join(CURATED_CONN_IDS)
    node_list_str = "', '".join(CURATED_NODE_IDS)
    bind.execute(sa.text(f"DELETE FROM topology_connections WHERE connection_id IN ('{conn_list_str}')"))
    bind.execute(sa.text(f"DELETE FROM topology_nodes WHERE node_id IN ('{node_list_str}')"))
