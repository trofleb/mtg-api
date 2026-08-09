import { expect, test } from "@playwright/test";

/**
 * Tier A (static) - issue #32, favicon.ico / robots.txt / sitemap.xml 404.
 *
 * None of these needs the API, a database or a stub: they are produced by the
 * Next server itself from `app/robots.ts`, `app/sitemap.ts` and the
 * `app/favicon.ico` metadata file convention.
 *
 * `public/` holds only favicon.png and app/layout.tsx declares
 * `icon: "/favicon.png"`, so the app's *own* reference already resolves. What
 * 404s is the conventional /favicon.ico that browser chrome requests
 * unprompted and no application code ever asks for - which is why nothing in
 * the app surfaced it.
 */
test.describe("well-known static routes", () => {
  test("/robots.txt is served and points at the sitemap", async ({ request }) => {
    const response = await request.get("/robots.txt");

    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toContain("text/plain");

    const body = await response.text();
    expect(body).toContain("User-Agent: *");
    expect(body).toContain("Sitemap:");
  });

  test("/favicon.ico is served", async ({ request }) => {
    const response = await request.get("/favicon.ico");

    expect(response.status()).toBe(200);
    expect((await response.body()).byteLength).toBeGreaterThan(0);
  });

  test("/sitemap.xml is served as XML and lists the home page", async ({ request }) => {
    const response = await request.get("/sitemap.xml");

    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toContain("xml");

    const body = await response.text();
    expect(body).toContain("<urlset");
    expect(body).toMatch(/<loc>https?:\/\/[^<]+<\/loc>/);
  });
});
