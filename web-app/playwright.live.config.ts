import { defineConfig, devices } from "@playwright/test";

/**
 * Tier C - the live smoke tests.
 *
 * These need the real stack: a real API, a real Mongo, a real Meilisearch,
 * and real card data. They are for post-deploy verification, not for a pull
 * request, and they are the reason this is a separate config: Playwright's
 * `webServer` is top-level rather than per-project, so a tier that needs a
 * different server needs a different config.
 *
 * Usage:
 *
 *   BASE_URL=https://mtg.nicocasa.ch pnpm run test:e2e:live   # deployed
 *   pnpm run test:e2e:live                                    # local stack
 *
 * With BASE_URL set there is nothing to boot; without it, a local server is
 * started and expected to reach an API on its own (docker-compose up api, or
 * the VPS tunnel). Starting a local server anyway when BASE_URL points
 * elsewhere would silently serve the local build on :3000 while the
 * assertions ran against the remote host.
 */

const APP_URL = "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./e2e/live",
  timeout: 60 * 1000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [["html", { outputFolder: "playwright-report-live", open: "never" }], ["list"]],
  outputDir: "test-results-live",

  use: {
    baseURL: process.env.BASE_URL || APP_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15 * 1000,
    navigationTimeout: 45 * 1000,
  },

  projects: [{ name: "live", use: { ...devices["Desktop Chrome"] } }],

  webServer: process.env.BASE_URL
    ? undefined
    : {
        // A production build even locally: several live assertions are about
        // caching headers, which `next dev` does not emit.
        command: "pnpm run build && pnpm run start",
        url: APP_URL,
        reuseExistingServer: !process.env.CI,
        timeout: 180 * 1000,
        stdout: "pipe",
        stderr: "pipe",
      },
});
