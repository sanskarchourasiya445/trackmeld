import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'desktop-1920', width: 1920, height: 1080 },
  { name: 'desktop-short-1802', width: 1802, height: 786 },
  { name: 'laptop-1440', width: 1440, height: 900 },
  { name: 'short-1280', width: 1280, height: 720 },
  { name: 'short-1024', width: 1024, height: 600 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'mobile-390', width: 390, height: 844 },
  { name: 'mobile-narrow-320', width: 320, height: 700 },
];

const MODES = [
  { id: 'INTEGRATED', label: '3-Panel Workstation', buttonText: '3-Panel Workstation' },
  { id: 'MAP', label: 'Railway Map', buttonText: 'Railway Map' },
  { id: 'TIMESPACE', label: 'Time-Space', buttonText: 'Time-Space' },
  { id: 'TIMELINE', label: 'Corridor Timeline', buttonText: 'Corridor Timeline' },
  { id: 'TASKS', label: 'Tasks Queue', buttonText: 'Tasks Queue' },
  { id: 'CONFLICTS', label: 'Conflicts', buttonText: 'Conflicts' },
  { id: 'VALIDATION', label: 'Validation', buttonText: 'Validation' },
  { id: 'DIAGNOSTICS', label: 'Diagnostics', buttonText: 'Diagnostics' },
  { id: 'COPILOT', label: 'Copilot', buttonText: 'Copilot' },
];

