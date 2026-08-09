import { expect, test } from "@playwright/test";

/**
 * Tier C - post-deploy smoke against the real stack.
 *
 * Deliberately short. Everything that can be pinned with fixtures belongs in
 * Tier B, where it runs on every pull request; what is left here is only what
 * needs a real API, a real database and real card data. Add a journey to this
 * file only when you can say which of those three it needs.
 *
 *   BASE_URL=https://mtg.nicocasa.ch pnpm run test:e2e:live
 *
 * Run against mtg.nicocasa.ch while this branch was written, the second test
 * below fails: the first tile still links to "/card" with no id, because the
 * #22 fix is merged but not yet deployed. That is the file doing its job -
 * Tier C is the only layer that can tell you what is actually live. It is not
 * in the pull-request pipeline for exactly that reason.
 */

test.describe("live smoke", () => {
  test("the home page renders real results", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBe(200);

    await expect(
      page.getByRole("heading", { name: "Magic the Gathering Card Search" })
    ).toBeVisible();
    await expect(page.locator('[data-testid="card-item"]').first()).toBeVisible();
  });

  test("a card from the grid has a page of its own", async ({ page }) => {
    await page.goto("/");

    const href = await page.locator('[data-testid="card-item"]').first().getAttribute("href");
    expect(href, "the first tile has no link - see #22").toMatch(/^\/card\/.+/);

    const response = await page.goto(href as string);
    expect(response?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).not.toBeEmpty();
  });

  test("card art actually loads through the image optimizer", async ({ page, request }) => {
    // Tier C only, and the one thing no cheaper layer can see: jsdom and
    // Browser Mode both mock next/image away, and neither harness runs a Next
    // server, so /_next/image simply 404s there. That blind spot is how a
    // Scryfall 400 reached production once already.
    await page.goto("/");

    const src = await page.locator('[data-testid="card-item"] img').first().getAttribute("src");
    test.skip(!src, "no card image on the grid to check");

    const response = await request.get(src as string);
    expect(response.status(), `image optimizer rejected ${src}`).toBe(200);
    expect(response.headers()["content-type"]).toContain("image/");
  });
});
