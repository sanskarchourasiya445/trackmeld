"""Integration and verification tests for P1 Cryptographic Audit Chaining (Migration 015).

Verifies the end-to-end cryptographic tamper-evidence and chain integrity:
1. Correct SHA-256 hashes and sequence numbers for newly appended events.
2. Multiple events and strict monotonic sequence ordering across governance lifecycle states.
3. Modular verifier detection:
   - Modified payload / comment detected as HASH_MISMATCH.
   - Modified stored hash detected as HASH_MISMATCH.
   - Tampered previous-hash pointer detected as BROKEN_LINK.
   - Discontinuous sequence numbers detected as SEQUENCE_GAP.
   - Unaligned chain head detected as HEAD_MISMATCH.
4. Live DB tamper detection: Verifier flags raw-SQL modifications and clears once restored.
5. Concurrent append serialization: 10 concurrent async sessions queue on audit_chain_head row-lock with 0 forks, consecutive sequence numbers, and unbroken links.
6. Transaction rollback safety: Uncommitted sequence numbers and head mutations are completely reverted by PostgreSQL transaction boundaries.
7. Historical backfill integrity: Pre-existing audit records form a continuous, unbroken chain.
"""

import asyncio
import copy
from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.models.plan_version import GovernanceAuditEventModel, AuditChainHeadModel
from backend.app.schemas.plan_version import GovernanceEventType
from backend.app.services.audit_chain_service import (
    GENESIS_HASH,
    append_chained_audit_event,
    compute_audit_event_hash,
    AuditChainVerifier,
)
from tests.conftest import get_test_database_url


@pytest.mark.asyncio
async def test_newly_inserted_event_hash_correctness(db_session: AsyncSession):
    """Test 1: Correct SHA-256 hashes, sequence numbers, and previous pointers on new events."""
    now = datetime.now(timezone.utc)
    event_id = f"AUD-CHAIN-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    plan_id = f"PV-CHAIN-{uuid.uuid4().hex[:8].upper()}"

    # Get current chain head before appending
    head_res = await db_session.execute(select(AuditChainHeadModel).where(AuditChainHeadModel.id == 1))
    head_before = head_res.scalar_one()
    expected_seq = head_before.last_sequence_number + 1
    expected_prev_hash = head_before.last_event_hash

    event = GovernanceAuditEventModel(
        event_id=event_id,
        entity_type="PLAN_VERSION",
        entity_id=plan_id,
        event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
        actor_id="usr-planner-01",
        actor_username="senior_planner_dli",
        actor_role="PLANNER",
        timestamp=now,
        previous_state=None,
        new_state="PENDING_REVIEW",
        comment="Cryptographic chain unit test event",
        schedule_identity="1" * 64,
        snapshot_hash="2" * 64,
        input_hash="3" * 64,
        event_metadata={"scenario_id": "SCN-TEST-CHAIN", "version_number": 1},
    )

    await append_chained_audit_event(db_session, event)
    await db_session.commit()

    assert event.sequence_number == expected_seq
    assert event.previous_event_hash == expected_prev_hash
    assert len(event.event_hash) == 64

    # Independently compute hash and assert 100% byte-for-byte equivalence
    recomputed = compute_audit_event_hash(
        event=event,
        previous_event_hash=expected_prev_hash,
        sequence_number=expected_seq,
    )
    assert event.event_hash == recomputed

    # Verify head table was atomically advanced
    head_res_after = await db_session.execute(select(AuditChainHeadModel).where(AuditChainHeadModel.id == 1))
    head_after = head_res_after.scalar_one()
    assert head_after.last_sequence_number == expected_seq
    assert head_after.last_event_hash == event.event_hash
    assert head_after.last_event_id == event.event_id


@pytest.mark.asyncio
async def test_multiple_events_and_chain_ordering(db_session: AsyncSession):
    """Test 2: Multiple events maintain strict monotonic sequence numbers and unbroken links."""
    plan_id = f"PV-MULTI-{uuid.uuid4().hex[:8].upper()}"
    event_types = [
        GovernanceEventType.PLAN_VERSION_CREATED.value,
        GovernanceEventType.PLAN_REVIEW_STARTED.value,
        GovernanceEventType.PLAN_COMMENT_ADDED.value,
        GovernanceEventType.PLAN_APPROVED.value,
        GovernanceEventType.PLAN_SUPERSEDED.value,
    ]

    events = []
    for idx, et in enumerate(event_types):
        now = datetime.now(timezone.utc)
        ev = GovernanceAuditEventModel(
            event_id=f"AUD-ORD-{idx}-{uuid.uuid4().hex[:6].upper()}",
            entity_type="PLAN_VERSION",
            entity_id=plan_id,
            event_type=et,
            actor_id="usr-planner-01",
            actor_username="senior_planner_dli",
            actor_role="PLANNER",
            timestamp=now,
            comment=f"Step {idx + 1} in multi-event workflow",
        )
        await append_chained_audit_event(db_session, ev)
        events.append(ev)

    await db_session.commit()

    # Verify monotonic sequencing and pointer links
    for i in range(len(events)):
        if i > 0:
            assert events[i].sequence_number == events[i - 1].sequence_number + 1
            assert events[i].previous_event_hash == events[i - 1].event_hash
        assert len(events[i].event_hash) == 64

    # Verify full chain passes verifier
    report = await AuditChainVerifier.verify_chain(db_session)
    assert report.is_valid is True
    assert report.error_code is None


