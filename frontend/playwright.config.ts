import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Configuration for TrackMeld Phase 15E.
 * Deterministic browser execution against Next.js frontend and FastAPI backend.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: false,
  workers: 1, // Deterministic serial execution for state-dependent governance tests
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
  webServer: [
    {
      command: 'python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000',
      cwd: '..',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true,
      timeout: 30000,
      env: {
        DATABASE_URL: 'postgresql+asyncpg://postgres@localhost:5433/trackmeld',
        AUTH_PLANNER_TOKEN: process.env.TEST_PLANNER_TOKEN || 'e2e-planner-token-2026',
        AUTH_APPROVER_TOKEN: process.env.TEST_APPROVER_TOKEN || 'e2e-approver-token-2026',
        AUTH_VIEWER_TOKEN: process.env.TEST_VIEWER_TOKEN || 'e2e-viewer-token-2026',
      },
    },
    {
      command: 'npm run start',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: true,
      timeout: 45000,
      env: {
        PORT: '3000',
        NEXT_PUBLIC_API_URL: 'http://127.0.0.1:8000/api/v1',
        BACKEND_URL: 'http://127.0.0.1:8000',
      },
    },
  ],
});
