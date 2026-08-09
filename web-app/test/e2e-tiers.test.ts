import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * The tier split is a property of *test discovery*, so it is asserted by
 * asking Playwright what it discovers rather than by reading the configs.
 *
 * Why this test exists: `playwright.config.ts` used to declare
 * `testDir: "./e2e"`, which swept `e2e/live/` - specs that need a real API,
 * a real database and production data - into the run that is supposed to
 * need none of those. A tier that quietly contains a Tier C spec cannot be
 * put in CI, which is the structural reason Playwright had never run there.
 *
 * It also fails if a spec lands in a directory no config covers, which is
 * the silent-orphan failure mode the split would otherwise introduce.
 */

const WEB_APP_ROOT = path.resolve(__dirname, "..");
const PLAYWRIGHT_CLI = path.join(WEB_APP_ROOT, "node_modules/@playwright/test/cli.js");

const E2E_ROOT = path.join(WEB_APP_ROOT, "e2e");

/**
 * Spec files a given Playwright config would run, relative to `e2e/`.
 *
 * Reported paths are relative to each config's own rootDir, which differs
 * between the two, so they are re-anchored on `e2e/` before comparison.
 */
function discoveredSpecs(config: string): string[] {
  const stdout = execFileSync(
    process.execPath,
    [PLAYWRIGHT_CLI, "test", "--list", "--reporter=json", "--config", config],
    { cwd: WEB_APP_ROOT, encoding: "utf8", maxBuffer: 32 * 1024 * 1024 }
  );

  const report = JSON.parse(stdout) as { config: { rootDir: string }; suites: { file: string }[] };

  return report.suites
    .map((suite) => path.relative(E2E_ROOT, path.resolve(report.config.rootDir, suite.file)))
    .map((file) => file.split(path.sep).join("/"))
    .sort();
}

/** Every `*.spec.ts` under `e2e/`, relative to `e2e/`, so none can be orphaned. */
function allSpecFiles(): string[] {
  const root = path.join(WEB_APP_ROOT, "e2e");
  return readdirSync(root, { recursive: true, encoding: "utf8" })
    .filter((entry) => entry.endsWith(".spec.ts"))
    .map((entry) => entry.split(path.sep).join("/"))
    .sort();
}

describe("Playwright tiers", () => {
  it("keeps Tier C out of the default run", () => {
    const specs = discoveredSpecs("playwright.config.ts");

    expect(specs.length).toBeGreaterThan(0);
    for (const spec of specs) {
      expect(spec, `${spec} is not in a tier the default config should run`).toMatch(
        /^(static|stubbed)\//
      );
    }
  });

  it("runs only Tier C from the live config", () => {
    const specs = discoveredSpecs("playwright.live.config.ts");

    expect(specs.length).toBeGreaterThan(0);
    for (const spec of specs) {
      expect(spec, `${spec} is not a live spec`).toMatch(/^live\//);
    }
  });

  it("leaves no spec behind that neither config runs", () => {
    const covered = new Set([
      ...discoveredSpecs("playwright.config.ts"),
      ...discoveredSpecs("playwright.live.config.ts"),
    ]);

    expect([...covered].sort()).toEqual(allSpecFiles());
  });
});