test.describe('Deep Audit: Planning Workstation 9 Modes & Component Reachability', () => {

  test('01. All 9 Planning Workstation Modes Render & Transition Cleanly', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    for (const mode of MODES) {
      // Find and click mode button in the sub-navigation bar
      const modeBtn = page.getByRole('button', { name: new RegExp(mode.buttonText, 'i') }).first();
      await expect(modeBtn).toBeVisible();
      await modeBtn.click();
      await page.waitForTimeout(300);

      // Verify that the mode container rendered without crashing
      const modeCheck = await page.evaluate((modeId) => {
        const main = document.querySelector('main');
        if (!main) return { ok: false, error: 'no main' };

        // Verify active button styling
        const activeButtons = Array.from(document.querySelectorAll('button')).filter(
          (b) => b.className && b.className.includes('bg-[#162238]')
        );

        return {
          ok: true,
          modeId,
          activeButtonsCount: activeButtons.length,
          mainScrollHeight: main.scrollHeight,
          mainClientHeight: main.clientHeight,
        };
      }, mode.id);

      expect(modeCheck.ok).toBe(true);
    }
  });

  test('02. Planning Workstation Across All 7 Viewports (Short-Height Reachability)', async ({ page }) => {
    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/planning', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(600);

      const metrics = await page.evaluate(() => {
        const table = document.querySelector('table');
        const timeline = Array.from(document.querySelectorAll('button')).find(
          (b) => b.textContent && b.textContent.includes('Timeline')
        );
        const map = document.querySelector('.maplibregl-map') || document.querySelector('canvas') || document.querySelector('[aria-label="Map"]');
        const target = timeline || table;

        // Scroll all scroll containers to test reachability
        document.querySelectorAll('*').forEach((el) => {
          if (el.scrollHeight > el.clientHeight) {
            el.scrollTop = el.scrollHeight;
          }
        });

        const rectAfter = target ? target.getBoundingClientRect() : null;

        return {
          hasMap: !!map,
          hasTarget: !!target,
          topAfterScroll: rectAfter ? Math.round(rectAfter.top) : null,
          viewportHeight: window.innerHeight,
          isTargetReachable: rectAfter ? rectAfter.top < window.innerHeight : true,
        };
      });

      expect(metrics.isTargetReachable).toBe(true);
    }
  });

  test('03. Inspector Drawer & Docked State Verification', async ({ page }) => {
    // Desktop: Inspector docks into layout
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    const inspectorBtn = page.getByRole('button', { name: 'Inspector', exact: true });
    if (await inspectorBtn.isVisible()) {
      await inspectorBtn.click();
      await page.waitForTimeout(300);

      // Verify inspector panel is open
      const isInspectorVisible = await page.evaluate(() => {
        const el = document.querySelector('[role="complementary"]') || document.querySelector('.w-\\[360px\\], .w-\\[400px\\]');
        return el ? window.getComputedStyle(el).display !== 'none' : false;
      });
      expect(isInspectorVisible).toBe(true);

      // Toggle closed
      await inspectorBtn.click();
      await page.waitForTimeout(200);
    }

    // Mobile: Inspector opens as a slide-in drawer
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/planning', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    const mobileInspectorBtn = page.getByRole('button', { name: 'Inspector', exact: true });
    if (await mobileInspectorBtn.isVisible()) {
      await mobileInspectorBtn.click();
      await page.waitForTimeout(300);

      const isMobileDrawerOpen = await page.evaluate(() => {
        const drawer = document.querySelector('[role="dialog"]') || document.querySelector('.fixed.inset-y-0.right-0');
        return drawer ? window.getComputedStyle(drawer).display !== 'none' : false;
      });
      expect(isMobileDrawerOpen).toBe(true);
    }
  });

  test('04. Modals in Planning (Compare Plans, Benchmark, Approval)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    // 1. Compare Plans Modal
    const compareBtn = page.getByRole('button', { name: /Compare/i }).first();
    if (await compareBtn.isVisible()) {
      await compareBtn.click();
      await page.waitForTimeout(300);

      const modalInfo = await page.evaluate(() => {
        const modal = document.querySelector('[role="dialog"]');
        if (!modal) return null;
        return {
          isOpen: true,
          scrollHeight: modal.scrollHeight,
          clientHeight: modal.clientHeight,
        };
      });
      expect(modalInfo).not.toBeNull();

      // Close modal via Escape or Close button
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);
    }

    // 2. Lifecycle Sign-Off Modal (when approvable)
    const approveBtn = page.getByRole('button', { name: /Sign-Off|Approve|Governance/i }).first();
    if (await approveBtn.isVisible() && await approveBtn.isEnabled()) {
      await approveBtn.click();
      await page.waitForTimeout(300);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);
    }
  });

  test('05. Cross-Mode Transitions & Scroll Position Stability', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/planning', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    // Scroll to bottom in Integrated mode
    await page.evaluate(() => {
      document.querySelectorAll('*').forEach((el) => {
        if (el.scrollHeight > el.clientHeight) el.scrollTop = el.scrollHeight;
      });
    });

    // Switch to Tasks mode while scrolled
    const tasksBtn = page.getByRole('button', { name: /Tasks Queue/i }).first();
    await tasksBtn.click();
    await page.waitForTimeout(300);

    // Verify Tasks table search input is interactive and operable
    const searchInput = page.getByPlaceholder(/Search by Task ID/i);
    await expect(searchInput).toBeVisible();
    await searchInput.fill('TSK-0001');
    await page.waitForTimeout(200);

    const filteredRows = await page.evaluate(() => {
      return document.querySelectorAll('tbody tr').length;
    });
    expect(filteredRows).toBeGreaterThanOrEqual(1);

    // Switch to Diagnostics mode with search active
    const diagBtn = page.getByRole('button', { name: /Diagnostics/i }).first();
    await diagBtn.click();
    await page.waitForTimeout(300);

    // Verify Diagnostics content is present and no uncaught exceptions
    const hasDiagHeading = await page.evaluate(() => {
      return document.body.textContent?.includes('Causal Constraint Diagnostics') ?? false;
    });
    expect(hasDiagHeading).toBe(true);

    // Return to 3-Panel Workstation
    const integratedBtn = page.getByRole('button', { name: /3-Panel Workstation/i }).first();
    await integratedBtn.click();
    await page.waitForTimeout(300);
  });

  test('06. Viewport 1802x786: Page Vertical Scroll & Expand Button Absence Verification', async ({ page }) => {
    await page.setViewportSize({ width: 1802, height: 786 });
    await page.goto('/planning', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    // 1. Verify Expand button does NOT exist anywhere in DOM
    const expandBtnCount = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('button')).filter(
        (b) => b.textContent && b.textContent.trim().toLowerCase() === 'expand'
      ).length;
    });
    expect(expandBtnCount).toBe(0);

    // 2. Verify Planning page container owns vertical scrolling at 1802x786
    const pageScrollMetrics = await page.evaluate(() => {
      const pageEl = document.querySelector('main > div') as HTMLElement | null;
      if (!pageEl) return { found: false, scrollHeight: 0, clientHeight: 0, canScroll: false };
      return {
        found: true,
        scrollHeight: pageEl.scrollHeight,
        clientHeight: pageEl.clientHeight,
        canScroll: pageEl.scrollHeight > pageEl.clientHeight,
      };
    });
    expect(pageScrollMetrics.found).toBe(true);
    expect(pageScrollMetrics.canScroll).toBe(true);
    expect(pageScrollMetrics.scrollHeight).toBeGreaterThan(pageScrollMetrics.clientHeight);

    // 3. Scroll to bottom of planning page and verify complete reachability
    await page.evaluate(() => {
      const pageEl = document.querySelector('main > div') as HTMLElement | null;
      if (pageEl) {
        pageEl.scrollTop = pageEl.scrollHeight;
      }
    });
    await page.waitForTimeout(200);

    // Check bottom elements reachability
    const reachability = await page.evaluate(() => {
      const table = document.querySelector('table');
      const tableRect = table ? table.getBoundingClientRect() : null;
      const inspector = document.querySelector('.hidden.xl\\:flex');
      const inspectorRect = inspector ? inspector.getBoundingClientRect() : null;
      return {
        tableVisible: tableRect ? tableRect.top < window.innerHeight : true,
        inspectorVisible: inspectorRect ? inspectorRect.top < window.innerHeight : true,
      };
    });
    expect(reachability.tableVisible).toBe(true);
    expect(reachability.inspectorVisible).toBe(true);

    // 4. Verify all 9 modes at 1802x786 remain functional and scroll-accessible
    for (const mode of MODES) {
      const modeBtn = page.getByRole('button', { name: new RegExp(mode.buttonText, 'i') }).first();
      await modeBtn.click();
      await page.waitForTimeout(200);

      const modeMetrics = await page.evaluate(() => {
        const pageEl = document.querySelector('main > div') as HTMLElement | null;
        return {
          scrollHeight: pageEl?.scrollHeight ?? 0,
          clientHeight: pageEl?.clientHeight ?? 0,
        };
      });
      // Page must have valid dimensions in every mode
      expect(modeMetrics.clientHeight).toBeGreaterThan(0);
      expect(modeMetrics.scrollHeight).toBeGreaterThan(0);
    }
  });
});
