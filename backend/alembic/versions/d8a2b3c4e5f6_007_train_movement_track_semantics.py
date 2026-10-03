"""007_train_movement_track_semantics

Revision ID: d8a2b3c4e5f6
Revises: c7f1a9b2e043
Create Date: 2026-10-03 23:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a2b3c4e5f6'
down_revision: Union[str, None] = 'c7f1a9b2e043'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable track_id foreign key column to train_movements
    op.add_column(
        'train_movements',
        sa.Column('track_id', sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        'fk_train_movements_track_id',
        'train_movements',
        'tracks',
        ['track_id'],
        ['track_id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_train_movements_track_id',
        'train_movements',
        ['track_id'],
        unique=False,
    )

    # 2. Deterministically seed sample track assignments on SCN-DEMO-001 train movements
    # MOV-12301-NDLS-09: UP Rajdhani arrival at NDLS -> TRK-NDLS-GZB-UP (UP_MAIN)
    # MOV-12302-NDLS-01: DN Rajdhani departure from NDLS -> TRK-NDLS-GZB-DN (DN_MAIN)
    # MOV-12301-CNB-08: UP Rajdhani stop at CNB -> TRK-ETW-CNB-UP (UP_MAIN)
    # MOV-12302-CNB-02: DN Rajdhani stop at CNB -> TRK-ETW-CNB-DN (DN_MAIN)
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE train_movements
            SET track_id = 'TRK-NDLS-GZB-UP'
            WHERE movement_id = 'MOV-12301-NDLS-09'
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE train_movements
            SET track_id = 'TRK-NDLS-GZB-DN'
            WHERE movement_id = 'MOV-12302-NDLS-01'
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE train_movements
            SET track_id = 'TRK-ETW-CNB-UP'
            WHERE movement_id = 'MOV-12301-CNB-08'
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE train_movements
            SET track_id = 'TRK-ETW-CNB-DN'
            WHERE movement_id = 'MOV-12302-CNB-02'
            """
        )
    )


def downgrade() -> None:
    op.drop_index('ix_train_movements_track_id', table_name='train_movements')
    op.drop_constraint('fk_train_movements_track_id', 'train_movements', type_='foreignkey')
    op.drop_column('train_movements', 'track_id')