def test_verifier_detects_payload_tampering():
    """Test 3A: Verifier flags modified event payload with HASH_MISMATCH."""
    now = datetime.now(timezone.utc)
    ev1 = GovernanceAuditEventModel(
        id=101,
        event_id="AUD-T1",
        sequence_number=1,
        previous_event_hash=GENESIS_HASH,
        event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
        actor_id="usr-1",
        timestamp=now,
        comment="Genuine comment",
    )
    ev1.event_hash = compute_audit_event_hash(ev1, GENESIS_HASH, 1)

    ev2 = GovernanceAuditEventModel(
        id=102,
        event_id="AUD-T2",
        sequence_number=2,
        previous_event_hash=ev1.event_hash,
        event_type=GovernanceEventType.PLAN_APPROVED.value,
        actor_id="usr-2",
        timestamp=now,
        comment="Genuine approval",
    )
    ev2.event_hash = compute_audit_event_hash(ev2, ev1.event_hash, 2)

    # Valid chain passes
    valid_report = AuditChainVerifier.verify_events([ev1, ev2], 2, ev2.event_hash)
    assert valid_report.is_valid is True

    # Tamper with ev1 payload
    tampered_ev1 = copy.copy(ev1)
    tampered_ev1.comment = "Malicious unauthorized alteration"

    tampered_report = AuditChainVerifier.verify_events([tampered_ev1, ev2], 2, ev2.event_hash)
    assert tampered_report.is_valid is False
    assert tampered_report.error_code == "HASH_MISMATCH"
    assert tampered_report.first_inconsistent_id == 101
    assert tampered_report.first_inconsistent_sequence == 1
    assert tampered_report.expected_hash != tampered_report.actual_hash


def test_verifier_detects_modified_stored_hash():
    """Test 3B: Verifier flags tampered stored hash with HASH_MISMATCH."""
    now = datetime.now(timezone.utc)
    ev1 = GovernanceAuditEventModel(
        id=201,
        event_id="AUD-H1",
        sequence_number=1,
        previous_event_hash=GENESIS_HASH,
        event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
        actor_id="usr-1",
        timestamp=now,
        comment="Valid event",
    )
    ev1.event_hash = compute_audit_event_hash(ev1, GENESIS_HASH, 1)

    # Alter stored hash
    tampered_ev1 = copy.copy(ev1)
    tampered_ev1.event_hash = "deadbeef" * 8

    report = AuditChainVerifier.verify_events([tampered_ev1], 1, tampered_ev1.event_hash)
    assert report.is_valid is False
    assert report.error_code == "HASH_MISMATCH"
    assert report.first_inconsistent_id == 201


def test_verifier_detects_broken_link():
    """Test 3C: Verifier flags broken previous_event_hash with BROKEN_LINK."""
    now = datetime.now(timezone.utc)
    ev1 = GovernanceAuditEventModel(
        id=301,
        event_id="AUD-L1",
        sequence_number=1,
        previous_event_hash=GENESIS_HASH,
        event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
        actor_id="usr-1",
        timestamp=now,
    )
    ev1.event_hash = compute_audit_event_hash(ev1, GENESIS_HASH, 1)

    ev2 = GovernanceAuditEventModel(
        id=302,
        event_id="AUD-L2",
        sequence_number=2,
        previous_event_hash="invalid_parent_hash" + "0" * 46,
        event_type=GovernanceEventType.PLAN_APPROVED.value,
        actor_id="usr-2",
        timestamp=now,
    )
    ev2.event_hash = compute_audit_event_hash(ev2, ev2.previous_event_hash, 2)

    report = AuditChainVerifier.verify_events([ev1, ev2], 2, ev2.event_hash)
    assert report.is_valid is False
    assert report.error_code == "BROKEN_LINK"
    assert report.first_inconsistent_id == 302
    assert report.first_inconsistent_sequence == 2
    assert report.expected_hash == ev1.event_hash
    assert report.actual_hash == ev2.previous_event_hash


