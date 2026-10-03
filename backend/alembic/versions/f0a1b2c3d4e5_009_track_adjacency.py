"""009_track_adjacency

Revision ID: f0a1b2c3d4e5
Revises: e9f3b2a1c0d4
Create Date: 2026-10-04 01:15:00.000000

"""
import json
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from collections import defaultdict


# revision identifiers, used by Alembic.
revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = 'e9f3b2a1c0d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable adjacent_track_ids JSON column to tracks
    op.add_column(
        'tracks',
        sa.Column('adjacent_track_ids', sa.JSON(), nullable=True),
    )

    # 2. Seed explicit track adjacency for existing paired double-line tracks
    connection = op.get_bind()
    rows = connection.execute(
        sa.text('SELECT track_id, section_id, track_code FROM tracks')
    ).fetchall()

    by_section = defaultdict(list)
    for row in rows:
        t_id, s_id, t_code = row
        by_section[s_id].append((t_id, t_code))

    for s_id, t_list in by_section.items():
        if len(t_list) == 2:
            t1_id, t1_code = t_list[0]
            t2_id, t2_code = t_list[1]
            # Mutually adjacent double-line tracks
            connection.execute(
                sa.text(
                    "UPDATE tracks SET adjacent_track_ids = :adj WHERE track_id = :t_id"
                ),
                {"adj": json.dumps([t2_id]), "t_id": t1_id},
            )
            connection.execute(
                sa.text(
                    "UPDATE tracks SET adjacent_track_ids = :adj WHERE track_id = :t_id"
                ),
                {"adj": json.dumps([t1_id]), "t_id": t2_id},
            )
        elif len(t_list) == 1:
            # Single line: explicitly isolated with zero adjacent running lines
            t_id, _ = t_list[0]
            connection.execute(
                sa.text(
                    "UPDATE tracks SET adjacent_track_ids = :adj WHERE track_id = :t_id"
                ),
                {"adj": json.dumps([]), "t_id": t_id},
            )


def downgrade() -> None:
    op.drop_column('tracks', 'adjacent_track_ids')
