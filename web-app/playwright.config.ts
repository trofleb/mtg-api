import { defineConfig, devices } from "@playwright/test";

/**
 * Tiers A and B - the run that goes in CI.
 *
 *   A (`e2e/static/`)  - `next start`, no data. Headers, robots, favicon,
 *                        sitemap. Everything that is true of the server
 *                        regardless of what the API says.
 *   B (`e2e/stubbed/`) - `next start` with `API_URL` pointed at the node
 *                        stub in `e2e/stub/`. Real routing, real RSC
 *                        resolution, real ISR, real headers, deterministic
 *                        data, no Mongo and no Meilisearch.
 *
 * Tier C lives in `playwright.live.config.ts` and is deliberately NOT
 * discovered here. It used to be: `testDir: "./e2e"` with no project filter
 * swept `e2e/live/` into this run, which is why a suite that needs a
 * database and production data kept ending up in the "needs neither" tier.
 * `test/e2e-tiers.test.ts` fails if that regresses.
 *
 * Two configs rather than two projects because `webServer` is top-level in
 * Playwright, not per-project, and the two tiers need different servers.
 */

const STUB_PORT = Number(process.env.STUB_PORT ?? 8787);
const APP_PORT = Number(process.env.APP_PORT ?? 3000);
const STUB_URL = `http://127.0.0.1:${STUB_PORT}`;
const APP_URL = `http://127.0.0.1:${APP_PORT}`;

/**
 * A production build, not `next dev`.
 *
 * Measured, not assumed: `next dev` never prerenders, so #34's regression
 * answers 200 there and the spec passes with the bug fully present. Anything
 * about caching, ISR or prerendering is simply invisible against a dev
 * server. `E2E_DEV_SERVER=1` swaps back for fast local iteration, at the cost
 * of the specs that need a real build skipping themselves - which they say
 * out loud rather than reporting a pass.
 */
const APP_COMMAND = process.env.E2E_DEV_SERVER
  ? "pnpm run dev"
  : "pnpm run build && pnpm run start";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30 * 1000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ["html", { outputFolder: "playwright-report", open: "never" }],
    ["json", { outputFile: "playwright-report/test-results.json" }],
    ["list"],
  ],
  outputDir: "test-results",

  use: {
    // Fixed to the local server on purpose. BASE_URL belongs to Tier C: a
    // stubbed spec pointed at a deployed host would assert fixture data
    // against production and fail for a reason that is not a bug.
    baseURL: APP_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10 * 1000,
    navigationTimeout: 30 * 1000,
  },

  projects: [
    {
      name: "static",
      testDir: "./e2e/static",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "stubbed",
      testDir: "./e2e/stubbed",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Order matters: the stub has to answer before `next build` runs, because
  // the build resolves whatever the route tree asks for at build time.
  webServer: [
    {
      command: "pnpm run stub",
      url: `${STUB_URL}/ping`,
      reuseExistingServer: !process.env.CI,
      timeout: 30 * 1000,
      stdout: "pipe",
      stderr: "pipe",
      env: { STUB_PORT: String(STUB_PORT) },
    },
    {
      command: APP_COMMAND,
      url: APP_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 180 * 1000,
      stdout: "pipe",
      stderr: "pipe",
      // The single-variable process boundary the whole tier rests on:
      // lib/api.ts reads API_URL and nothing else decides where data comes
      // from. Point it here and the Next server is otherwise untouched.
      env: { API_URL: STUB_URL, PORT: String(APP_PORT) },
    },
  ],
});
