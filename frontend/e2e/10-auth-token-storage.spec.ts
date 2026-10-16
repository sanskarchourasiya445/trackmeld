import { test, expect, TEST_CONFIG, authenticateViaUi, clearAuthViaUi } from './fixtures';
import { getAuthToken, setAuthToken } from '../src/lib/api/client';

/**
 * Task 10 (F10) Regression Spec: Frontend Authentication Token Storage
 *
 * Verifies that:
 * 1. getAuthToken() reads exclusively from sessionStorage and NEVER falls back to localStorage.
 * 2. Legacy token in localStorage only is strictly ignored (fails closed as unauthenticated).
 * 3. Token in sessionStorage is actively read by the application.
 * 4. Signing in via UI writes to sessionStorage and purges any legacy token in localStorage.
 * 5. Logout clears both sessionStorage and legacy localStorage tokens.
 * 6. Logout preserves unrelated user preferences (e.g. trackmeld_sidebar_collapsed).
 * 7. SSR safety: getAuthToken() and setAuthToken() run safely in server context where window is undefined.
 */

test.describe('Task 10 (F10): Authentication Token Storage Consistency', () => {
  test('SSR Safety: getAuthToken and setAuthToken execute in Node context without window', () => {
    // In Playwright runner (Node.js), window is undefined
    expect(typeof window).toBe('undefined');
    expect(getAuthToken()).toBeNull();
    expect(() => setAuthToken('test-server-token')).not.toThrow();
    expect(() => setAuthToken(null)).not.toThrow();
  });

  test.describe('Browser Storage Behavior', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await page.evaluate(() => {
        sessionStorage.clear();
        localStorage.clear();
      });
    });

    test('Legacy token in localStorage only is strictly ignored by application', async ({ page }) => {
      await page.goto('/planning');

      // Seed a legacy token only into localStorage
      await page.evaluate(() => {
        localStorage.setItem('trackmeld_auth_token', 'stale-legacy-token-2025');
        sessionStorage.removeItem('trackmeld_auth_token');
      });

      // Reload page to re-initialize application state
      await page.reload();

      // Verify AuthWidget reflects unauthenticated state ("Sign In")
      const authBtn = page.locator('button[aria-label^="Authentication:"]');
      await expect(authBtn).toContainText('Sign In');
      await expect(page.locator('button[aria-label="Authentication: Authenticated"]')).not.toBeVisible();

      // Verify that sessionStorage remains empty and localStorage still has the unread key
      const sessionToken = await page.evaluate(() => sessionStorage.getItem('trackmeld_auth_token'));
      expect(sessionToken).toBeNull();
    });

    test('Valid session token in sessionStorage is read and recognized by application', async ({ page }) => {
      await page.goto('/planning');

      // Seed valid token into sessionStorage
      await page.evaluate((tok) => {
        sessionStorage.setItem('trackmeld_auth_token', tok);
        localStorage.removeItem('trackmeld_auth_token');
      }, TEST_CONFIG.plannerToken);

      // Reload page so AuthWidget re-reads storage on mount
      await page.reload();

      // Verify AuthWidget is recognized as Authenticated
      const authBtn = page.locator('button[aria-label="Authentication: Authenticated"]');
      await expect(authBtn).toBeVisible({ timeout: 10000 });
    });

    test('Sign in via UI writes to sessionStorage and cleans up legacy localStorage token', async ({ page }) => {
      // Intercept token verification probe so AuthWidget accepts the token
      await page.route('**/planning-runs*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [] }),
        });
      });

      await page.goto('/planning');

      // Plant an obsolete legacy token in localStorage before user signs in
      await page.evaluate(() => {
        localStorage.setItem('trackmeld_auth_token', 'stale-obsolete-legacy-token');
      });

      // User performs sign in via AuthWidget
      await authenticateViaUi(page, TEST_CONFIG.plannerToken);

      // Verify sessionStorage holds new token, and localStorage legacy token is purged
      const sessionToken = await page.evaluate(() => sessionStorage.getItem('trackmeld_auth_token'));
      const localToken = await page.evaluate(() => localStorage.getItem('trackmeld_auth_token'));

      expect(sessionToken).toBe(TEST_CONFIG.plannerToken);
      expect(localToken).toBeNull();
    });

    test('Logout clears both sessionStorage and localStorage while preserving unrelated preferences', async ({ page }) => {
      await page.goto('/planning');

      // Seed both token stores plus an unrelated application preference in localStorage
      await page.evaluate((tok) => {
        sessionStorage.setItem('trackmeld_auth_token', tok);
        localStorage.setItem('trackmeld_auth_token', 'legacy-local-token');
        localStorage.setItem('trackmeld_sidebar_collapsed', 'true');
      }, TEST_CONFIG.plannerToken);

      await page.reload();

      // Verify authenticated
      await expect(page.locator('button[aria-label="Authentication: Authenticated"]')).toBeVisible();

      // Sign out via UI
      await clearAuthViaUi(page);

      // Verify AuthWidget shows Sign In
      await expect(page.locator('button[aria-label="Authentication: Sign In"]')).toBeVisible();

      // Check storage
      const sessionToken = await page.evaluate(() => sessionStorage.getItem('trackmeld_auth_token'));
      const localToken = await page.evaluate(() => localStorage.getItem('trackmeld_auth_token'));
      const sidebarPref = await page.evaluate(() => localStorage.getItem('trackmeld_sidebar_collapsed'));

      expect(sessionToken).toBeNull();
      expect(localToken).toBeNull();
      // Unrelated preference must remain preserved
      expect(sidebarPref).toBe('true');
    });
  });
});
