import { defineConfig } from '@playwright/test';

// End-to-end tests against a RUNNING app (the built Docker image in CI): LMX_URL, default http://localhost:8000
export default defineConfig({
  testDir: 'e2e',
  timeout: 30_000,
  // tests share one server (and its data), so one at a time
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: process.env.LMX_URL ?? 'http://localhost:8000', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { browserName: 'chromium', viewport: { width: 1200, height: 800 } } },
    { name: 'phone', use: { browserName: 'chromium', viewport: { width: 390, height: 844 }, isMobile: true } }
  ]
});