def test_verifier_detects_sequence_gap():
    """Test 3D: Verifier flags sequence number discontinuity with SEQUENCE_GAP."""
    now = datetime.now(timezone.utc)
    ev1 = GovernanceAuditEventModel(
        id=401,
        event_id="AUD-G1",
        sequence_number=1,
        previous_event_hash=GENESIS_HASH,
        event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
        actor_id="usr-1",
        timestamp=now,
    )
    ev1.event_hash = compute_audit_event_hash(ev1, GENESIS_HASH, 1)

    # Event 2 has sequence_number 3 instead of 2 (a gap)
    ev2 = GovernanceAuditEventModel(
        id=402,
        event_id="AUD-G2",
        sequence_number=3,
        previous_event_hash=ev1.event_hash,
        event_type=GovernanceEventType.PLAN_APPROVED.value,
        actor_id="usr-2",
        timestamp=now,
    )
    ev2.event_hash = compute_audit_event_hash(ev2, ev1.event_hash, 3)

    report = AuditChainVerifier.verify_events([ev1, ev2], 3, ev2.event_hash)
    assert report.is_valid is False
    assert report.error_code == "SEQUENCE_GAP"
    assert report.first_inconsistent_id == 402
    assert report.first_inconsistent_sequence == 3


def test_verifier_detects_head_mismatch():
    """Test 3E: Verifier flags head anchor disagreement with HEAD_MISMATCH."""
    now = datetime.now(timezone.utc)
    ev1 = GovernanceAuditEventModel(
        id=501,
        event_id="AUD-H1",
        sequence_number=1,
        previous_event_hash=GENESIS_HASH,
        event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
        actor_id="usr-1",
        timestamp=now,
    )
    ev1.event_hash = compute_audit_event_hash(ev1, GENESIS_HASH, 1)

    # Head claims sequence 5
    report = AuditChainVerifier.verify_events([ev1], 5, ev1.event_hash)
    assert report.is_valid is False
    assert report.error_code == "HEAD_MISMATCH"


@pytest.mark.asyncio
async def test_live_db_tamper_detection_and_restoration(db_session: AsyncSession):
    """Test 4: Live DB raw-SQL tamper is detected and clears after restoration under try...finally."""
    now = datetime.now(timezone.utc)
    ev = GovernanceAuditEventModel(
        event_id=f"AUD-LIVE-TAMPER-{uuid.uuid4().hex[:6].upper()}",
        entity_type="PLAN_VERSION",
        entity_id=f"PV-LIVE-TAMPER-{uuid.uuid4().hex[:6].upper()}",
        event_type=GovernanceEventType.PLAN_APPROVED.value,
        actor_id="usr-approver-01",
        actor_username="divisional_operations_manager",
        actor_role="APPROVER",
        timestamp=now,
        comment="Genuine unadulterated approval statement",
    )
    await append_chained_audit_event(db_session, ev)
    await db_session.commit()
    target_id = ev.id
    target_seq = ev.sequence_number
    original_comment = ev.comment

    try:
        # Adversarially tamper with comment via elevated SQL (disabling immutability trigger)
        await db_session.execute(text("ALTER TABLE public.governance_audit_events DISABLE TRIGGER trg_audit_events_no_update_delete;"))
        await db_session.execute(
            text("UPDATE public.governance_audit_events SET comment = 'Adversarial fraudulent approval' WHERE id = :id"),
            {"id": target_id},
        )
        await db_session.execute(text("ALTER TABLE public.governance_audit_events ENABLE TRIGGER trg_audit_events_no_update_delete;"))
        await db_session.commit()

        # Verifier must detect tampering on the live database
        report = await AuditChainVerifier.verify_chain(db_session)
        assert report.is_valid is False
        assert report.error_code == "HASH_MISMATCH"
        assert report.first_inconsistent_id == target_id
        assert report.first_inconsistent_sequence == target_seq
        assert "Payload tamper or hash mismatch" in (report.error_message or "")
    finally:
        # Guaranteed restoration
        await db_session.execute(text("ALTER TABLE public.governance_audit_events DISABLE TRIGGER trg_audit_events_no_update_delete;"))
        await db_session.execute(
            text("UPDATE public.governance_audit_events SET comment = :c WHERE id = :id"),
            {"c": original_comment, "id": target_id},
        )
        await db_session.execute(text("ALTER TABLE public.governance_audit_events ENABLE TRIGGER trg_audit_events_no_update_delete;"))
        await db_session.commit()

    # Re-verify live DB chain is restored
    restored_report = await AuditChainVerifier.verify_chain(db_session)
    assert restored_report.is_valid is True


