import { test as base, expect, Page, APIRequestContext } from '@playwright/test';

export const TEST_CONFIG = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001/api/v1',
  plannerToken: process.env.TEST_PLANNER_TOKEN || 'e2e-planner-token-2026',
  approverToken: process.env.TEST_APPROVER_TOKEN || 'e2e-approver-token-2026',
  adminToken: process.env.TEST_ADMIN_TOKEN || 'admin-token-2026',
  viewerToken: process.env.TEST_VIEWER_TOKEN || 'e2e-viewer-token-2026',
  invalidToken: 'invalid-revoked-token-9999',
  scenarioId: 'SCN-DEMO-001',
};

/**
 * Authenticate the current browser page via the Phase 15D TopBar AuthWidget.
 */
export async function authenticateViaUi(page: Page, token: string): Promise<void> {
  const currentUrl = page.url();
  if (currentUrl === 'about:blank' || (!currentUrl.includes('/planning') && !currentUrl.includes('/audit') && !currentUrl.includes('/overview'))) {
    await page.goto('/planning');
  }
  const authTrigger = page.locator('button[aria-label^="Authentication:"]');
  await authTrigger.click();

  // If already authenticated or forbidden, sign out first to reveal sign-in form
  const signOutButton = page.locator('button:has-text("Clear token / Sign out")');
  if (await signOutButton.isVisible()) {
    await signOutButton.click();
    await authTrigger.click();
  }

  const tokenInput = page.locator('input[placeholder="Bearer token…"]');
  await expect(tokenInput).toBeVisible();
  await tokenInput.fill(token);

  const submitButton = page.locator('button:has-text("Sign In")').last();
  await submitButton.click();

  // Verify badge shows authenticated
  await expect(page.locator('button[aria-label="Authentication: Authenticated"]')).toBeVisible({
    timeout: 10000,
  });

  // Verify token is in sessionStorage
  const stored = await page.evaluate(() => sessionStorage.getItem('trackmeld_auth_token'));
  expect(stored).toBe(token);

  // Close panel if still open
  const closeButton = page.locator('button[aria-label="Close"]');
  if (await closeButton.isVisible()) {
    await closeButton.click();
  }
}

/**
 * Poll until an asynchronous planning run reaches COMPLETED status.
 */
export async function waitForRunCompleted(
  request: APIRequestContext,
  runId: string,
  maxWaitMs = 15000
): Promise<Record<string, unknown>> {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    const res = await request.get(`${TEST_CONFIG.apiUrl}/planning-runs/${runId}`);
    if (res.ok()) {
      const data = await res.json();
      if (data.status === 'COMPLETED') return data;
      if (['FAILED', 'TIMED_OUT', 'CANCELLED'].includes(data.status)) {
        throw new Error(`Run ${runId} terminated prematurely with status: ${data.status}`);
      }
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`Run ${runId} did not complete within ${maxWaitMs}ms`);
}

/**
 * Sign out / clear token via AuthWidget.
 */
export async function clearAuthViaUi(page: Page): Promise<void> {
  const authTrigger = page.locator('button[aria-label^="Authentication:"]');
  await authTrigger.click();

  const signOutButton = page.locator('button:has-text("Clear token / Sign out")');
  await expect(signOutButton).toBeVisible();
  await signOutButton.click();

  await expect(page.locator('button[aria-label="Authentication: Sign In"]')).toBeVisible();

  const stored = await page.evaluate(() => sessionStorage.getItem('trackmeld_auth_token'));
  expect(stored).toBeNull();
}

/**
 * Directly inject token into page sessionStorage before navigation.
 */
export async function injectSessionToken(page: Page, token: string | null): Promise<void> {
  await page.addInitScript((tok) => {
    if (tok) {
      sessionStorage.setItem('trackmeld_auth_token', tok);
    } else {
      sessionStorage.removeItem('trackmeld_auth_token');
    }
  }, token);
}

export const test = base;
export { expect };
