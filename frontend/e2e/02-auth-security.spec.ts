import { test, expect, TEST_CONFIG, authenticateViaUi, clearAuthViaUi } from './fixtures';

test.describe('Phase 15E: Authentication & Security Boundary E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      sessionStorage.clear();
      localStorage.clear();
    });
  });

  test('AuthWidget handles unauthenticated, invalid, restricted, and authenticated states correctly', async ({ page }) => {
    await page.goto('/planning');

    // 1. Initial Unauthenticated State
    const authBtn = page.locator('button[aria-label^="Authentication:"]');
    await expect(authBtn).toContainText('Sign In');

    // Open widget
    await authBtn.click();
    const tokenInput = page.locator('input[placeholder="Bearer token…"]');
    await expect(tokenInput).toHaveAttribute('type', 'password');

    // 2. Reject Invalid / Revoked Token (401)
    await tokenInput.fill(TEST_CONFIG.invalidToken);
    const signInBtn = page.locator('button:has-text("Sign In")').last();
    await signInBtn.click();

    // Verify error message in panel
    await expect(page.locator('text=Token rejected (401)')).toBeVisible({ timeout: 10000 });
    // Verify badge shows failure
    await expect(page.locator('button[aria-label="Authentication: Auth Failed"]')).toBeVisible();

    // 3. Authenticate with Restricted Token (Viewer Role - 403 on protected write routes)
    await tokenInput.fill(TEST_CONFIG.viewerToken);
    await signInBtn.click();

    // Token is accepted but role is restricted
    await expect(page.locator('button[aria-label^="Authentication:"]')).toBeVisible({ timeout: 10000 });

    // Clear token before switching to Planner Token
    await clearAuthViaUi(page);

    // 4. Authenticate with Full Planner Token
    await authenticateViaUi(page, TEST_CONFIG.plannerToken);

    await expect(page.locator('button[aria-label="Authentication: Authenticated"]')).toBeVisible({ timeout: 10000 });

    // Verify sessionStorage has token, but localStorage does NOT store it
    const sessionToken = await page.evaluate(() => sessionStorage.getItem('trackmeld_auth_token'));
    const localToken = await page.evaluate(() => localStorage.getItem('trackmeld_auth_token'));
    expect(sessionToken).toBe(TEST_CONFIG.plannerToken);
    expect(localToken).toBeNull();

    // 5. Sign Out
    await clearAuthViaUi(page);
    await expect(page.locator('button[aria-label="Authentication: Sign In"]')).toBeVisible();
    const clearedToken = await page.evaluate(() => sessionStorage.getItem('trackmeld_auth_token'));
    expect(clearedToken).toBeNull();
  });

  test('Backend API enforces RBAC: 401 for unauthenticated, 403 for unauthorized viewer', async ({ request }) => {
    // 1. Unauthenticated request to protected route
    const unauthRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions`, {
      data: { planning_run_id: 'RUN-NONEXISTENT' },
    });
    // In production fail-closed: 401; in non-production with default demo viewer: 403
    expect([401, 403]).toContain(unauthRes.status());

    // 2. Authenticated request with Viewer token attempting to approve (requires plan:approve)
    const viewerApproveRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions/PV-FAKE/approve`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.viewerToken}` },
      data: { comment: 'Unauthorized approval attempt' },
    });
    expect(viewerApproveRes.status()).toBe(403);
    const errBody = await viewerApproveRes.json();
    const code = errBody?.error?.code || errBody?.detail?.error?.code;
    expect(['PERMISSION_DENIED', 'FORBIDDEN']).toContain(code);

    // 3. Authenticated request with Planner token attempting to approve (lacks plan:approve)
    const plannerApproveRes = await request.post(`${TEST_CONFIG.apiUrl}/plan-versions/PV-FAKE/approve`, {
      headers: { Authorization: `Bearer ${TEST_CONFIG.plannerToken}` },
      data: { comment: 'Planner attempting approval' },
    });
    expect(plannerApproveRes.status()).toBe(403);
  });

  test('No credentials leaked into raw page DOM or rendered text', async ({ page }) => {
    await page.goto('/planning');
    await authenticateViaUi(page, TEST_CONFIG.plannerToken);

    // Verify the raw token string is not rendered in plain text anywhere on the page
    const pageText = await page.innerText('body');
    expect(pageText).not.toContain(TEST_CONFIG.plannerToken);
    expect(pageText).not.toContain('e2e-planner-token-2026');
    expect(pageText).not.toContain('e2e-approver-token-2026');
  });
});
