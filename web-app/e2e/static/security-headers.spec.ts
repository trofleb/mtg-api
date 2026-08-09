import { expect, test } from "@playwright/test";

/**
 * Tier A (static) - issue #31, no security headers.
 *
 * These assertions run against /robots.txt rather than /, deliberately.
 * `app/page.tsx` calls `searchCards` unconditionally, so / cannot render
 * without an API and Tier A has none. `headers()` in next.config.ts matches
 * by `source` pattern, not by whether a React tree rendered, so a static
 * route proves exactly the same thing with no data behind it.
 *
 * Not covered here, and not coverable at any layer: HSTS only does its job
 * on the *first* plaintext request of a session, before any document exists
 * to run a test inside. Asserting the header is emitted is all a test can do.
 */
test.describe("security headers", () => {
  test("are present on a route that needs no API", async ({ request }) => {
    const response = await request.get("/robots.txt");
    expect(response.status()).toBe(200);

    const headers = response.headers();

    expect(headers["strict-transport-security"]).toMatch(/max-age=\d+/);
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["permissions-policy"]).toBeTruthy();
  });

  test("do not advertise the framework", async ({ request }) => {
    const response = await request.get("/robots.txt");
    expect(response.headers()["x-powered-by"]).toBeUndefined();
  });

  test("include a content security policy", async ({ request }) => {
    const response = await request.get("/robots.txt");
    const csp = response.headers()["content-security-policy"];

    expect(csp).toBeTruthy();
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
    // Card art is served straight from Scryfall's CDN (next.config.ts sets
    // `unoptimized`), so the CDN host has to be allowed explicitly or every
    // card image is blocked.
    expect(csp).toContain("cards.scryfall.io");
  });
});

/**
 * The CSP has to be proven non-breaking, not just present - a policy that
 * blocks the app's own inline styles or the RSC bootstrap is worse than none.
 *
 * Next's built-in 404 page is the one HTML document Tier A can render: it
 * still goes through the root layout, so it carries next/font's injected
 * <style>, the framework chunks and the `self.__next_f.push` inline RSC
 * payload - i.e. every part of the page the policy could plausibly break.
 */
test("the CSP does not block the app's own inline styles or scripts", async ({ page }) => {
  const violations: string[] = [];
  await page.addInitScript(() => {
    document.addEventListener("securitypolicyviolation", (event) => {
      const record = window as unknown as { __cspViolations?: string[] };
      record.__cspViolations ??= [];
      record.__cspViolations.push(`${event.violatedDirective} blocked ${event.blockedURI}`);
    });
  });
  page.on("console", (message) => {
    if (message.type() === "error" && /content security policy/i.test(message.text())) {
      violations.push(message.text());
    }
  });

  const response = await page.goto("/this-route-does-not-exist");
  expect(response?.status()).toBe(404);
  expect(response?.headers()["content-security-policy"]).toBeTruthy();

  await expect(page.locator("body")).not.toBeEmpty();

  const reported = await page.evaluate(
    () => (window as unknown as { __cspViolations?: string[] }).__cspViolations ?? []
  );
  expect([...violations, ...reported]).toEqual([]);
});
