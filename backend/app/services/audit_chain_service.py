"""TrackMeld Cryptographic Audit Chaining Service.

Provides deterministic event canonicalization, SHA-256 hash chaining,
atomic append serialization with row-level locking on audit_chain_head,
and full-chain verification with granular inconsistency detection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.plan_version import GovernanceAuditEventModel, AuditChainHeadModel

GENESIS_HASH = "0" * 64


def canonical_iso_timestamp(dt: Any) -> str:
    """Normalize any timestamp representation to strict UTC ISO-8601 with microsecond precision."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        # Parse into datetime if string
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        dt_utc = dt.astimezone(timezone.utc)
    else:
        dt_utc = dt.replace(tzinfo=timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canonicalize_audit_event(
    event: Any,
    previous_event_hash: str,
    sequence_number: int,
) -> bytes:
    """Produce deterministic UTF-8 byte payload for cryptographic hashing.

    All keys are sorted lexicographically with compact separators.
    """
    metadata = getattr(event, "event_metadata", None)
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}
    elif not isinstance(metadata, dict):
        metadata = {} if metadata is None else dict(metadata)

    canonical_payload: Dict[str, Any] = {
        "actor_id": str(getattr(event, "actor_id", "") or ""),
        "actor_role": str(getattr(event, "actor_role", "") or ""),
        "actor_username": str(getattr(event, "actor_username", "") or ""),
        "comment": str(getattr(event, "comment", "") or ""),
        "entity_id": str(getattr(event, "entity_id", "") or ""),
        "entity_type": str(getattr(event, "entity_type", "") or ""),
        "event_id": str(getattr(event, "event_id", "") or ""),
        "event_metadata": metadata,
        "event_type": str(getattr(event, "event_type", "") or ""),
        "input_hash": str(getattr(event, "input_hash", "") or ""),
        "new_state": str(getattr(event, "new_state", "") or ""),
        "previous_event_hash": str(previous_event_hash),
        "previous_state": str(getattr(event, "previous_state", "") or ""),
        "reason": str(getattr(event, "reason", "") or ""),
        "schedule_identity": str(getattr(event, "schedule_identity", "") or ""),
        "sequence_number": int(sequence_number),
        "snapshot_hash": str(getattr(event, "snapshot_hash", "") or ""),
        "timestamp": canonical_iso_timestamp(getattr(event, "timestamp", None)),
    }
    return json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_audit_event_hash(
    event: Any,
    previous_event_hash: str,
    sequence_number: int,
) -> str:
    """Compute authoritative 64-char lowercase SHA-256 fingerprint for a chained audit event."""
    canonical_bytes = canonicalize_audit_event(
        event=event,
        previous_event_hash=previous_event_hash,
        sequence_number=sequence_number,
    )
    return hashlib.sha256(canonical_bytes).hexdigest()


async def append_chained_audit_event(
    session: AsyncSession,
    event: GovernanceAuditEventModel,
) -> GovernanceAuditEventModel:
    """Atomically append a cryptographically chained audit event under row lock.

    1. Locks the single-row audit_chain_head anchor FOR UPDATE.
    2. Derives sequence_number and previous_event_hash from the committed tip.
    3. Computes event_hash over canonical event payload.
    4. Updates audit_chain_head and adds event to session.
    5. Guarantees zero forks, zero race conditions, and complete transaction rollback safety.
    """
    head_stmt = (
        select(AuditChainHeadModel)
        .where(AuditChainHeadModel.id == 1)
        .with_for_update()
    )
    res = await session.execute(head_stmt)
    head = res.scalar_one_or_none()

    if head is None:
        # Initialize head if missing
        head = AuditChainHeadModel(
            id=1,
            last_sequence_number=0,
            last_event_hash=GENESIS_HASH,
            last_event_id="GENESIS",
            updated_at=datetime.now(timezone.utc),
        )
        session.add(head)
        await session.flush()

    next_sequence = head.last_sequence_number + 1
    prev_hash = head.last_event_hash

    event.sequence_number = next_sequence
    event.previous_event_hash = prev_hash
    event.event_hash = compute_audit_event_hash(
        event=event,
        previous_event_hash=prev_hash,
        sequence_number=next_sequence,
    )

    # Advance the chain head
    head.last_sequence_number = next_sequence
    head.last_event_hash = event.event_hash
    head.last_event_id = event.event_id
    head.updated_at = event.timestamp if event.timestamp else datetime.now(timezone.utc)

    session.add(event)
    await session.flush()
    return event


@dataclass
class AuditChainVerificationReport:
    """Report detailing cryptographic chain integrity and any detected inconsistencies."""
    is_valid: bool
    total_events: int
    head_sequence_number: int
    head_event_hash: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    first_inconsistent_id: Optional[int] = None
    first_inconsistent_event_id: Optional[str] = None
    first_inconsistent_sequence: Optional[int] = None
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None


