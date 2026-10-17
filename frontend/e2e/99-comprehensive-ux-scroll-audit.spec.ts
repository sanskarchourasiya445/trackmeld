import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const ARTIFACTS_DIR = 'C:/Users/DELL/.gemini/antigravity/brain/2b364e02-5a9f-4058-bb03-42f611a2ff0b/audit-baseline';

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

const ROUTES = [
  { name: 'landing', path: '/' },
  { name: 'overview', path: '/overview' },
  { name: 'planning', path: '/planning' },
  { name: 'work-orders', path: '/work-orders' },
  { name: 'network', path: '/network' },
  { name: 'governance', path: '/governance' },
  { name: 'audit', path: '/audit' },
  { name: 'copilot', path: '/copilot' },
];

test.describe('Phase 1 & 2: Comprehensive UX & Scroll Architecture Audit', () => {
  test.beforeAll(() => {
    if (!fs.existsSync(ARTIFACTS_DIR)) {
      fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
    }
  });

  for (const route of ROUTES) {
    test(`Audit ${route.name} route layout, scroll, and console errors across viewports`, async ({ page }) => {
      test.setTimeout(120000);
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      for (const vp of VIEWPORTS) {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.goto(route.path, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(500); // Allow MapLibre or initial renders to settle

        // 1. Evaluate scroll container metrics
        const metrics = await page.evaluate(() => {
          const docEl = document.documentElement;
          const body = document.body;
          const hasWindowScroll = docEl.scrollHeight > docEl.clientHeight;
          const hasBodyScroll = body.scrollHeight > body.clientHeight;
          const hasDocHorizontalOverflow = docEl.scrollWidth > window.innerWidth;
          
          // Find all scrollable containers
          const scrollables: Array<{ tag: string; id: string; className: string; scrollHeight: number; clientHeight: number; overflowY: string }> = [];
          const allEls = document.querySelectorAll('*');
          allEls.forEach((el) => {
            const style = window.getComputedStyle(el);
            if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
              scrollables.push({
                tag: el.tagName.toLowerCase(),
                id: el.id,
                className: el.className ? String(el.className).substring(0, 50) : '',
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight,
                overflowY: style.overflowY,
              });
            }
          });

          return {
            windowInnerWidth: window.innerWidth,
            windowInnerHeight: window.innerHeight,
            docScrollWidth: docEl.scrollWidth,
            docScrollHeight: docEl.scrollHeight,
            docClientHeight: docEl.clientHeight,
            hasWindowScroll,
            hasBodyScroll,
            hasDocHorizontalOverflow,
            scrollableCount: scrollables.length,
            scrollables: scrollables.slice(0, 5),
          };
        });

        // Save a screenshot for record
        const screenshotPath = path.join(ARTIFACTS_DIR, `${route.name}-${vp.name}.png`);
        await page.screenshot({ path: screenshotPath });

        console.log(`[AUDIT] ${route.name} @ ${vp.name}: DocHOverflow=${metrics.hasDocHorizontalOverflow}, Scrollables=${metrics.scrollableCount}`);
        
        // Assert no unexpected document-level horizontal overflow
        expect(metrics.hasDocHorizontalOverflow, `Route ${route.name} has document horizontal overflow at ${vp.width}px`).toBe(false);
      }

      // Check for serious console errors
      const criticalErrors = consoleErrors.filter(
        (e) => !e.includes('favicon') && !e.includes('MapLibre') && !e.includes('WebGL')
      );
      if (criticalErrors.length > 0) {
        console.warn(`[AUDIT WARNING] ${route.name} had console errors:`, criticalErrors);
      }
    });
  }
});
