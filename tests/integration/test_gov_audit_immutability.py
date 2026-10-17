"""Integration tests for P1 Audit-Table Permission Hardening (Migration 014).

Verifies database-engine level immutability on public.governance_audit_events:
1. Allowed INSERT with automatic sequence (public.governance_audit_events_id_seq) generation.
2. Allowed SELECT with full payload integrity.
3. Denied UPDATE with GOV-AUDIT-IMMUTABLE restrict_violation error (asserts row unchanged).
4. Denied DELETE with GOV-AUDIT-IMMUTABLE restrict_violation error (asserts row remains).
5. Denied TRUNCATE with GOV-AUDIT-IMMUTABLE restrict_violation error (asserts row count intact).
6. Legitimate governance service workflow execution (Append-only state transition audit trail).
7. Test isolation verification across distinct entity IDs without table deletion.
"""

import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy import select, text, func
from sqlalchemy.exc import DBAPIError, InternalError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.plan_version import GovernanceAuditEventModel
from backend.app.schemas.plan_version import GovernanceEventType
from backend.app.services.audit_chain_service import append_chained_audit_event


@pytest.mark.asyncio
async def test_audit_event_insert_and_sequence_advancement(db_session: AsyncSession):
    """Test 1: Allowed INSERT generates unique ID via sequence public.governance_audit_events_id_seq."""
    now = datetime.now(timezone.utc)
    event_id = f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    plan_id = f"PV-TEST-{uuid.uuid4().hex[:8].upper()}"

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
        comment="Test audit event insertion",
        schedule_identity="a" * 64,
        snapshot_hash="b" * 64,
        input_hash="c" * 64,
        event_metadata={"scenario_id": "SCN-DEMO-001", "version_number": 1},
    )
    await append_chained_audit_event(db_session, event)
    await db_session.commit()

    assert event.id is not None
    assert event.id > 0
    assert event.event_id == event_id


@pytest.mark.asyncio
async def test_audit_event_read_integrity(db_session: AsyncSession):
    """Test 2: Allowed SELECT returns exact persisted audit record and metadata."""
    now = datetime.now(timezone.utc)
    event_id = f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    plan_id = f"PV-TEST-{uuid.uuid4().hex[:8].upper()}"

    event = GovernanceAuditEventModel(
        event_id=event_id,
        entity_type="PLAN_VERSION",
        entity_id=plan_id,
        event_type=GovernanceEventType.PLAN_APPROVED.value,
        actor_id="usr-approver-01",
        actor_username="divisional_operations_manager",
        actor_role="APPROVER",
        timestamp=now,
        previous_state="PENDING_REVIEW",
        new_state="APPROVED",
        comment="Formal operational approval certified",
        schedule_identity="f" * 64,
        snapshot_hash="1" * 64,
        input_hash="2" * 64,
        event_metadata={"scenario_id": "SCN-DEMO-001", "version_number": 1},
    )
    await append_chained_audit_event(db_session, event)
    await db_session.commit()

    # Read back via select
    stmt = select(GovernanceAuditEventModel).where(GovernanceAuditEventModel.event_id == event_id)
    res = await db_session.execute(stmt)
    persisted = res.scalar_one()

    assert persisted.id == event.id
    assert persisted.event_id == event_id
    assert persisted.entity_id == plan_id
    assert persisted.event_type == "PLAN_APPROVED"
    assert persisted.actor_username == "divisional_operations_manager"
    assert persisted.schedule_identity == "f" * 64
    assert persisted.event_metadata == {"scenario_id": "SCN-DEMO-001", "version_number": 1}


@pytest.mark.asyncio
async def test_audit_event_update_denied_by_trigger(db_session: AsyncSession):
    """Test 3: Denied UPDATE produces GOV-AUDIT-IMMUTABLE restrict_violation and leaves row untampered."""
    now = datetime.now(timezone.utc)
    event_id = f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    plan_id = f"PV-TEST-{uuid.uuid4().hex[:8].upper()}"

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
        comment="Original uncorrupted comment",
    )
    await append_chained_audit_event(db_session, event)
    await db_session.commit()
    target_id = event.id

    # Attempt illegal raw SQL update
    with pytest.raises((DBAPIError, InternalError)) as exc_info:
        await db_session.execute(
            text("UPDATE public.governance_audit_events SET comment = 'Tampered content' WHERE id = :id"),
            {"id": target_id},
        )
        await db_session.commit()

    err_msg = str(exc_info.value)
    assert "GOV-AUDIT-IMMUTABLE" in err_msg
    assert "UPDATE operation denied on table governance_audit_events" in err_msg
    assert f"id={target_id}" in err_msg
    assert f"event_id={event_id}" in err_msg

    await db_session.rollback()

    # Verify row was NOT modified
    stmt = select(GovernanceAuditEventModel).where(GovernanceAuditEventModel.id == target_id)
    res = await db_session.execute(stmt)
    unchanged = res.scalar_one()
    assert unchanged.comment == "Original uncorrupted comment"


