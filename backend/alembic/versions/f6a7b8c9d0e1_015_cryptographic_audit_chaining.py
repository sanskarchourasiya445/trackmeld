"""015_cryptographic_audit_chaining

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-17 18:45:00.000000

P1 Cryptographic Audit Chaining:
- Creates audit_chain_head singleton table for serialized chain head tracking
- Adds sequence_number, previous_event_hash, and event_hash to governance_audit_events
- Backfills existing historical audit records with deterministic SHA-256 hash chain without rewriting event content
- Applies NOT NULL constraints, unique index on sequence_number, and indexes on hashes
"""
from datetime import datetime, timezone
import hashlib
import json
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GENESIS_HASH = "0" * 64


def _canonicalize_row(row_dict: dict, previous_event_hash: str, sequence_number: int) -> bytes:
    ts = row_dict.get("timestamp")
    if ts is not None:
        if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
            ts_utc = ts.astimezone(timezone.utc)
        else:
            ts_utc = ts.replace(tzinfo=timezone.utc)
        ts_str = ts_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        ts_str = ""

    meta = row_dict.get("event_metadata")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    elif not isinstance(meta, dict):
        meta = {} if meta is None else dict(meta)

    canonical = {
        "actor_id": str(row_dict.get("actor_id") or ""),
        "actor_role": str(row_dict.get("actor_role") or ""),
        "actor_username": str(row_dict.get("actor_username") or ""),
        "comment": str(row_dict.get("comment") or ""),
        "entity_id": str(row_dict.get("entity_id") or ""),
        "entity_type": str(row_dict.get("entity_type") or ""),
        "event_id": str(row_dict.get("event_id") or ""),
        "event_metadata": meta,
        "event_type": str(row_dict.get("event_type") or ""),
        "input_hash": str(row_dict.get("input_hash") or ""),
        "new_state": str(row_dict.get("new_state") or ""),
        "previous_event_hash": str(previous_event_hash),
        "previous_state": str(row_dict.get("previous_state") or ""),
        "reason": str(row_dict.get("reason") or ""),
        "schedule_identity": str(row_dict.get("schedule_identity") or ""),
        "sequence_number": int(sequence_number),
        "snapshot_hash": str(row_dict.get("snapshot_hash") or ""),
        "timestamp": ts_str,
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")


def upgrade() -> None:
    # 1. Create audit_chain_head table
    op.create_table(
        'audit_chain_head',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('last_sequence_number', sa.BigInteger(), nullable=False),
        sa.Column('last_event_hash', sa.String(length=64), nullable=False),
        sa.Column('last_event_id', sa.String(length=64), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_chain_head')),
    )

    # 2. Add chaining columns as nullable initially for backfill
    op.add_column('governance_audit_events', sa.Column('sequence_number', sa.BigInteger(), nullable=True))
    op.add_column('governance_audit_events', sa.Column('previous_event_hash', sa.String(length=64), nullable=True))
    op.add_column('governance_audit_events', sa.Column('event_hash', sa.String(length=64), nullable=True))

    bind = op.get_bind()

    # 3. Disable update trigger temporarily to permit migration backfill
    bind.execute(sa.text("ALTER TABLE public.governance_audit_events DISABLE TRIGGER trg_audit_events_no_update_delete;"))

    # Fetch all existing rows ordered chronologically by id
    select_sql = sa.text("""
        SELECT id, event_id, entity_type, entity_id, event_type, actor_id, actor_username, actor_role,
               timestamp, previous_state, new_state, reason, comment, schedule_identity,
               snapshot_hash, input_hash, event_metadata
        FROM public.governance_audit_events
        ORDER BY id ASC;
    """)
    rows = bind.execute(select_sql).fetchall()

    last_seq = 0
    last_hash = GENESIS_HASH
    last_id = "GENESIS"
    now_utc = datetime.now(timezone.utc)

    update_sql = sa.text("""
        UPDATE public.governance_audit_events
        SET sequence_number = :seq,
            previous_event_hash = :prev_hash,
            event_hash = :ev_hash
        WHERE id = :id;
    """)

    for idx, r in enumerate(rows):
        seq = idx + 1
        prev = GENESIS_HASH if seq == 1 else last_hash
        row_dict = {
            "id": r[0],
            "event_id": r[1],
            "entity_type": r[2],
            "entity_id": r[3],
            "event_type": r[4],
            "actor_id": r[5],
            "actor_username": r[6],
            "actor_role": r[7],
            "timestamp": r[8],
            "previous_state": r[9],
            "new_state": r[10],
            "reason": r[11],
            "comment": r[12],
            "schedule_identity": r[13],
            "snapshot_hash": r[14],
            "input_hash": r[15],
            "event_metadata": r[16],
        }
        canonical_bytes = _canonicalize_row(row_dict, previous_event_hash=prev, sequence_number=seq)
        ev_hash = hashlib.sha256(canonical_bytes).hexdigest()

        bind.execute(update_sql, {"seq": seq, "prev_hash": prev, "ev_hash": ev_hash, "id": r[0]})
        last_seq = seq
        last_hash = ev_hash
        last_id = r[1]
        if r[8] is not None:
            now_utc = r[8] if hasattr(r[8], "tzinfo") and r[8].tzinfo else r[8].replace(tzinfo=timezone.utc)

    # Initialize audit_chain_head anchor
    insert_head_sql = sa.text("""
        INSERT INTO public.audit_chain_head (id, last_sequence_number, last_event_hash, last_event_id, updated_at)
        VALUES (1, :seq, :hash, :event_id, :updated_at);
    """)
    bind.execute(insert_head_sql, {
        "seq": last_seq,
        "hash": last_hash,
        "event_id": last_id,
        "updated_at": now_utc,
    })

    # 4. Re-enable immutability trigger
    bind.execute(sa.text("ALTER TABLE public.governance_audit_events ENABLE TRIGGER trg_audit_events_no_update_delete;"))

    # 5. Enforce NOT NULL constraints on newly backfilled columns
    op.alter_column('governance_audit_events', 'sequence_number', nullable=False)
    op.alter_column('governance_audit_events', 'previous_event_hash', nullable=False)
    op.alter_column('governance_audit_events', 'event_hash', nullable=False)

    # 6. Create unique and lookup indexes
    op.create_index('uq_audit_events_sequence_number', 'governance_audit_events', ['sequence_number'], unique=True)
    op.create_index('ix_audit_events_event_hash', 'governance_audit_events', ['event_hash'], unique=False)
    op.create_index('ix_audit_events_previous_event_hash', 'governance_audit_events', ['previous_event_hash'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_audit_events_previous_event_hash', table_name='governance_audit_events')
    op.drop_index('ix_audit_events_event_hash', table_name='governance_audit_events')
    op.drop_index('uq_audit_events_sequence_number', table_name='governance_audit_events')
    op.drop_column('governance_audit_events', 'event_hash')
    op.drop_column('governance_audit_events', 'previous_event_hash')
    op.drop_column('governance_audit_events', 'sequence_number')
    op.drop_table('audit_chain_head')
