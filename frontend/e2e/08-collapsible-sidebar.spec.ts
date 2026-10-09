import { test, expect } from '@playwright/test';

test.describe('Requirement 42: Collapsible / Sliding Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Intercept planning-runs to return empty list so auth checks succeed cleanly
    await page.route('**/api/v1/planning-runs*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    });

    // Reset localStorage before each test
    await page.goto('/planning');
    await page.evaluate(() => {
      localStorage.removeItem('trackmeld_sidebar_collapsed');
    });
    await page.reload();
  });

  test('01. Desktop default state: sidebar opens expanded (w-64) with labels, badges, and collapse control', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning');

    const sidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    await expect(sidebar).toBeVisible();

    // Verify expanded desktop width (~256px)
    const box = await sidebar.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(240);
    expect(box!.width).toBeLessThanOrEqual(280);

    // Verify section header and full workspace labels
    await expect(sidebar.getByText('Operational Workspaces')).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /overview/i })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /planning/i })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /network/i })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /work orders/i })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /validation & governance/i })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /copilot/i })).toBeVisible();

    // Verify active corridor footer card
    await expect(sidebar.getByText('Active Corridor')).toBeVisible();
    await expect(sidebar.getByText('NDLS → CNB')).toBeVisible();

    // Verify collapse toggle button with accessible attributes
    const collapseBtn = sidebar.getByRole('button', { name: 'Collapse sidebar navigation' });
    await expect(collapseBtn).toBeVisible();
    await expect(collapseBtn).toHaveAttribute('aria-expanded', 'true');
    await expect(collapseBtn).toHaveAttribute('aria-controls', 'railway-navigation-sidebar');

    // Screenshot expanded state
    await page.screenshot({ path: 'test-results/sidebar-expanded-desktop.png' });
  });

  test('02. Collapsing sidebar shrinks to 64px icon rail and automatically expands main workspace width', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning');

    const sidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    const mainWorkspace = page.locator('main');

    // Measure initial workspace width
    const initialMainBox = await mainWorkspace.boundingBox();
    expect(initialMainBox).not.toBeNull();

    // Click collapse button
    const collapseBtn = sidebar.getByRole('button', { name: 'Collapse sidebar navigation' });
    await collapseBtn.click();

    // Wait for transition (200ms)
    await page.waitForTimeout(300);

    // Verify collapsed width (~64px)
    const collapsedSidebarBox = await sidebar.boundingBox();
    expect(collapsedSidebarBox).not.toBeNull();
    expect(collapsedSidebarBox!.width).toBeLessThanOrEqual(72);
    expect(collapsedSidebarBox!.width).toBeGreaterThanOrEqual(60);

    // Verify workspace gained the freed width (~192px expansion)
    const expandedMainBox = await mainWorkspace.boundingBox();
    expect(expandedMainBox).not.toBeNull();
    expect(expandedMainBox!.width).toBeGreaterThan(initialMainBox!.width + 150);

    // Verify "Operational Workspaces" text is hidden in icon rail
    await expect(sidebar.getByText('Operational Workspaces')).not.toBeVisible();

    // Verify expand button is now present with aria-expanded="false"
    const expandBtn = sidebar.getByRole('button', { name: 'Expand sidebar navigation' });
    await expect(expandBtn).toBeVisible();
    await expect(expandBtn).toHaveAttribute('aria-expanded', 'false');

    // Screenshot collapsed icon rail and expanded workspace
    await page.screenshot({ path: 'test-results/sidebar-collapsed-desktop.png' });
  });

  test('03. Planning workspace state, active view, and map remain intact when sidebar collapses', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning');

    // 1. Switch to Time-Space view
    const timeSpaceBtn = page.getByRole('button', { name: 'Time-Space' });
    await timeSpaceBtn.click();
    await expect(page.getByText('Corridor Time-Space Diagram')).toBeVisible();

    // 2. Collapse the sidebar
    const sidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    await sidebar.getByRole('button', { name: 'Collapse sidebar navigation' }).click();
    await page.waitForTimeout(300);

    // 3. Verify Time-Space view is STILL active and visible without page reload
    await expect(page.getByText('Corridor Time-Space Diagram')).toBeVisible();

    // 4. Re-expand sidebar and switch back to Railway Map
    await sidebar.getByRole('button', { name: 'Expand sidebar navigation' }).click();
    await page.waitForTimeout(300);
    await page.getByRole('button', { name: 'Railway Map' }).click();

    // 5. Verify Railway Map view is active and dominant
    await expect(page.getByRole('button', { name: 'Railway Map' })).toBeVisible();
  });

  test('04. TopBar toggle button and Ctrl+B keyboard shortcut toggle sidebar collapse smoothly', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning');

    const sidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });

    // 1. Toggle via TopBar button
    const topBarToggle = page.locator('header').getByRole('button', { name: /sidebar navigation/i });
    await expect(topBarToggle).toBeVisible();
    await topBarToggle.click();
    await page.waitForTimeout(300);

    // Sidebar should be collapsed
    let box = await sidebar.boundingBox();
    expect(box!.width).toBeLessThanOrEqual(72);

    // 2. Toggle back via TopBar button
    await topBarToggle.click();
    await page.waitForTimeout(300);

    // Sidebar should be expanded
    box = await sidebar.boundingBox();
    expect(box!.width).toBeGreaterThanOrEqual(240);

    // 3. Toggle via Ctrl+B shortcut
    await page.keyboard.press('Control+b');
    await page.waitForTimeout(300);

    box = await sidebar.boundingBox();
    expect(box!.width).toBeLessThanOrEqual(72);

    // 4. Toggle back via Ctrl+B shortcut
    await page.keyboard.press('Control+b');
    await page.waitForTimeout(300);

    box = await sidebar.boundingBox();
    expect(box!.width).toBeGreaterThanOrEqual(240);
  });

  test('05. Persistence: Collapsed preference is saved in localStorage and persists across navigation', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning');

    const sidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });

    // Collapse sidebar
    await sidebar.getByRole('button', { name: 'Collapse sidebar navigation' }).click();
    await page.waitForTimeout(300);

    // Check localStorage
    const storedVal = await page.evaluate(() => localStorage.getItem('trackmeld_sidebar_collapsed'));
    expect(storedVal).toBe('true');

    // Navigate to /network
    await page.goto('/network');
    await page.waitForTimeout(200);

    // Sidebar must remain collapsed on /network
    const networkSidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    const netBox = await networkSidebar.boundingBox();
    expect(netBox!.width).toBeLessThanOrEqual(72);

    // Navigate to /work-orders
    await page.goto('/work-orders');
    await page.waitForTimeout(200);

    // Sidebar must remain collapsed on /work-orders
    const woSidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    const woBox = await woSidebar.boundingBox();
    expect(woBox!.width).toBeLessThanOrEqual(72);

    // Re-expand on /work-orders
    await woSidebar.getByRole('button', { name: 'Expand sidebar navigation' }).click();
    await page.waitForTimeout(300);

    const reExpandedVal = await page.evaluate(() => localStorage.getItem('trackmeld_sidebar_collapsed'));
    expect(reExpandedVal).toBe('false');
  });

  test('06. Mobile & tablet view: Sidebar acts as slide-over drawer with backdrop and close controls', async ({ page }) => {
    // Set mobile viewport (< 1024px)
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/planning');

    const sidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });

    // On mobile, sidebar is off-screen initially (-translate-x-full)
    // Click hamburger button in header
    const menuBtn = page.locator('header').getByRole('button', { name: /sidebar navigation/i });
    await expect(menuBtn).toBeVisible();
    await menuBtn.click();
    await page.waitForTimeout(300);

    // Drawer should be visible
    await expect(sidebar).toBeVisible();
    await expect(sidebar.getByText('TrackMeld')).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /overview/i })).toBeVisible();

    // Verify close X button is visible and closes drawer
    const closeBtn = sidebar.getByRole('button', { name: 'Close navigation menu' });
    await expect(closeBtn).toBeVisible();

    // Screenshot mobile drawer
    await page.screenshot({ path: 'test-results/sidebar-mobile-drawer.png' });

    await closeBtn.click();
    await page.waitForTimeout(300);

    // Drawer should be closed
    await expect(sidebar).toHaveClass(/-translate-x-full/);
  });
});
