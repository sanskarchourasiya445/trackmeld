import { test, expect, TEST_CONFIG, authenticateViaUi } from './fixtures';

test.describe('Phase 15E: Truthful UI & Error Resilience E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/planning-runs*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    });
    await page.goto('/');
    await page.evaluate(() => {
      sessionStorage.clear();
      localStorage.clear();
    });
  });

  test('Initial state displays explicit uncomputed notice with no synthetic certification', async ({ page }) => {
    await page.goto('/planning');

    // 1. Initial banner is strictly visible
    const uncomputedBanner = page.locator('text=No schedule computed');
    await expect(uncomputedBanner).toBeVisible();
    await expect(page.locator('text=Planning data is unverified — no approval decision can be made')).toBeVisible();

    // 2. Validation tab must NOT show synthetic VALID badge with 0 errors
    await page.locator('button:has-text("Validation")').click();
    await expect(page.locator('text=STATUS: NOT RUN')).toBeVisible();
    await expect(page.locator('text=No validation data — run optimization to certify schedule')).toBeVisible();

    // 3. Governance review button inside Validation tab must be disabled
    const govBtn = page.locator('button:has-text("Proceed to Governance Review")');
    if (await govBtn.isVisible()) {
      await expect(govBtn).toBeDisabled();
    }
  });

  test('Backend optimization failure produces explicit error and does NOT fall back to demo schedule', async ({ page }) => {
    await authenticateViaUi(page, TEST_CONFIG.plannerToken);
    await page.goto('/planning');

    // Intercept optimization endpoint to return a 503 Service Unavailable
    await page.route('**/api/v1/planning/optimize', (route) => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'SOLVER_UNAVAILABLE',
            message: 'OR-Tools CP-SAT engine is currently experiencing worker exhaustion.',
          },
        }),
      });
    });

    const runOptBtn = page.locator('button:has-text("Run Optimization")');
    await expect(runOptBtn).toBeEnabled();
    await runOptBtn.click();

    // Error banner MUST appear with explicit failure code
    await expect(page.locator('text=OPTIMIZATION UNAVAILABLE')).toBeVisible({ timeout: 10000 });

    // The uncomputed notice must remain — NO synthetic schedule may be shown
    await expect(page.locator('text=No schedule computed')).toBeVisible();
  });

  test('Network disconnection produces explicit unavailable alert without synthetic fallback', async ({ page }) => {
    await authenticateViaUi(page, TEST_CONFIG.plannerToken);
    await page.goto('/planning');

    // Abort network connection for solve endpoint
    await page.route('**/api/v1/planning/optimize', (route) => {
      route.abort('failed');
    });

    const runOptBtn = page.locator('button:has-text("Run Optimization")');
    await expect(runOptBtn).toBeEnabled();
    await runOptBtn.click();

    // Error alert must be shown to the user
    await expect(page.locator('text=OPTIMIZATION UNAVAILABLE')).toBeVisible({ timeout: 10000 });

    // Ensure scheduleResult remains null
    await expect(page.locator('text=No schedule computed')).toBeVisible();
  });

  test('Canonical governance state names: only PENDING_REVIEW, UNDER_REVIEW, APPROVED, REJECTED, SUPERSEDED', async ({ page }) => {
    await page.goto('/audit');

    // Page body should NEVER contain the forbidden deprecated state names as status badges
    const pageHtml = await page.content();
    expect(pageHtml).not.toMatch(/class="[^"]*">Draft<\/span>/i);
    expect(pageHtml).not.toMatch(/class="[^"]*">READY_FOR_REVIEW<\/span>/i);
  });

  test('Approval API failure displays honest error and preserves pending status without local mutation', async ({ page }) => {
    // Intercept approval call to simulate backend failure
    await page.route('**/api/v1/plan-versions/*/approve', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'DATABASE_UNAVAILABLE',
            message: 'PostgreSQL connection failed: cannot commit approval signature',
          },
        }),
      });
    });

    await page.goto('/audit');

    // Click direct Approve Plan button
    const approveBtn = page.getByRole('button', { name: 'Approve Plan' });
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // Honest error banner MUST be visible
    await expect(page.locator('text=ACTION NOT COMPLETED')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=No local state transition has been applied')).toBeVisible();

    // Active plan version must still show PENDING_REVIEW / Active
    await expect(page.locator('text=Plan Version v1.2 (Active)')).toBeVisible();
  });

  test('Audit trail shows DEMO badge when backend is offline and AUTHORITATIVE when backend returns data', async ({ page }) => {
    // 1. When backend is offline or returns error
    await page.route('**/api/v1/plan-versions?scenario_id=*', (route) => {
      route.abort('failed');
    });

    await page.goto('/audit');
    await expect(page.getByText('DEMO AUDIT TRAIL • READ ONLY')).toBeVisible();
    await expect(page.getByText('AUTHORITATIVE BACKEND LEDGER')).not.toBeVisible();

    // 2. When backend returns authoritative data
    await page.route('**/api/v1/plan-versions?scenario_id=*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            plan_version_id: 'PV-AUTH-001',
            scenario_id: 'SCN-DEMO-001',
            planning_run_id: 'RUN-001',
            version_number: 1,
            status: 'PENDING_REVIEW',
            created_at: new Date().toISOString(),
            created_by: 'chief_controller',
            total_scheduled: 29,
            total_unscheduled: 1,
            schedule_identity: 'sha256-auth-identity',
          },
        ]),
      });
    });

    await page.reload();
    await expect(page.getByText('AUTHORITATIVE BACKEND LEDGER')).toBeVisible();
    await expect(page.getByText('DEMO AUDIT TRAIL • READ ONLY')).not.toBeVisible();
  });

  test('Successful approval refreshes authoritative state from backend', async ({ page }) => {
    let approvalCount = 0;

    // Initial plan version is PENDING_REVIEW
    await page.route('**/api/v1/plan-versions?scenario_id=*', (route) => {
      if (approvalCount === 0) {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              plan_version_id: 'PV-AUTH-001',
              scenario_id: 'SCN-DEMO-001',
              planning_run_id: 'RUN-001',
              version_number: 1,
              status: 'PENDING_REVIEW',
              created_at: new Date().toISOString(),
              created_by: 'chief_controller',
              total_scheduled: 29,
              total_unscheduled: 1,
              schedule_identity: 'sha256-auth-identity',
            },
          ]),
        });
      } else {
        // Refreshed plan version after approval
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              plan_version_id: 'PV-AUTH-001',
              scenario_id: 'SCN-DEMO-001',
              planning_run_id: 'RUN-001',
              version_number: 1,
              status: 'APPROVED',
              created_at: new Date().toISOString(),
              created_by: 'chief_controller',
              approved_by: 'divisional_manager',
              total_scheduled: 29,
              total_unscheduled: 1,
              schedule_identity: 'sha256-auth-identity',
            },
          ]),
        });
      }
    });

    // Mock successful approve call
    await page.route('**/api/v1/plan-versions/PV-AUTH-001/approve', (route) => {
      approvalCount++;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plan_version_id: 'PV-AUTH-001',
          scenario_id: 'SCN-DEMO-001',
          planning_run_id: 'RUN-001',
          version_number: 1,
          status: 'APPROVED',
          created_at: new Date().toISOString(),
          created_by: 'chief_controller',
          approved_by: 'divisional_manager',
          total_scheduled: 29,
          total_unscheduled: 1,
          schedule_identity: 'sha256-auth-identity',
        }),
      });
    });

    // Mock audit logs
    await page.route('**/api/v1/plan-versions/PV-AUTH-001/audit', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            event_id: 'EVT-01',
            event_type: 'PLAN_APPROVED',
            actor_username: 'divisional_manager',
            actor_role: 'DIVISIONAL_RAILWAY_MANAGER',
            timestamp: new Date().toISOString(),
            comment: 'Approved under Four-Eyes railway governance.',
          },
        ]),
      });
    });

    await page.goto('/audit');
    await expect(page.getByText('AUTHORITATIVE BACKEND LEDGER')).toBeVisible();

    // Click direct Approve Plan button
    const approveBtn = page.getByRole('button', { name: 'Approve Plan' });
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // Success notification appears
    await expect(page.locator('text=approved successfully')).toBeVisible({ timeout: 5000 });

    // The inspector reflects the refreshed status APPROVED
    await expect(page.locator('text=Plan Version v1 (APPROVED)')).toBeVisible();
  });
});
