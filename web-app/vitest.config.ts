import react from "@vitejs/plugin-react";
import { playwright } from "@vitest/browser-playwright";
import tsconfigPaths from "vite-tsconfig-paths";
import { defineConfig } from "vitest/config";

// Two Vitest projects, split by what the test needs from the environment.
//
//   unit    - jsdom, milliseconds, no browser download. Everything that
//             asserts values or DOM shape lives here.
//   browser - a real Chromium via Playwright. jsdom has no layout engine
//             (getBoundingClientRect always returns zeros), so anything that
//             asserts a *size*, a real drag, or real focus behaviour has to
//             run here. Matched on `*.browser.test.tsx`.
//
// Plugins are not inherited from the root config by projects, so each project
// gets its own set.
const projectPlugins = () => [
  tsconfigPaths(), // Resolves path aliases from tsconfig.json
  react(), // Enables React support
];

const sharedExclude = [
  "**/node_modules/**",
  "**/dist/**",
  "**/e2e/**", // Exclude Playwright e2e tests
  "**/.next/**",
];

export default defineConfig({
  test: {
    projects: [
      {
        plugins: projectPlugins(),
        test: {
          name: "unit",
          environment: "jsdom", // Use jsdom for DOM testing
          globals: true,
          setupFiles: ["./vitest.setup.ts"],
          css: true,
          // Browser-mode specs need real layout; they run in "browser" below.
          exclude: [...sharedExclude, "**/*.browser.test.tsx"],
        },
      },
      {
        plugins: projectPlugins(),
        // Pre-bundled up front: otherwise Vite discovers them mid-run and
        // reloads the page, which Vitest reports as possibly-flaky.
        optimizeDeps: {
          include: [
            "react",
            "react-dom/client",
            "react/jsx-dev-runtime",
            "next/image",
            "next/link",
          ],
        },
        test: {
          name: "browser",
          globals: true,
          include: ["**/*.browser.test.tsx"],
          exclude: sharedExclude,
          // Imports app/globals.css, so measurements are taken against real
          // Tailwind output rather than unstyled defaults.
          setupFiles: ["./vitest.setup.browser.ts"],
          browser: {
            enabled: true,
            headless: true,
            provider: playwright(),
            instances: [{ browser: "chromium" }],
          },
        },
      },
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: [
        "node_modules/**",
        "**/*.config.{ts,js}",
        "**/*.d.ts",
        "**/types/**",
        "**/__tests__/**",
        "**/test/**",
        "**/e2e/**",
      ],
    },
  },
});
