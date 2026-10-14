import { test, expect } from '@playwright/test';

test.describe('Official Canonical 3D Digital Twin Homepage & Governance Suite', () => {
  test('01. / renders headline, HUD telemetry, and 3D canvas container', async ({ page }) => {
    await page.goto('/');

    // Verify main editorial headline
    await expect(page.locator('h1')).toContainText('SMARTER');
    await expect(page.locator('h1')).toContainText('RAILWAY');
    await expect(page.locator('h1')).toContainText('PLANNING.');

    // Verify technical pill
    await expect(page.getByText('DIGITAL TWIN & POSSESSION OPTIMIZATION')).toBeVisible();

    // Verify HUD dock elements
    await expect(page.getByText('DIGITAL TWIN HUD')).toBeVisible();
    await expect(page.getByText('Camera View')).toBeVisible();
    await expect(page.getByText('Atmosphere')).toBeVisible();

    // Verify KPI ticker
    await expect(page.getByText('440 km')).toBeVisible();
    await expect(page.getByText('132 Tracks', { exact: true })).toBeVisible();
    await expect(page.getByText('13 Categories', { exact: true })).toBeVisible();
    await expect(page.getByText('Four-Eyes', { exact: true })).toBeVisible();
  });

  test('02. /landing-3d redirects cleanly to canonical root /', async ({ page }) => {
    await page.goto('/landing-3d');
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator('h1')).toContainText('SMARTER');
  });

  test('03. Interactive sections render without errors on canonical homepage', async ({ page }) => {
    await page.goto('/');

    // Section 2: Digital Twin
    const secTwin = page.locator('#digital-twin');
    await expect(secTwin).toBeVisible();
    await expect(secTwin).toContainText('THE RAILWAY');
    await expect(secTwin).toContainText('DIGITIZED.');

    // Section 3: Constraints
    const secConstraints = page.locator('#constraints');
    await expect(secConstraints).toBeVisible();
    await expect(secConstraints).toContainText('PLAN AROUND');
    await expect(secConstraints).toContainText('REAL CONSTRAINTS.');

    // Section 4: Optimization
    const secOpt = page.locator('#optimization');
    await expect(secOpt).toBeVisible();
    await expect(secOpt).toContainText('OPTIMIZE');
    await expect(secOpt).toContainText("DON'T GUESS.");

    // Section 5: Validation Firewall
    const secVal = page.locator('#validation');
    await expect(secVal).toBeVisible();
    await expect(secVal).toContainText('VALIDATE');
    await expect(secVal).toContainText('INDEPENDENTLY.');
    await expect(secVal).toContainText('13-CATEGORY SAFETY FIREWALL MATRIX');

    // Section 6: AI Copilot
    const secCopilot = page.locator('#copilot');
    await expect(secCopilot).toBeVisible();
    await expect(secCopilot).toContainText('EXPLAINS THE PLAN.');
    await expect(secCopilot).toContainText('AI does not control the schedule.');

    // Section 7: Plan Comparison
    const secComp = page.locator('#comparison');
    await expect(secComp).toBeVisible();
    await expect(secComp).toContainText('PRECISION');
    await expect(secComp).toContainText('PLAN COMPARISON.');

    // Section 8: Architecture
    const secArch = page.locator('#architecture');
    await expect(secArch).toBeVisible();
    await expect(secArch).toContainText('INVIOLABLE');
    await expect(secArch).toContainText('PIPELINE ARCHITECTURE.');
  });

  test('04. Enterprise Briefing Modal opens, validates, and simulates dossier generation on root /', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Click Request Demo in navbar (using toPass to guarantee React client hydration has attached onClick)
    const requestDemoBtn = page.getByRole('button', { name: /REQUEST DEMO/i });
    const modalHeading = page.getByRole('heading', { name: 'Schedule Architecture Briefing' });
    await expect(async () => {
      if (!(await modalHeading.isVisible())) {
        await requestDemoBtn.click({ force: true });
      }
      await expect(modalHeading).toBeVisible({ timeout: 3000 });
    }).toPass({ timeout: 20000 });

    // Fill form
    await page.fill('input[placeholder="e.g. Dr. Elena Vance"]', 'Director Jane Doe');
    await page.fill('input[placeholder="name@railway.gov / .com"]', 'jane.doe@nationalrail.gov');
    await page.fill('input[placeholder="e.g. Central Corridor Rail"]', 'National Rail Authority');

    // Submit form
    await page.click('button:has-text("Transmit Architecture Request")');

    // Verify confirmation and reference token
    await expect(page.getByText('Architecture Dossier Scheduled')).toBeVisible({ timeout: 12000 });
    await expect(page.getByText(/REFERENCE TOKEN: TM-REQ-\d+-VERIFIED/)).toBeVisible();

    // Close modal
    await page.click('button:has-text("Return to Digital Twin")');
    await expect(page.getByText('Architecture Dossier Scheduled')).not.toBeVisible();
  });
});
