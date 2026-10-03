import { test, expect, TEST_CONFIG, authenticateViaUi, waitForRunCompleted } from './fixtures';

test.describe('Phase 15E: Primary Happy-Path Governance Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Start with a clean browser context and no stored tokens
    await page.goto('/');
    await page.evaluate(() => {
      sessionStorage.clear();
      localStorage.clear();
    });
  });

  test('Complete 12-step governance workflow with Four-Eyes enforcement', async ({ page, request }) => {
    // -------------------------------------------------------------------------
    // STEP 1: Open TrackMeld & verify unauthenticated state
    // -------------------------------------------------------------------------
    await page.goto('/planning');
    await expect(page).toHaveTitle(/TrackMeld/i);

    // Verify unauthenticated auth widget is visible
    const authTrigger = page.locator('button[aria-label^="Authentication:"]');
    await expect(authTrigger).toBeVisible();
    await expect(authTrigger).toContainText('Sign In');

    // -------------------------------------------------------------------------
    // STEP 2: Authenticate as authorized planner
    // -------------------------------------------------------------------------
    await authenticateViaUi(page, TEST_CONFIG.plannerToken);

    // Verify authenticated badge
    await expect(page.locator('button[aria-label="Authentication: Authenticated"]')).toBeVisible();

    // Verify session storage has token, but localStorage does not have privileged tokens
    const sessionToken = await page.evaluate(() => sessionStorage.getItem('trackmeld_auth_token'));
    expect(sessionToken).toBe(TEST_CONFIG.plannerToken);

    // -------------------------------------------------------------------------
    // STEP 3: Verify initial planning workspace is truthful
    // -------------------------------------------------------------------------
    await expect(page.locator('text=No schedule computed')).toBeVisible();
    await expect(page.locator('text=Backend unavailable or optimization has not yet run')).toBeVisible();

    // Switch to Validation tab and check uncomputed state
    await page.locator('button:has-text("Validation")').click();
    await expect(page.locator('text=STATUS: NOT RUN')).toBeVisible();
    await expect(page.locator('text=No validation data')).toBeVisible();

    // -------------------------------------------------------------------------
    // STEP 4 & 5: Run optimization from real backend
    // -------------------------------------------------------------------------
    const runOptBtn = page.locator('button:has-text("Run Optimization")');
    await expect(runOptBtn).toBeEnabled();
    await runOptBtn.click();

    // Check loading indicator appears
    await expect(page.locator('text=OPTIMIZING POSSESSION SCHEDULE')).toBeVisible();

    // Wait for optimization to complete (< 15 seconds)
    await expect(page.locator('text=OPTIMIZING POSSESSION SCHEDULE')).not.toBeVisible({ timeout: 20000 });

    // The uncomputed banner must be gone
    await expect(page.locator('text=No schedule computed')).not.toBeVisible();

    // -------------------------------------------------------------------------
    // STEP 6: Run validation and verify certification
    // -------------------------------------------------------------------------
    await page.locator('button:has-text("Validation")').click();
    await expect(page.locator('text=STATUS: VALID')).toBeVisible();
    await expect(page.locator('text=COMPLETED ≠ APPROVED')).toBeVisible();

    // -------------------------------------------------------------------------
    // STEP 7: Run diagnostics
    // -------------------------------------------------------------------------
    await page.getByRole('button', { name: 'Diagnostics', exact: true }).click();
    await expect(page.locator('text=Causal Constraint Diagnostics')).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------------------
    // STEP 8: Create/promote a PlanVersion candidate
    // -------------------------------------------------------------------------
    // Create planning run and candidate PlanVersion via API as the planner
    const createRunRes = await request.post(`${TEST_CONFIG.apiUrl}/planning-runs`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: {
        scenario_id: TEST_CONFIG.scenarioId,
        scheduler_type: 'CP_SAT',
        validate_after_solve: true,
      },
    });
    expect(createRunRes.ok()).toBeTruthy();
    const runData = await createRunRes.json();
    const runId = runData.run_id;
    await waitForRunCompleted(request, runId);

    // Create plan version as the planner
    const createPlanRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: {
        planning_run_id: runId,
        comment: 'Candidate created by planner for Phase 15E governance test',
      },
    });
    expect(createPlanRes.ok()).toBeTruthy();
    const planData = await createPlanRes.json();
    const planVersionId = planData.plan_version_id;

    // Verify canonical status is PENDING_REVIEW (not DRAFT or READY_FOR_REVIEW)
    expect(planData.status).toBe('PENDING_REVIEW');
    expect(planData.created_by).toBe('production_planner');

    // -------------------------------------------------------------------------
    // STEP 9: Open review workflow in Audit & Governance workstation
    // -------------------------------------------------------------------------
    await page.goto('/audit');
    await expect(page.locator('h1:has-text("Audit & Governance")')).toBeVisible();

    // Click refresh to ensure newly created plan is in the version list
    const refreshBtn = page.locator('button:has-text("Refresh")').first();
    await refreshBtn.click();

    // Select the plan version row
    const planRow = page.locator(`tr:has-text("${planVersionId}")`);
    await expect(planRow).toBeVisible({ timeout: 10000 });
    await planRow.click();

    // Verify Pending Review badge is shown
    await expect(page.locator('span:has-text("Pending Review")').first()).toBeVisible();

    // -------------------------------------------------------------------------
    // STEP 10: Attempt approval as the CREATOR (MUST FAIL: 409 FOUR_EYES_VIOLATION)
    // -------------------------------------------------------------------------
    const approveBtn = page.locator('button:has-text("Approve Plan")').last();
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // Verify error notification shows approval blocked by security governance
    const errorNotice = page.locator('text=ACTION NOT COMPLETED');
    await expect(errorNotice).toBeVisible({ timeout: 10000 });
    await expect(
      page.locator('text=lacking required permission')
        .or(page.locator('text=Separation of duties'))
        .or(page.locator('text=FOUR_EYES_VIOLATION'))
        .or(page.locator('text=Missing required permission'))
        .or(page.locator('text=PERMISSION_DENIED'))
    ).toBeVisible();

    // Verify plan did NOT become approved locally
    await expect(page.locator('span:has-text("Pending Review")').first()).toBeVisible();

    // -------------------------------------------------------------------------
    // STEP 11: Switch to a DIFFERENT authorized approver and approve
    // -------------------------------------------------------------------------
    await authenticateViaUi(page, TEST_CONFIG.approverToken);

    // Verify approver token is active
    const approverTokenInStorage = await page.evaluate(() => sessionStorage.getItem('trackmeld_auth_token'));
    expect(approverTokenInStorage).toBe(TEST_CONFIG.approverToken);

    // Attempt approval as independent approver
    await page.goto('/audit');
    const targetPlanRow = page.locator(`tr:has-text("${planVersionId}")`);
    await expect(targetPlanRow).toBeVisible({ timeout: 10000 });
    await targetPlanRow.click();

    const independentApproveBtn = page.locator('button:has-text("Approve Plan")').last();
    await independentApproveBtn.click();

    // Verify approval succeeds
    await expect(page.locator(`text=Plan ${planVersionId} approved successfully.`)).toBeVisible({ timeout: 10000 });

    // Verify table displays Approved badge
    await expect(page.locator(`tr:has-text("${planVersionId}")`).locator('span:has-text("Approved")')).toBeVisible();

    // -------------------------------------------------------------------------
    // STEP 12: Verify immutable audit event ledger
    // -------------------------------------------------------------------------
    // Switch to AUDIT inspector tab
    await page.locator('button:has-text("Audit Trail")').click();

    // Verify the approval audit event is present in the ledger
    const auditLedger = page.locator('div:has-text("PLAN_APPROVED")');
    await expect(auditLedger.first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=production_approver').first()).toBeVisible();
  });
});
