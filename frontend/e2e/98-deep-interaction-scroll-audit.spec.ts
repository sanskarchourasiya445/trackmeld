import { test, expect } from '@playwright/test';

test.describe('Deep Interaction, Modal, Drawer & Usability Audit', () => {
  test('01. Text selection usability across all pages', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });

    const routes = ['/overview', '/planning', '/work-orders', '/network', '/governance', '/audit', '/copilot'];
    const selectionResults: Record<string, boolean> = {};

    for (const r of routes) {
      await page.goto(r, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(400);

      // Check if body or root container has user-select: none
      const isSelectNone = await page.evaluate(() => {
        const rootDiv = document.querySelector('main > div') || document.querySelector('main');
        if (!rootDiv) return false;
        const style = window.getComputedStyle(rootDiv);
        return style.userSelect === 'none';
      });

      selectionResults[r] = isSelectNone;
      console.log(`[SELECTION AUDIT] Route ${r}: userSelect === 'none' -> ${isSelectNone}`);
    }

    // Report selection results
    console.log('[SELECTION SUMMARY]', JSON.stringify(selectionResults, null, 2));
  });

  test('02. Network subtabs table scroll and sticky headers', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/network?subtab=STATIONS', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    const stationTableInfo = await page.evaluate(() => {
      const table = document.querySelector('table');
      if (!table) return null;
      const thead = table.querySelector('thead');
      const theadStyle = thead ? window.getComputedStyle(thead) : null;
      const scrollParent = table.closest('.overflow-y-auto') || table.parentElement;
      return {
        tableRows: table.querySelectorAll('tbody tr').length,
        theadPosition: theadStyle?.position,
        scrollParentClass: scrollParent?.className,
        scrollParentScrollHeight: scrollParent?.scrollHeight,
        scrollParentClientHeight: scrollParent?.clientHeight,
      };
    });

    console.log('[NETWORK STATIONS AUDIT]', JSON.stringify(stationTableInfo, null, 2));
    expect(stationTableInfo?.tableRows).toBeGreaterThan(0);
  });

  test('03. Work Orders table and mobile cards', async ({ page }) => {
    // Desktop check
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/work-orders', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    const desktopInfo = await page.evaluate(() => {
      const table = document.querySelector('table');
      const tableRows = table ? table.querySelectorAll('tbody tr').length : 0;
      const scrollContainer = table?.closest('.overflow-auto');
      return {
        tableRows,
        hasScrollContainer: !!scrollContainer,
        scrollHeight: scrollContainer?.scrollHeight,
        clientHeight: scrollContainer?.clientHeight,
        isScrollable: scrollContainer ? scrollContainer.scrollHeight > scrollContainer.clientHeight : false,
      };
    });
    console.log('[WORK ORDERS DESKTOP]', JSON.stringify(desktopInfo, null, 2));

    // Mobile check (390px)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/work-orders', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    const mobileInfo = await page.evaluate(() => {
      const table = document.querySelector('table');
      const isTableHidden = table ? window.getComputedStyle(table.closest('div')!).display === 'none' : true;
      const cards = document.querySelectorAll('.md\\:hidden > div[role="button"]');
      const scrollParent = document.querySelector('main > div');
      return {
        isTableHidden,
        cardsCount: cards.length,
        scrollParentHeight: scrollParent?.clientHeight,
        scrollParentScrollHeight: scrollParent?.scrollHeight,
        isScrollable: scrollParent ? scrollParent.scrollHeight > scrollParent.clientHeight : false,
      };
    });
    console.log('[WORK ORDERS MOBILE]', JSON.stringify(mobileInfo, null, 2));
  });

  test('04. Entity Inspector and Drawer Usability', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    // Click Inspector button in Planning Top Bar
    const inspectorBtn = page.getByRole('button', { name: 'Inspector', exact: true });
    if (await inspectorBtn.isVisible()) {
      await inspectorBtn.click();
      await page.waitForTimeout(300);

      const inspectorInfo = await page.evaluate(() => {
        const inspectorEl = document.querySelector('[role="complementary"]') || document.querySelector('.w-\\[360px\\], .w-\\[400px\\]');
        if (!inspectorEl) return null;
        const style = window.getComputedStyle(inspectorEl);
        return {
          visible: style.display !== 'none',
          userSelect: style.userSelect,
          className: inspectorEl.className,
          scrollHeight: inspectorEl.scrollHeight,
          clientHeight: inspectorEl.clientHeight,
        };
      });
      console.log('[INSPECTOR AUDIT]', JSON.stringify(inspectorInfo, null, 2));
    }
  });

  test('05. Modal Scrollability (Plan Approval Modal)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/governance', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    // If approval button is enabled or we inspect modal component
    const approveBtn = page.getByRole('button', { name: /Review & Approve Plan/i });
    if (await approveBtn.isVisible() && await approveBtn.isEnabled()) {
      await approveBtn.click();
      await page.waitForTimeout(400);

      const modalInfo = await page.evaluate(() => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return null;
        const bodyEl = dialog.querySelector('.overflow-y-auto') || dialog;
        return {
          dialogWidth: dialog.clientWidth,
          dialogHeight: dialog.clientHeight,
          bodyScrollHeight: bodyEl.scrollHeight,
          bodyClientHeight: bodyEl.clientHeight,
          isBodyScrollable: bodyEl.scrollHeight > bodyEl.clientHeight,
        };
      });
      console.log('[APPROVAL MODAL AUDIT]', JSON.stringify(modalInfo, null, 2));
    }
  });
});
