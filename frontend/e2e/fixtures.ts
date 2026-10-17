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
  const tokenInput = page.locator('input[placeholder="Bearer token…"]');
  const signOutButton = page.locator('button:has-text("Clear token / Sign out")');

  // Open panel with retry in case click was intercepted during React hydration
  for (let attempt = 0; attempt < 4; attempt++) {
    if ((await tokenInput.isVisible()) || (await signOutButton.isVisible())) break;
    await authTrigger.evaluate((el: HTMLElement) => el.click()).catch(() => authTrigger.click({ force: true }));
    try {
      await expect(tokenInput.or(signOutButton)).toBeVisible({ timeout: 2000 });
      break;
    } catch {
      await page.waitForTimeout(400);
    }
  }

  // If already authenticated or forbidden, sign out first to reveal sign-in form
  if (await signOutButton.isVisible()) {
    await signOutButton.evaluate((el: HTMLElement) => el.click()).catch(() => signOutButton.click({ force: true }));
    for (let attempt = 0; attempt < 4; attempt++) {
      if (await tokenInput.isVisible()) break;
      await authTrigger.evaluate((el: HTMLElement) => el.click()).catch(() => authTrigger.click({ force: true }));
      try {
        await expect(tokenInput).toBeVisible({ timeout: 2000 });
        break;
      } catch {
        await page.waitForTimeout(400);
      }
    }
  }

  await expect(tokenInput).toBeVisible({ timeout: 10000 });
  await tokenInput.fill(token);

  const submitButton = page.locator('button:has-text("Sign In")').last();
  await submitButton.click({ force: true });

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
    await closeButton.click({ force: true });
  }
}

/**
 * Poll until an asynchronous planning run reaches COMPLETED status.
 */
export async function waitForRunCompleted(
  request: APIRequestContext,
  runId: string,
  maxWaitMs = 15000,
  token?: string
): Promise<Record<string, unknown>> {
  const start = Date.now();
  const authToken = token || TEST_CONFIG.plannerToken;
  while (Date.now() - start < maxWaitMs) {
    const res = await request.get(`${TEST_CONFIG.apiUrl}/planning-runs/${runId}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
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
  const signOutButton = page.locator('button:has-text("Clear token / Sign out")');
  const authTrigger = page.locator('button[aria-label^="Authentication:"]');

  for (let attempt = 0; attempt < 4; attempt++) {
    if (await signOutButton.isVisible()) break;
    await authTrigger.evaluate((el: HTMLElement) => el.click()).catch(() => authTrigger.click({ force: true }));
    try {
      await expect(signOutButton).toBeVisible({ timeout: 2000 });
      break;
    } catch {
      await page.waitForTimeout(400);
    }
  }

  await expect(signOutButton).toBeVisible({ timeout: 10000 });
  await signOutButton.evaluate((el: HTMLElement) => el.click()).catch(() => signOutButton.click({ force: true }));

  await expect(page.locator('button[aria-label="Authentication: Sign In"]')).toBeVisible({ timeout: 10000 });

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

export const test = base.extend({
  page: async ({ page }, use) => {
    // Fail-closed safety guard: Intercept browser requests to port 8000 and reroute to test backend port 8001
    await page.route('**/api/v1/**', async (route) => {
      const reqUrl = route.request().url();
      if (reqUrl.includes(':8000/api/v1/')) {
        const redirected = reqUrl.replace(':8000/api/v1/', ':8001/api/v1/');
        await route.continue({ url: redirected });
      } else {
        await route.continue();
      }
    });

    // Suppress Next.js dev overlay / portal to prevent it from overlaying UI buttons in tests
    await page.addInitScript(() => {
      const style = document.createElement('style');
      style.innerHTML = 'nextjs-portal, [id^="__next-build-watcher"], [data-nextjs-toast] { display: none !important; pointer-events: none !important; visibility: hidden !important; }';
      document.head ? document.head.appendChild(style) : document.addEventListener('DOMContentLoaded', () => document.head?.appendChild(style));
    });

    await use(page);
  },
});
export { expect };