@pytest.mark.asyncio
async def test_concurrent_writes_without_forks_or_lost_links():
    """Test 5: Concurrent writes are strictly serialized by row-lock with 0 forks and unbroken links."""
    test_db_url = get_test_database_url()
    engine = create_async_engine(test_db_url, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    num_concurrent = 10

    async def worker_append(worker_idx: int):
        async with session_factory() as session:
            ev = GovernanceAuditEventModel(
                event_id=f"AUD-CONCUR-{worker_idx}-{uuid.uuid4().hex[:6].upper()}",
                entity_type="PLAN_VERSION",
                entity_id=f"PV-CONCUR-{worker_idx}",
                event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
                actor_id=f"usr-worker-{worker_idx}",
                actor_username=f"worker_{worker_idx}",
                actor_role="PLANNER",
                timestamp=datetime.now(timezone.utc),
                comment=f"Concurrent append worker {worker_idx}",
            )
            await append_chained_audit_event(session, ev)
            await session.commit()
            return {
                "worker_idx": worker_idx,
                "event_id": ev.event_id,
                "sequence_number": ev.sequence_number,
                "previous_event_hash": ev.previous_event_hash,
                "event_hash": ev.event_hash,
            }

    # Execute all appends concurrently
    tasks = [worker_append(i) for i in range(num_concurrent)]
    res_list = await asyncio.gather(*tasks)

    # Sort results by sequence number
    res_sorted = sorted(res_list, key=lambda x: x["sequence_number"])
    sequences = [r["sequence_number"] for r in res_sorted]

    # Verify no duplicate sequence numbers (0 forks)
    assert len(sequences) == len(set(sequences)), "Forks detected! Duplicate sequence numbers found."

    # Verify sequence continuity across the concurrent batch
    for i in range(1, len(res_sorted)):
        assert res_sorted[i]["sequence_number"] == res_sorted[i - 1]["sequence_number"] + 1, "Gap in sequence numbers!"
        assert res_sorted[i]["previous_event_hash"] == res_sorted[i - 1]["event_hash"], "Broken link in concurrent batch!"

    # Verify full chain integrity in DB
    async with session_factory() as session:
        report = await AuditChainVerifier.verify_chain(session)
        assert report.is_valid is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_transaction_rollback_preserves_chain_integrity(db_session: AsyncSession):
    """Test 6: Rolled-back append cleanly reverts sequence advancement and leaves chain valid."""
    head_res = await db_session.execute(select(AuditChainHeadModel).where(AuditChainHeadModel.id == 1))
    head_before = head_res.scalar_one()
    tip_seq_before = head_before.last_sequence_number
    tip_hash_before = head_before.last_event_hash

    # Attempt append inside a transaction that rolls back
    ev_rolled_back = GovernanceAuditEventModel(
        event_id=f"AUD-ROLLBACK-{uuid.uuid4().hex[:6].upper()}",
        entity_type="PLAN_VERSION",
        entity_id="PV-ROLLBACK-TEST",
        event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
        actor_id="usr-planner-01",
        actor_username="planner_01",
        actor_role="PLANNER",
        timestamp=datetime.now(timezone.utc),
        comment="This transaction will be rolled back",
    )
    await append_chained_audit_event(db_session, ev_rolled_back)
    # Roll back instead of committing
    await db_session.rollback()

    # Re-query head: must remain at previous tip
    head_res_after = await db_session.execute(select(AuditChainHeadModel).where(AuditChainHeadModel.id == 1))
    head_after = head_res_after.scalar_one()
    assert head_after.last_sequence_number == tip_seq_before
    assert head_after.last_event_hash == tip_hash_before

    # Re-query event: must NOT exist in table
    ev_res = await db_session.execute(
        select(GovernanceAuditEventModel).where(GovernanceAuditEventModel.event_id == ev_rolled_back.event_id)
    )
    assert ev_res.scalar_one_or_none() is None

    # Next append must smoothly claim tip_seq_before + 1 with tip_hash_before as parent
    ev_next = GovernanceAuditEventModel(
        event_id=f"AUD-NEXT-{uuid.uuid4().hex[:6].upper()}",
        entity_type="PLAN_VERSION",
        entity_id="PV-NEXT-TEST",
        event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
        actor_id="usr-planner-01",
        actor_username="planner_01",
        actor_role="PLANNER",
        timestamp=datetime.now(timezone.utc),
        comment="Committed event after rollback",
    )
    await append_chained_audit_event(db_session, ev_next)
    await db_session.commit()

    assert ev_next.sequence_number == tip_seq_before + 1
    assert ev_next.previous_event_hash == tip_hash_before

    # Verify chain remains valid
    report = await AuditChainVerifier.verify_chain(db_session)
    assert report.is_valid is True


@pytest.mark.asyncio
async def test_historical_backfill_and_existing_records_validity(db_session: AsyncSession):
    """Test 7: Migration 015 backfill produced a valid, contiguous cryptographic chain for all historical records."""
    report = await AuditChainVerifier.verify_chain(db_session)

    assert report.is_valid is True
    assert report.total_events >= 21
    assert report.head_sequence_number == report.total_events
    assert len(report.head_event_hash) == 64
    assert report.error_code is None
