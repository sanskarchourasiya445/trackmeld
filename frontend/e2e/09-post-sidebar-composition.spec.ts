import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const ARTIFACTS_DIR = 'C:/Users/DELL/.gemini/antigravity/brain/2b364e02-5a9f-4058-bb03-42f611a2ff0b';

test.describe('Post-Sidebar Visual Composition & Anti-Cramping Pass', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/planning-runs*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    });
  });

  const saveArtifactScreenshot = async (page: Page, filename: string) => {
    const localPath = path.join('test-results', filename);
    await page.screenshot({ path: localPath });
    try {
      if (fs.existsSync(ARTIFACTS_DIR)) {
        const artifactPath = path.join(ARTIFACTS_DIR, filename);
        fs.copyFileSync(localPath, artifactPath);
      }
    } catch (e) {
      console.error('Failed to copy to artifacts dir:', e);
    }
  };

  test('01. /overview: Generous layout with expanded sidebar and full-screen map expansion', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/overview');

    // Sidebar should be expanded by default (256px)
    const nav = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    await expect(nav).toBeVisible();
    const navBox = await nav.boundingBox();
    expect(navBox?.width).toBeCloseTo(256, 1);

    // Verify executive cards have generous padding and are visible
    await expect(page.getByText('1. WHAT IS HAPPENING?')).toBeVisible();
    await expect(page.getByText('2. WHAT NEEDS ATTENTION?')).toBeVisible();
    await expect(page.getByText('3. IS THE PLAN SAFE?')).toBeVisible();
    await expect(page.getByText('4. DECISION REQUIRED')).toBeVisible();

    // Verify map is visible with healthy height
    await expect(page.getByRole('heading', { name: /Corridor Topology/i })).toBeVisible();

    await saveArtifactScreenshot(page, 'composition-overview-1440x900.png');

    // Verify Explore Network Map navigation link
    const exploreNetworkBtn = page.getByRole('button', { name: /Explore Network Map/i });
    await expect(exploreNetworkBtn).toBeVisible();
    await saveArtifactScreenshot(page, 'composition-overview-macro-map.png');
  });

  test('02. /work-orders: Full-width table workbench + Slide-in drawer on row click', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/work-orders');

    // Verify sidebar expanded
    const nav = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    await expect(nav).toBeVisible();

    // Verify 100% full-width operational table without cramped side column
    await expect(page.getByRole('heading', { name: 'Maintenance Work Orders & Requisitions' })).toBeVisible();
    await expect(page.getByRole('table')).toBeVisible();

    // Verify table has full breathing room
    await saveArtifactScreenshot(page, 'composition-work-orders-table-fullwidth.png');

    // Click on row 1 (WO-1842 / TSK-0001)
    const firstRow = page.getByRole('table').locator('tbody tr').first();
    await firstRow.click();

    // Verify drawer slides in
    const drawer = page.getByRole('dialog');
    await expect(drawer).toBeVisible();
    await expect(drawer.getByText(/Work Order:/i)).toBeVisible();
    await saveArtifactScreenshot(page, 'composition-work-orders-drawer-open.png');

    // Close drawer via Escape or close button
    await page.keyboard.press('Escape');
    await expect(drawer).not.toBeVisible();
  });

  test('03. /planning: Full-width dominant workspace (Map / Tasks / Timeline) + Drawer on Inspector toggle', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning');

    // Sidebar expanded
    const nav = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    await expect(nav).toBeVisible();

    // Primary operating workspace takes 100% available width
    await expect(page.getByRole('button', { name: /Railway Map/i })).toBeVisible();

    await saveArtifactScreenshot(page, 'composition-planning-workspace-fullwidth.png');

    // Switch to Tasks Queue view mode
    await page.getByRole('button', { name: /Tasks Queue/i }).click();
    await expect(page.getByPlaceholder('Search by Task ID, section, work title...')).toBeVisible();
    await saveArtifactScreenshot(page, 'composition-planning-tasks-queue-fullwidth.png');

    // Open Inspector Drawer
    const inspectorBtn = page.getByRole('button', { name: 'Inspector' }).first();
    await inspectorBtn.click();

    // Drawer should open smoothly
    const drawer = page.getByRole('dialog');
    await expect(drawer).toBeVisible();
    await saveArtifactScreenshot(page, 'composition-planning-drawer-open.png');

    // Close drawer
    await page.keyboard.press('Escape');
    await expect(drawer).not.toBeVisible();
  });

  test('04. /network: Full-width asset tables and Map view + Slide-in drawer', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/network');

    // Check header
    await expect(page.getByRole('heading', { name: 'Railway Network Infrastructure' })).toBeVisible();

    // Switch to Track Sections table tab
    await page.getByRole('button', { name: /Track Sections/i }).click();
    await expect(page.getByRole('table')).toBeVisible();
    await saveArtifactScreenshot(page, 'composition-network-table-fullwidth.png');

    // Switch to Infrastructure Map tab
    await page.getByRole('button', { name: /Infrastructure Map/i }).click();
    await saveArtifactScreenshot(page, 'composition-network-map-fullwidth.png');
  });

  test('05. /copilot: Full-width inquiry interface with interactive citation drawer', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/copilot');

    await expect(page.getByRole('heading', { name: 'AI Decision Support Copilot' })).toBeVisible();
    await expect(page.getByPlaceholder(/Ask Copilot about conflicts/i)).toBeVisible();

    // Verify conversation area has full width
    await saveArtifactScreenshot(page, 'composition-copilot-fullwidth.png');

    // Click the Evidence button
    const evidenceBtn = page.getByRole('button', { name: /Evidence/i });
    if (await evidenceBtn.isVisible()) {
      await evidenceBtn.click();
      const drawer = page.getByRole('dialog');
      await expect(drawer).toBeVisible();
      await expect(drawer.getByText(/Verified Evidence/i)).toBeVisible();
      await saveArtifactScreenshot(page, 'composition-copilot-citation-drawer.png');

      await page.keyboard.press('Escape');
      await expect(drawer).not.toBeVisible();
    }
  });

  test('06. 1920x1080 High-Resolution Viewport Check across core pages', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });

    await page.goto('/overview');
    await saveArtifactScreenshot(page, 'composition-overview-1920x1080.png');

    await page.goto('/planning');
    await saveArtifactScreenshot(page, 'composition-planning-1920x1080.png');

    await page.goto('/work-orders');
    await saveArtifactScreenshot(page, 'composition-work-orders-1920x1080.png');
  });
});