class AuditChainVerifier:
    """Independent verification engine for TrackMeld cryptographic audit chain."""

    @classmethod
    def verify_events(
        cls,
        events: Sequence[Any],
        head_sequence_number: Optional[int] = None,
        head_event_hash: Optional[str] = None,
    ) -> AuditChainVerificationReport:
        """Verify the cryptographic integrity of an ordered sequence of audit events."""
        if not events:
            if head_sequence_number is not None and head_sequence_number != 0:
                return AuditChainVerificationReport(
                    is_valid=False,
                    total_events=0,
                    head_sequence_number=head_sequence_number,
                    head_event_hash=head_event_hash or "",
                    error_code="HEAD_MISMATCH",
                    error_message=f"Empty audit events but head sequence is {head_sequence_number}.",
                )
            return AuditChainVerificationReport(
                is_valid=True,
                total_events=0,
                head_sequence_number=0,
                head_event_hash=GENESIS_HASH,
            )

        expected_prev_hash = GENESIS_HASH
        expected_seq = 1

        for idx, ev in enumerate(events):
            # 1. Sequence number continuity
            if ev.sequence_number != expected_seq:
                return AuditChainVerificationReport(
                    is_valid=False,
                    total_events=len(events),
                    head_sequence_number=head_sequence_number if head_sequence_number is not None else 0,
                    head_event_hash=head_event_hash or "",
                    error_code="SEQUENCE_GAP",
                    error_message=f"Sequence discontinuity at row id={getattr(ev, 'id', None)}: expected sequence {expected_seq}, found {ev.sequence_number}.",
                    first_inconsistent_id=getattr(ev, "id", None),
                    first_inconsistent_event_id=getattr(ev, "event_id", None),
                    first_inconsistent_sequence=ev.sequence_number,
                )

            # 2. Previous hash link validation
            if ev.previous_event_hash != expected_prev_hash:
                return AuditChainVerificationReport(
                    is_valid=False,
                    total_events=len(events),
                    head_sequence_number=head_sequence_number if head_sequence_number is not None else 0,
                    head_event_hash=head_event_hash or "",
                    error_code="BROKEN_LINK",
                    error_message=f"Broken previous-hash pointer at row id={getattr(ev, 'id', None)} (event '{getattr(ev, 'event_id', None)}', seq {ev.sequence_number}): expected '{expected_prev_hash}', found '{ev.previous_event_hash}'.",
                    first_inconsistent_id=getattr(ev, "id", None),
                    first_inconsistent_event_id=getattr(ev, "event_id", None),
                    first_inconsistent_sequence=ev.sequence_number,
                    expected_hash=expected_prev_hash,
                    actual_hash=ev.previous_event_hash,
                )

            # 3. Payload cryptographic hash validation
            computed_hash = compute_audit_event_hash(
                event=ev,
                previous_event_hash=ev.previous_event_hash,
                sequence_number=ev.sequence_number,
            )
            if computed_hash != ev.event_hash:
                return AuditChainVerificationReport(
                    is_valid=False,
                    total_events=len(events),
                    head_sequence_number=head_sequence_number if head_sequence_number is not None else 0,
                    head_event_hash=head_event_hash or "",
                    error_code="HASH_MISMATCH",
                    error_message=f"Payload tamper or hash mismatch at row id={getattr(ev, 'id', None)} (event '{getattr(ev, 'event_id', None)}', seq {ev.sequence_number}): recomputed '{computed_hash}', stored '{ev.event_hash}'.",
                    first_inconsistent_id=getattr(ev, "id", None),
                    first_inconsistent_event_id=getattr(ev, "event_id", None),
                    first_inconsistent_sequence=ev.sequence_number,
                    expected_hash=computed_hash,
                    actual_hash=ev.event_hash,
                )

            expected_prev_hash = ev.event_hash
            expected_seq += 1

        # 4. Chain head alignment check
        if head_sequence_number is None or head_event_hash is None:
            return AuditChainVerificationReport(
                is_valid=False,
                total_events=len(events),
                head_sequence_number=0,
                head_event_hash="",
                error_code="HEAD_MISSING",
                error_message="audit_chain_head record is missing.",
            )

        last_ev = events[-1]
        if head_sequence_number != last_ev.sequence_number or head_event_hash != last_ev.event_hash:
            return AuditChainVerificationReport(
                is_valid=False,
                total_events=len(events),
                head_sequence_number=head_sequence_number,
                head_event_hash=head_event_hash,
                error_code="HEAD_MISMATCH",
                error_message=f"Head anchor mismatch: head has (seq={head_sequence_number}, hash='{head_event_hash}'), but last event has (seq={last_ev.sequence_number}, hash='{last_ev.event_hash}').",
                first_inconsistent_id=getattr(last_ev, "id", None),
                first_inconsistent_event_id=getattr(last_ev, "event_id", None),
                first_inconsistent_sequence=last_ev.sequence_number,
                expected_hash=last_ev.event_hash,
                actual_hash=head_event_hash,
            )

        return AuditChainVerificationReport(
            is_valid=True,
            total_events=len(events),
            head_sequence_number=head_sequence_number,
            head_event_hash=head_event_hash,
        )

    @classmethod
    async def verify_chain(cls, session: AsyncSession) -> AuditChainVerificationReport:
        """Verify the cryptographic integrity of the entire audit chain from genesis to head."""
        head_stmt = (
            select(AuditChainHeadModel)
            .where(AuditChainHeadModel.id == 1)
            .execution_options(populate_existing=True)
        )
        head_res = await session.execute(head_stmt)
        head = head_res.scalar_one_or_none()

        stmt = (
            select(GovernanceAuditEventModel)
            .order_by(GovernanceAuditEventModel.sequence_number.asc())
            .execution_options(populate_existing=True)
        )
        events_res = await session.execute(stmt)
        events = events_res.scalars().all()

        return cls.verify_events(
            events=events,
            head_sequence_number=head.last_sequence_number if head else None,
            head_event_hash=head.last_event_hash if head else None,
        )
