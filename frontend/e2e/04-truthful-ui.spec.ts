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

  test('Batch 7: Overview workspace truthfully badges synthetic data and Card 4 links to /governance', async ({ page }) => {
    await page.goto('/overview');

    // Provenance badges on Overview cards
    await expect(page.getByText('DEMO CORRIDOR')).toBeVisible();
    await expect(page.getByText('SIMULATED CONFLICT')).toBeVisible();
    await expect(page.getByText('DEMO BASELINE')).toBeVisible();
    await expect(page.getByText('SYNTHETIC BENCHMARK')).toBeVisible();

    // 1. Overview no longer displays "Validated under 13 safety rules"
    const pageHtml = await page.content();
    expect(pageHtml).not.toContain('Validated under 13 safety rules');
    await expect(page.getByText('Candidate schedule • Subject to independent governance verification')).toBeVisible();

    // 2. The action-required count is explicitly labeled synthetic
    await expect(page.getByText('1 ACTION REQUIRED (SYNTHETIC)')).toBeVisible();

    // Card 4 should link directly to governance workspace rather than popping up a modal
    const card4Link = page.locator('a[href="/governance"]').filter({ hasText: '4. DECISION REQUIRED' });
    await expect(card4Link).toBeVisible();
  });

  test('Batch 7: Governance page shows honest OFFLINE state on backend failure without claiming 13/13 checks passed', async ({ page }) => {
    // Intercept backend call to fail
    await page.route('**/api/v1/plan-versions?scenario_id=*', (route) => {
      route.abort('failed');
    });

    await page.goto('/governance');

    // Must show BACKEND OFFLINE badge and error banner
    await expect(page.getByText('BACKEND OFFLINE')).toBeVisible();
    await expect(page.getByText('Backend Governance Service Unreachable')).toBeVisible();

    // Must NOT claim all 13 checks passed
    const content = await page.content();
    expect(content).not.toContain('ALL CHECKS PASSED (13/13)');
    expect(content).not.toContain('VAL-STRUCT-01');
  });

  test('Batch 7: Governance workspace disables review actions on synthetic demo data', async ({ page }) => {
    // Backend is offline or returns error
    await page.route('**/api/v1/plan-versions?scenario_id=*', (route) => {
      route.abort('failed');
    });

    await page.goto('/governance');
    await expect(page.getByText('BACKEND OFFLINE')).toBeVisible();

    // Select "Inspect Synthetic Demo Scenario"
    await page.getByRole('button', { name: 'Inspect Synthetic Demo Scenario' }).click();

    // Header updates to synthetic read-only badge
    await expect(page.getByText('DEMO AUDIT TRAIL • READ ONLY')).toBeVisible();

    // 3. Review/approval action is disabled and displays Demo Plan — Read Only
    const demoBtn = page.getByRole('button', { name: 'Demo Plan — Read Only' });
    await expect(demoBtn).toBeVisible();
    await expect(demoBtn).toBeDisabled();

    // Modal cannot be opened
    await expect(page.locator('role=dialog')).not.toBeVisible();
  });

  test('Batch 7: Governance workspace allows review actions for real backend plan versions', async ({ page }) => {
    // 4. With a real backend-returned eligible plan version, review action is enabled
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
            validation_status: 'VALID',
            is_approvable: true,
          },
        ]),
      });
    });

    await page.route('**/api/v1/plan-versions/PV-AUTH-001/audit', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/governance');
    await expect(page.getByText('AUTHORITATIVE BACKEND LEDGER')).toBeVisible();

    // Perform Four-Eyes Review button must be ENABLED
    const reviewBtn = page.getByRole('button', { name: 'Perform Four-Eyes Review' });
    await expect(reviewBtn).toBeVisible();
    await expect(reviewBtn).toBeEnabled();

    // Clicking it opens the approval modal
    await reviewBtn.click();
    await expect(page.getByRole('heading', { name: 'Authorize & Approve Plan Version' })).toBeVisible();
  });

  test('Batch 7: Audit page marks locally typed review comments as local session drafts', async ({ page }) => {
    await page.goto('/audit');

    // Switch to Review tab
    await page.getByRole('button', { name: /Review \(\d+\)/ }).click();

    // Initially no fake comments should be present
    await expect(page.getByText('No Review Comments')).toBeVisible();
    expect(await page.content()).not.toContain('S. K. Verma');

    // Add a review comment
    const input = page.getByPlaceholder('Add a review comment...');
    await input.fill('Checking catenary clearance on track 2');
    await page.getByRole('button', { name: 'Post' }).click();

    // Newly posted comment should be labeled as Local Session Draft
    await expect(page.getByText('Checking catenary clearance on track 2')).toBeVisible();
    await expect(page.getByText('Local Session Draft (Not Persisted to Backend)')).toBeVisible();
  });

  test('Batch 7: Planning workspace displays explicit SYNTHETIC FIXTURE badge when demo schedule is loaded', async ({ page }) => {
    await page.goto('/planning');

    // Click Load Demo Schedule
    const loadDemoBtn = page.getByRole('button', { name: 'Load Demo' });
    await loadDemoBtn.click();

    // Top bar must show DEMO SCHEDULE (SYNTHETIC)
    await expect(page.getByText('DEMO SCHEDULE (SYNTHETIC)')).toBeVisible();
  });

  test('Batch 8: Newly optimized schedule associates with exact persisted plan version if identity matches', async ({ page }) => {
    const MATCH_HASH = 'sha256-matching-identity-abc123';

    await authenticateViaUi(page, TEST_CONFIG.plannerToken);

    await page.route('**/api/v1/planning/optimize', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          scenario_id: 'SCN-DEMO-001',
          scheduler_type: 'CP_SAT',
          status: 'OPTIMAL',
          solver_wall_time_seconds: 1.2,
          objective_value: 120,
          best_bound: 120,
          scheduled_tasks: [
            {
              task_id: 'TSK-0001',
              task_code: 'TSK-TRK-001',
              interval: { start: '2026-10-10T07:00:00Z', end: '2026-10-10T10:00:00Z' },
              possession_interval: { start: '2026-10-10T06:45:00Z', end: '2026-10-10T10:15:00Z' },
              duration_minutes: 180,
              affected_sections: ['SEC-ETW-CNB'],
              section_code: 'SEC-ETW-CNB',
              assigned_resources: ['RES-TM-CSM-01'],
              priority_score: 159.5,
              scheduling_reason: 'OPTIMAL',
            },
          ],
          unscheduled_tasks: [],
          metrics: {
            total_tasks: 1,
            scheduled_tasks: 1,
            unscheduled_tasks: 0,
            completion_rate: 1.0,
            mandatory_tasks: 1,
            mandatory_scheduled: 1,
            mandatory_unscheduled: 0,
            mandatory_completion_rate: 1.0,
            total_scheduled_duration_minutes: 180,
            total_possession_duration_minutes: 210,
            priority_score_capture_rate: 1.0,
            total_requested_tasks: 1,
            completion_rate_pct: 100,
          },
        }),
      });
    });

    await page.route('**/api/v1/planning/validate', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'VALID',
          valid: true,
          error_count: 0,
          warning_count: 0,
          schedule_identity: MATCH_HASH,
          is_approvable: true,
          checked_task_count: 29,
          findings: [],
        }),
      });
    });

    await page.route('**/api/v1/planning/diagnose', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ diagnostics: [] }),
      });
    });

    await page.route('**/api/v1/plan-versions*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            plan_version_id: 'PV-EXACT-001',
            scenario_id: 'SCN-DEMO-001',
            planning_run_id: 'RUN-001',
            version_number: 1,
            status: 'PENDING_REVIEW',
            created_at: new Date().toISOString(),
            created_by: 'chief_controller',
            total_scheduled: 29,
            total_unscheduled: 0,
            schedule_identity: MATCH_HASH,
          },
        ]),
      });
    });

    await page.goto('/planning');
    const runOptBtn = page.getByRole('button', { name: 'Run Optimization' });
    await expect(runOptBtn).toBeEnabled();
    await runOptBtn.click();

    // Stage 3 status must become PENDING FOUR-EYES
    await expect(page.getByText('PENDING FOUR-EYES')).toBeVisible({ timeout: 10000 });

    // Approve button must be enabled
    const approveBtn = page.getByRole('button', { name: 'Approve' });
    await expect(approveBtn).toBeEnabled();
    await approveBtn.click();

    // Approval modal must open displaying the exact persisted version and matching identity
    await expect(page.getByText('Plan Version 1 • Immutable Four-Eyes Governance Gate')).toBeVisible();
    await expect(page.getByText(MATCH_HASH)).toBeVisible();
  });

  test('Batch 8: Unpersisted schedule candidate never binds older unrelated plan version and blocks approval', async ({ page }) => {
    const NEW_SOLVE_HASH = 'sha256-newly-optimized-cand-999';
    const OLDER_VERSION_HASH = 'sha256-older-different-version-000';

    await authenticateViaUi(page, TEST_CONFIG.plannerToken);

    await page.route('**/api/v1/planning/optimize', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          scenario_id: 'SCN-DEMO-001',
          scheduler_type: 'CP_SAT',
          status: 'OPTIMAL',
          solver_wall_time_seconds: 1.0,
          objective_value: 95,
          best_bound: 95,
          scheduled_tasks: [
            {
              task_id: 'TSK-0001',
              task_code: 'TSK-TRK-001',
              interval: { start: '2026-10-10T07:00:00Z', end: '2026-10-10T10:00:00Z' },
              possession_interval: { start: '2026-10-10T06:45:00Z', end: '2026-10-10T10:15:00Z' },
              duration_minutes: 180,
              affected_sections: ['SEC-ETW-CNB'],
              section_code: 'SEC-ETW-CNB',
              assigned_resources: ['RES-TM-CSM-01'],
              priority_score: 159.5,
              scheduling_reason: 'OPTIMAL',
            },
          ],
          unscheduled_tasks: [],
          metrics: {
            total_tasks: 1,
            scheduled_tasks: 1,
            unscheduled_tasks: 0,
            completion_rate: 1.0,
            mandatory_tasks: 1,
            mandatory_scheduled: 1,
            mandatory_unscheduled: 0,
            mandatory_completion_rate: 1.0,
            total_scheduled_duration_minutes: 180,
            total_possession_duration_minutes: 210,
            priority_score_capture_rate: 1.0,
            total_requested_tasks: 1,
            completion_rate_pct: 100,
          },
        }),
      });
    });

    await page.route('**/api/v1/planning/validate', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'VALID',
          valid: true,
          error_count: 0,
          warning_count: 0,
          schedule_identity: NEW_SOLVE_HASH,
          is_approvable: true,
          checked_task_count: 29,
          findings: [],
        }),
      });
    });

    await page.route('**/api/v1/planning/diagnose', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ diagnostics: [] }),
      });
    });

    // Backend has an older plan version, but NOT one matching the newly optimized schedule
    await page.route('**/api/v1/plan-versions*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            plan_version_id: 'PV-OLD-001',
            scenario_id: 'SCN-DEMO-001',
            planning_run_id: 'RUN-OLD',
            version_number: 1,
            status: 'PENDING_REVIEW',
            created_at: new Date().toISOString(),
            created_by: 'old_planner',
            total_scheduled: 15,
            total_unscheduled: 14,
            schedule_identity: OLDER_VERSION_HASH,
          },
        ]),
      });
    });

    await page.goto('/planning');
    const runOptBtn = page.getByRole('button', { name: 'Run Optimization' });
    await expect(runOptBtn).toBeEnabled();
    await runOptBtn.click();

    // Stage 3 status MUST show UNPERSISTED CANDIDATE, NOT PENDING FOUR-EYES
    await expect(page.getByText('UNPERSISTED CANDIDATE')).toBeVisible({ timeout: 10000 });

    // Header action button must show Unpersisted Plan and be disabled
    const unpersistedBtn = page.getByRole('button', { name: 'Unpersisted Plan' });
    await expect(unpersistedBtn).toBeVisible();
    await expect(unpersistedBtn).toBeDisabled();

    // In Validation view, Proceed to Governance Review must be disabled and show UNPERSISTED CANDIDATE
    await page.getByRole('button', { name: 'Validate' }).click();
    await expect(page.getByText('UNPERSISTED CANDIDATE').first()).toBeVisible();
    const govBtn = page.getByRole('button', { name: 'Proceed to Governance Review' });
    await expect(govBtn).toBeDisabled();
  });

  test('Batch 8: Governance workspace detects identity mismatch between plan version and validation summary', async ({ page }) => {
    await page.route('**/api/v1/plan-versions?scenario_id=*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            plan_version_id: 'PV-TAMPER-001',
            scenario_id: 'SCN-DEMO-001',
            planning_run_id: 'RUN-001',
            version_number: 1,
            status: 'PENDING_REVIEW',
            created_at: new Date().toISOString(),
            created_by: 'planner',
            total_scheduled: 29,
            total_unscheduled: 0,
            schedule_identity: 'sha256-version-expected-hash',
            schedule_result: {
              validation_summary: {
                valid: true,
                is_approvable: true,
                schedule_identity: 'sha256-mismatched-validation-hash',
              },
            },
          },
        ]),
      });
    });

    await page.route('**/api/v1/plan-versions/PV-TAMPER-001/audit', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/governance');

    // Cryptographic Identity Mismatch warning banner must appear
    await expect(page.getByText('Cryptographic Identity Mismatch:')).toBeVisible();

    // Review button must display Identity Mismatch and be disabled
    const mismatchBtn = page.getByRole('button', { name: 'Identity Mismatch' });
    await expect(mismatchBtn).toBeVisible();
    await expect(mismatchBtn).toBeDisabled();
  });

  test('Batch 10: Governance workspace displays Validation Incomplete and disables review when plan version is uncertified or invalid', async ({ page }) => {
    await page.route('**/api/v1/plan-versions?scenario_id=*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            plan_version_id: 'PV-UNVERIFIED-001',
            scenario_id: 'SCN-DEMO-001',
            planning_run_id: 'RUN-001',
            version_number: 1,
            status: 'PENDING_REVIEW',
            created_at: new Date().toISOString(),
            created_by: 'planner',
            total_scheduled: 25,
            total_unscheduled: 5,
            schedule_identity: 'sha256-unverified-identity',
            validation_status: 'INVALID',
            is_approvable: false,
          },
        ]),
      });
    });

    await page.route('**/api/v1/plan-versions/PV-UNVERIFIED-001/audit', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/governance');
    await expect(page.getByText('AUTHORITATIVE BACKEND LEDGER')).toBeVisible();

    // Review button must show Validation Incomplete and be disabled
    const incompleteBtn = page.getByRole('button', { name: 'Validation Incomplete' });
    await expect(incompleteBtn).toBeVisible();
    await expect(incompleteBtn).toBeDisabled();

    // Modal cannot be opened
    await expect(page.locator('role=dialog')).not.toBeVisible();
  });

  test('Batch 15: Governance workspace displays honest unavailable indicator when approved plan has null or empty approved_by', async ({ page }) => {
    await page.route('**/api/v1/plan-versions?scenario_id=*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            plan_version_id: 'PV-NULL-APPROVER-001',
            scenario_id: 'SCN-DEMO-001',
            planning_run_id: 'RUN-001',
            version_number: 1,
            status: 'APPROVED',
            created_at: new Date().toISOString(),
            created_by: 'planner_admin',
            approved_by: null,
            total_scheduled: 29,
            total_unscheduled: 0,
            schedule_identity: 'sha256-approved-valid-identity',
            validation_status: 'VALID',
            is_approvable: true,
          },
        ]),
      });
    });

    await page.route('**/api/v1/plan-versions/PV-NULL-APPROVER-001/audit', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/governance');
    await expect(page.getByText('AUTHORITATIVE BACKEND LEDGER')).toBeVisible();

    // Four-Eyes role segregation card must display APPROVED BY: and honest unavailable indicator '—'
    await expect(page.getByText('APPROVED BY:')).toBeVisible();
    await expect(page.getByText('ops_executive_officer')).not.toBeVisible();

    const approverContainer = page.locator('div', { hasText: 'APPROVED BY:' }).last();
    await expect(approverContainer).toContainText('—');
  });
});
