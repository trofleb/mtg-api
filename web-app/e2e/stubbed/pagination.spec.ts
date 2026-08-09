import { expect, test } from "@playwright/test";

/**
 * Tier B - paging past the first page (#21).
 *
 * The stub carries 21 filler cards plus Black Lotus, all matching the app's
 * default query, so a 20-card page always has a second page behind it and
 * the ids are the same on every run. That is what makes an overlap between
 * pages a finding rather than a coincidence: a stateless generator would
 * hand back fresh cards for page 2 and the assertion below would be
 * meaningless.
 */

type Page = import("@playwright/test").Page;

const cardIdsOn = async (page: Page): Promise<string[]> => {
  const hrefs = await page
    .locator('[data-testid="card-item"]')
    .evaluateAll((nodes) => nodes.map((node) => node.getAttribute("href") ?? ""));
  return hrefs.map((href) => href.replace("/card/", ""));
};

/**
 * Paging is a client-side navigation, so the grid is still the old one for a
 * moment after the click. Waiting on the URL rather than on the DOM keeps the
 * assertion about the cursor and not about render timing - and reading the
 * grid too early is exactly how this test first passed against a page that
 * had not changed.
 */
async function followPagingLink(page: Page, name: RegExp, expectedUrl: RegExp): Promise<void> {
  await page.getByRole("link", { name }).click();
  await page.waitForURL(expectedUrl);
}

test.describe("search pagination", () => {
  test("page two continues the first page instead of repeating it", async ({ page }) => {
    await page.goto("/");

    const firstPage = await cardIdsOn(page);
    expect(firstPage).toHaveLength(20);
    expect(new Set(firstPage).size, "page one repeats a card").toBe(firstPage.length);

    await followPagingLink(page, /load more cards/i, /cursor=/);

    const secondPage = await cardIdsOn(page);
    expect(secondPage.length).toBeGreaterThan(0);

    const overlap = secondPage.filter((id) => firstPage.includes(id));
    expect(overlap, "the cursor handed back cards already shown on page one").toEqual([]);
  });

  test("going back to the start drops the cursor", async ({ page }) => {
    await page.goto("/");
    const firstPage = await cardIdsOn(page);

    await followPagingLink(page, /load more cards/i, /cursor=/);
    await followPagingLink(page, /back to start/i, /^[^?]*\/(\?(?!.*cursor=).*)?$/);

    expect(await cardIdsOn(page)).toEqual(firstPage);
  });
});
