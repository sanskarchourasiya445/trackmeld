import { test, expect, TEST_CONFIG, authenticateViaUi, waitForRunCompleted } from './fixtures';

test.describe('Phase 15E: Negative Paths, Integrity & State Machine E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      sessionStorage.clear();
      localStorage.clear();
    });
  });

  test('Four-Eyes principle strictly prevents creator from approving own plan', async ({ request, page }) => {
    // 1. Create run and candidate version as planner
    const runRes = await request.post(`${TEST_CONFIG.apiUrl}/planning-runs`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { scenario_id: TEST_CONFIG.scenarioId, scheduler_type: 'CP_SAT', validate_after_solve: true },
    });
    const run = await runRes.json();
    await waitForRunCompleted(request, run.run_id);

    const planRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { planning_run_id: run.run_id, comment: 'Candidate for negative test' },
    });
    const plan = await planRes.json();
    const planId = plan.plan_version_id;

    // 2. Direct API approval attempt by planner (lacks plan:approve permission -> 403 Forbidden)
    const plannerApproveRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions/${planId}/approve`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { comment: 'Planner unauthorized approval attempt' },
    });
    expect(plannerApproveRes.status()).toBe(403);

    // 3. Create candidate where creator HAS plan:approve permission (admin identity)
    const adminRunRes = await request.post(`${TEST_CONFIG.apiUrl}/planning-runs`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.adminToken}` },
      data: { scenario_id: TEST_CONFIG.scenarioId, scheduler_type: 'CP_SAT', validate_after_solve: true },
    });
    const adminRun = await adminRunRes.json();
    await waitForRunCompleted(request, adminRun.run_id);

    const adminPlanRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.adminToken}` },
      data: { planning_run_id: adminRun.run_id, comment: 'Admin-created candidate' },
    });
    const adminPlan = await adminPlanRes.json();
    const adminPlanId = adminPlan.plan_version_id;

    // Admin self-approval attempt (Creator == Approver -> strictly 409 FOUR_EYES_VIOLATION)
    const adminSelfApproveRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions/${adminPlanId}/approve`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.adminToken}` },
      data: { comment: 'Admin self-approval attempt' },
    });
    expect(adminSelfApproveRes.status()).toBe(409);
    const errJson = await adminSelfApproveRes.json();
    expect(errJson.error.code).toBe('FOUR_EYES_VIOLATION');
    expect(errJson.error.message).toContain('Separation of duties violation');

    // 4. Verify in browser UI that plan status remains PENDING_REVIEW
    await authenticateViaUi(page, TEST_CONFIG.plannerToken);
    await page.goto('/audit');
    await page.locator('button:has-text("Refresh")').first().click();

    const planRow = page.locator(`tr:has-text("${planId}")`);
    await expect(planRow).toBeVisible({ timeout: 10000 });
    await expect(planRow.locator('span:has-text("Pending Review")')).toBeVisible();
  });

  test('Rejection workflow transitions to REJECTED and cannot subsequently be approved', async ({ request, page }) => {
    // 1. Setup a plan candidate
    const runRes = await request.post(`${TEST_CONFIG.apiUrl}/planning-runs`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { scenario_id: TEST_CONFIG.scenarioId, scheduler_type: 'CP_SAT', validate_after_solve: true },
    });
    const run = await runRes.json();
    await waitForRunCompleted(request, run.run_id);

    const planRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { planning_run_id: run.run_id },
    });
    const plan = await planRes.json();
    const planId = plan.plan_version_id;

    // 2. Reject the plan via approver
    const rejectRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions/${planId}/reject`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.approverToken}` },
      data: { reason: 'Track occupancy conflict with Rajdhani Express buffer.' },
    });
    expect(rejectRes.status()).toBe(200);
    const rejectedPlan = await rejectRes.json();
    expect(rejectedPlan.status).toBe('REJECTED');

    // 3. Attempt to approve the REJECTED plan (Must fail with 409 ILLEGAL_TRANSITION)
    const approveRejectedRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions/${planId}/approve`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.approverToken}` },
      data: { comment: 'Illegal approval attempt on rejected plan' },
    });
    expect(approveRejectedRes.status()).toBe(409);
    const errBody = await approveRejectedRes.json();
    expect(errBody.error.code).toBe('ILLEGAL_TRANSITION');

    // 4. Verify in UI that status is truthfully REJECTED
    await authenticateViaUi(page, TEST_CONFIG.approverToken);
    await page.goto('/audit');
    await page.locator('button:has-text("Refresh")').first().click();

    const planRow = page.locator(`tr:has-text("${planId}")`);
    await expect(planRow).toBeVisible({ timeout: 10000 });
    await expect(planRow.locator('span:has-text("Rejected")')).toBeVisible();
  });

  test('Approving newer version supersedes previously approved version', async ({ request, page }) => {
    // 1. Create and approve Version 1
    const run1Res = await request.post(`${TEST_CONFIG.apiUrl}/planning-runs`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { scenario_id: TEST_CONFIG.scenarioId, scheduler_type: 'CP_SAT', validate_after_solve: true },
    });
    const run1 = await run1Res.json();
    await waitForRunCompleted(request, run1.run_id);

    const plan1Res = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { planning_run_id: run1.run_id, comment: 'First candidate' },
    });
    const plan1 = await plan1Res.json();
    const plan1Id = plan1.plan_version_id;

    // Approver approves Version 1
    const appr1Res = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions/${plan1Id}/approve`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.approverToken}` },
      data: { comment: 'Approving Version 1' },
    });
    expect(appr1Res.status()).toBe(200);

    // 2. Create and approve Version 2
    const run2Res = await request.post(`${TEST_CONFIG.apiUrl}/planning-runs`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { scenario_id: TEST_CONFIG.scenarioId, scheduler_type: 'CP_SAT', validate_after_solve: true },
    });
    const run2 = await run2Res.json();
    await waitForRunCompleted(request, run2.run_id);

    const plan2Res = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { planning_run_id: run2.run_id, comment: 'Second candidate' },
    });
    const plan2 = await plan2Res.json();
    const plan2Id = plan2.plan_version_id;

    // Approver approves Version 2 -> Version 1 must automatically become SUPERSEDED
    const appr2Res = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions/${plan2Id}/approve`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.approverToken}` },
      data: { comment: 'Approving Version 2 to supersede Version 1' },
    });
    expect(appr2Res.status()).toBe(200);

    // 3. Inspect Version 1 in backend
    const getPlan1Res = await request.get(`${TEST_CONFIG.apiUrl}/plan-versions/${plan1Id}`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.approverToken}` },
    });
    const plan1Updated = await getPlan1Res.json();
    expect(plan1Updated.status).toBe('SUPERSEDED');

    // 4. Inspect in Audit UI
    await authenticateViaUi(page, TEST_CONFIG.approverToken);
    await page.goto('/audit');
    await page.locator('button:has-text("Refresh")').first().click();

    // Version 2 shows Approved
    const plan2Row = page.locator(`tr:has-text("${plan2Id}")`);
    await expect(plan2Row.locator('span:has-text("Approved")')).toBeVisible({ timeout: 10000 });

    // Version 1 shows Superseded
    const plan1Row = page.locator(`tr:has-text("${plan1Id}")`);
    await expect(plan1Row.locator('span:has-text("Superseded")')).toBeVisible({ timeout: 10000 });
  });

  test('UI does not optimistically approve or fabricate success when API fails', async ({ page }) => {
    await authenticateViaUi(page, TEST_CONFIG.approverToken);
    await page.goto('/audit');

    // Intercept approve API call to simulate a backend error (e.g. 500)
    await page.route('**/api/v1/plan-versions/*/approve', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'INTERNAL_ERROR', message: 'Simulated backend database disconnection.' },
        }),
      });
    });

    // Click Approve Plan
    const approveBtn = page.locator('button:has-text("Approve Plan")').last();
    if (await approveBtn.isVisible()) {
      await approveBtn.click();

      // UI MUST show truthful error notice
      await expect(page.locator('text=ACTION NOT COMPLETED')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Simulated backend database disconnection')).toBeVisible();

      // UI must NOT show success toast or mutate local state to Approved
      await expect(page.locator('text=approved successfully')).not.toBeVisible();
    }
  });
});