@pytest.mark.asyncio
async def test_audit_event_delete_denied_by_trigger(db_session: AsyncSession):
    """Test 4: Denied DELETE produces GOV-AUDIT-IMMUTABLE restrict_violation and keeps row in table."""
    now = datetime.now(timezone.utc)
    event_id = f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    plan_id = f"PV-TEST-{uuid.uuid4().hex[:8].upper()}"

    event = GovernanceAuditEventModel(
        event_id=event_id,
        entity_type="PLAN_VERSION",
        entity_id=plan_id,
        event_type=GovernanceEventType.PLAN_APPROVED.value,
        actor_id="usr-approver-01",
        actor_username="divisional_operations_manager",
        actor_role="APPROVER",
        timestamp=now,
        previous_state="PENDING_REVIEW",
        new_state="APPROVED",
        comment="Indelible approval ledger entry",
    )
    await append_chained_audit_event(db_session, event)
    await db_session.commit()
    target_id = event.id

    # Attempt illegal raw SQL delete
    with pytest.raises((DBAPIError, InternalError)) as exc_info:
        await db_session.execute(
            text("DELETE FROM public.governance_audit_events WHERE id = :id"),
            {"id": target_id},
        )
        await db_session.commit()

    err_msg = str(exc_info.value)
    assert "GOV-AUDIT-IMMUTABLE" in err_msg
    assert "DELETE operation denied on table governance_audit_events" in err_msg
    assert f"id={target_id}" in err_msg
    assert f"event_id={event_id}" in err_msg

    await db_session.rollback()

    # Verify row is STILL present
    stmt = select(GovernanceAuditEventModel).where(GovernanceAuditEventModel.id == target_id)
    res = await db_session.execute(stmt)
    assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_audit_table_truncate_denied_by_trigger(db_session: AsyncSession):
    """Test 5: Denied TRUNCATE produces GOV-AUDIT-IMMUTABLE restrict_violation and preserves all rows."""
    # Count rows before truncate attempt
    count_stmt = select(func.count()).select_from(GovernanceAuditEventModel)
    initial_count = (await db_session.execute(count_stmt)).scalar() or 0

    with pytest.raises((DBAPIError, InternalError)) as exc_info:
        await db_session.execute(text("TRUNCATE TABLE public.governance_audit_events;"))
        await db_session.commit()

    err_msg = str(exc_info.value)
    assert "GOV-AUDIT-IMMUTABLE" in err_msg
    assert "TRUNCATE operation denied on table governance_audit_events" in err_msg

    await db_session.rollback()

    # Count rows after: must be identical
    after_count = (await db_session.execute(count_stmt)).scalar() or 0
    assert after_count == initial_count


@pytest.mark.asyncio
async def test_entity_scoped_isolation_without_deletion(db_session: AsyncSession):
    """Test 6: Multiple tests execute safely without cross-talk using entity_id query scoping."""
    plan_a = f"PV-A-{uuid.uuid4().hex[:8].upper()}"
    plan_b = f"PV-B-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)

    # Insert events for Plan A
    ev_a = GovernanceAuditEventModel(
        event_id=f"AUD-A-{uuid.uuid4().hex[:6].upper()}",
        entity_type="PLAN_VERSION",
        entity_id=plan_a,
        event_type="PLAN_VERSION_CREATED",
        actor_id="user-a",
        actor_username="planner_a",
        actor_role="PLANNER",
        timestamp=now,
        comment="Plan A event",
    )
    # Insert events for Plan B
    ev_b = GovernanceAuditEventModel(
        event_id=f"AUD-B-{uuid.uuid4().hex[:6].upper()}",
        entity_type="PLAN_VERSION",
        entity_id=plan_b,
        event_type="PLAN_VERSION_CREATED",
        actor_id="user-b",
        actor_username="planner_b",
        actor_role="PLANNER",
        timestamp=now,
        comment="Plan B event",
    )
    await append_chained_audit_event(db_session, ev_a)
    await append_chained_audit_event(db_session, ev_b)
    await db_session.commit()

    # Query Plan A: strictly returns Plan A's audit events
    stmt_a = (
        select(GovernanceAuditEventModel)
        .where(
            GovernanceAuditEventModel.entity_type == "PLAN_VERSION",
            GovernanceAuditEventModel.entity_id == plan_a,
        )
    )
    res_a = (await db_session.execute(stmt_a)).scalars().all()
    assert len(res_a) == 1
    assert res_a[0].entity_id == plan_a
    assert res_a[0].comment == "Plan A event"

    # Query Plan B: strictly returns Plan B's audit events
    stmt_b = (
        select(GovernanceAuditEventModel)
        .where(
            GovernanceAuditEventModel.entity_type == "PLAN_VERSION",
            GovernanceAuditEventModel.entity_id == plan_b,
        )
    )
    res_b = (await db_session.execute(stmt_b)).scalars().all()
    assert len(res_b) == 1
    assert res_b[0].entity_id == plan_b
    assert res_b[0].comment == "Plan B event"
