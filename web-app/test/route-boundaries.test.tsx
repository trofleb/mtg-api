import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ErrorBoundary from "@/app/error";
import NotFound from "@/app/not-found";

/**
 * The route tree has to *have* boundaries before anything can be said about
 * what they render.
 *
 * Next resolves `notFound()` and a thrown render error by walking up from the
 * segment looking for `not-found.tsx` / `error.tsx`. With none anywhere in
 * `app/`, it falls back to its own built-in pages - and because of the
 * `@modal` parallel slot those resolve client-side only, so the server sends
 * a body with no visible text at all. Tier B
 * (`e2e/stubbed/error-pages.spec.ts`) asserts that consequence over HTTP with
 * JavaScript disabled, which is the only place it is observable.
 *
 * What this file adds is the part Tier B cannot reach: that the boundaries
 * are at the *root*, so they cover every segment rather than just the one
 * that happened to be tested, and that what they render is worth showing. An
 * error boundary in particular is hard to trigger over HTTP on purpose - the
 * stub has no way to make a card page throw - so it is rendered directly.
 */

const APP_DIR = path.resolve(__dirname, "..", "app");

describe("route boundaries exist at the app root", () => {
  it.each([
    ["not-found.tsx", "notFound() from any segment"],
    ["error.tsx", "an uncaught render error in any segment"],
  ])("app/%s catches %s", (file) => {
    expect(
      existsSync(path.join(APP_DIR, file)),
      `app/${file} is missing, so Next falls back to its built-in page`
    ).toBe(true);
  });

  it("declares error.tsx as a client component", () => {
    // Not style: an error boundary is a React error boundary, which only
    // exists on the client. Without the directive Next fails the build, and
    // the file would be a boundary in name only.
    const source = readFileSync(path.join(APP_DIR, "error.tsx"), "utf8");

    expect(source.trimStart().startsWith('"use client"')).toBe(true);
  });
});

describe("not-found boundary", () => {
  it("says what happened", () => {
    render(<NotFound />);

    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("offers a way back to the search", () => {
    render(<NotFound />);

    expect(screen.getByRole("link", { name: /search/i })).toHaveAttribute("href", "/");
  });
});

describe("error boundary", () => {
  const boom = Object.assign(new Error("upstream exploded"), { digest: "abc123" });

  it("says what happened without leaking the message", () => {
    render(<ErrorBoundary error={boom} reset={() => {}} />);

    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    // The message can carry an API hostname or a stack fragment. The digest
    // is the supported way to correlate with the server log.
    expect(screen.queryByText(/upstream exploded/)).not.toBeInTheDocument();
    expect(screen.getByText(/abc123/)).toBeInTheDocument();
  });

  it("lets the user retry without a full reload", () => {
    let resets = 0;
    const reset = () => {
      resets += 1;
    };
    render(<ErrorBoundary error={boom} reset={reset} />);

    screen.getByRole("button", { name: /try again/i }).click();

    expect(resets).toBe(1);
  });

  it("offers a way back to the search", () => {
    render(<ErrorBoundary error={boom} reset={() => {}} />);

    expect(screen.getByRole("link", { name: /search/i })).toHaveAttribute("href", "/");
  });
});
