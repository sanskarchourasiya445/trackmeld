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
});
