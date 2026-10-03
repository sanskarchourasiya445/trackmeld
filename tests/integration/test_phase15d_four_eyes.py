"""Phase 15D Integration Tests — Four-Eyes Separation of Duties.

Verifies that the author of a PlanVersion cannot approve their own candidate.
An independent authorized approver CAN approve.

Safety invariant:
    COMPLETED != APPROVED
    creator cannot == approver
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import AuthUser, UserRole
from backend.app.repositories.plan_version_repo import (
    FourEyesViolationError,
    PlanVersionRepository,
)
from backend.app.services.plan_governance_service import PlanGovernanceService
from tests.integration.test_phase15b_governance_concurrency import _seed_completed_run_and_candidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_actor(username: str, role: UserRole = UserRole.OPERATOR) -> AuthUser:
    return AuthUser(
        user_id=f"{username}-id",
        username=username,
        role=role,
        permissions=["plan:approve", "plan:reject", "plan:view", "plan:create"],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_cannot_approve_own_plan(db_session: AsyncSession) -> None:
    """Author of a plan MUST NOT be able to approve it — FourEyesViolationError raised."""
    run, plan = await _seed_completed_run_and_candidate(db_session)

    # The seeded plan has created_by == actor.username of the planner token
    # Attempt approval with the same identity that created the plan
    creator_username = plan.created_by
    creator_actor = _make_actor(creator_username)

    service = PlanGovernanceService(db_session)
    with pytest.raises(FourEyesViolationError, match="Separation of duties violation"):
        await service.approve_plan(plan.plan_version_id, creator_actor)


@pytest.mark.asyncio
async def test_independent_approver_can_approve(db_session: AsyncSession) -> None:
    """An authorized approver who did NOT create the plan CAN approve it."""
    run, plan = await _seed_completed_run_and_candidate(db_session)

    # Use a different identity from the creator
    creator_username = plan.created_by
    approver_username = f"independent_approver_{creator_username[:4]}"
    assert approver_username != creator_username

    approver_actor = _make_actor(approver_username)
    service = PlanGovernanceService(db_session)
    approved = await service.approve_plan(plan.plan_version_id, approver_actor)

    assert approved.status == "APPROVED"
    # Core invariant: APPROVED requires explicit human action, not solver output
    assert approved.approved_by == approver_username


@pytest.mark.asyncio
async def test_four_eyes_does_not_prevent_independent_rejection(
    db_session: AsyncSession,
) -> None:
    """Creator IS allowed to reject their own plan — only approval is restricted."""
    run, plan = await _seed_completed_run_and_candidate(db_session)

    creator_username = plan.created_by
    creator_actor = _make_actor(creator_username)
    # Add reject permission
    creator_actor_with_reject = AuthUser(
        user_id=creator_actor.user_id,
        username=creator_actor.username,
        role=creator_actor.role,
        permissions=list(set(creator_actor.permissions) | {"plan:reject"}),
    )

    service = PlanGovernanceService(db_session)
    rejected = await service.reject_plan(
        plan.plan_version_id,
        creator_actor_with_reject,
        reason="Self-identified error in schedule — withdrawing for revision.",
    )
    assert rejected.status == "REJECTED"


@pytest.mark.asyncio
async def test_four_eyes_uses_username_not_user_id(db_session: AsyncSession) -> None:
    """Four-eyes check must use authoritative username, not a mismatched user_id."""
    run, plan = await _seed_completed_run_and_candidate(db_session)

    creator_username = plan.created_by
    # Actor with a DIFFERENT user_id but same username as creator → should be blocked
    actor_same_username_diff_id = AuthUser(
        user_id="completely-different-id-9999",
        username=creator_username,
        role=UserRole.OPERATOR,
        permissions=["plan:approve"],
    )

    service = PlanGovernanceService(db_session)
    with pytest.raises(FourEyesViolationError):
        await service.approve_plan(plan.plan_version_id, actor_same_username_diff_id)
