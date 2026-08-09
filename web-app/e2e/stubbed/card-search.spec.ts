import { expect, test } from "@playwright/test";

/**
 * Tier B - the search journey against the MSW stub.
 *
 * This file used to assert against whatever production happened to return:
 * it searched "Lightning Bolt", "Dragon" and "Planeswalker" and waited for
 * "results found". That is untestable in CI and unfalsifiable anywhere -
 * a green run proved the data was there, not that the app worked.
 *
 * Every query below is answered by `e2e/stub/fixtures.ts`, so the counts are
 * fixed and an empty grid is a real failure. The vocabulary comes from the
 * fixtures: "Black Lotus" (22 matches, the app's default query), "Replica"
 * (21), "Propaganda" (the reversible card), "Delver" (the double-faced one).
 */

const SEARCH_INPUT = "Search for cards by name, text, or ability...";

test.describe("MTG Card Search", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display the page title and description", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Magic the Gathering Card Search" })
    ).toBeVisible();
    await expect(page.getByText("Card info comes from the")).toBeVisible();
    await expect(page.getByRole("link", { name: "Scryfall API" })).toHaveAttribute(
      "href",
      "https://scryfall.com/docs/api"
    );
  });

  test("should have search input with default value", async ({ page }) => {
    const searchInput = page.getByPlaceholder(SEARCH_INPUT);
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toHaveValue("Black Lotus");
  });

  test("should perform basic card search", async ({ page }) => {
    const searchInput = page.getByPlaceholder(SEARCH_INPUT);

    await searchInput.clear();
    await searchInput.fill("Propaganda");
    await page
      .getByRole("button", { name: /search/i })
      .first()
      .click();

    await expect(page.getByText(/results found/i)).toBeVisible();
    await expect(page.locator('[data-testid="card-item"]')).toHaveCount(1);
    await expect(page.getByText("Propaganda // Propaganda")).toBeVisible();
  });

  test("should search on Enter key press", async ({ page }) => {
    const searchInput = page.getByPlaceholder(SEARCH_INPUT);

    await searchInput.clear();
    await searchInput.fill("Delver");
    await searchInput.press("Enter");

    await expect(page.locator('[data-testid="card-item"]')).toHaveCount(1);
  });

  test("should say so when nothing matches", async ({ page }) => {
    const searchInput = page.getByPlaceholder(SEARCH_INPUT);

    await searchInput.clear();
    await searchInput.fill("NoSuchCardExistsAnywhere");
    await searchInput.press("Enter");

    await expect(page.getByText("No cards found.")).toBeVisible();
  });

  test("should toggle filters panel", async ({ page }) => {
    // exact: true, or this also matches "Apply Filters" once the panel is
    // open and the click fails on a strict-mode violation.
    const filtersButton = page.getByRole("button", { name: "Filters", exact: true });

    await expect(page.getByText("Card Types")).not.toBeVisible();

    await filtersButton.click();
    await expect(page.getByText("Card Types")).toBeVisible();

    await filtersButton.click();
    await expect(page.getByText("Card Types")).not.toBeVisible();
  });

  test("should filter by card type", async ({ page }) => {
    const searchInput = page.getByPlaceholder(SEARCH_INPUT);

    await searchInput.clear();
    await searchInput.fill("Replica");
    await page.getByRole("button", { name: "Filters", exact: true }).click();
    await page.getByRole("button", { name: "Creature", exact: true }).click();
    await page.getByRole("button", { name: /apply filters/i }).click();

    // Half the fixture fillers are creatures; the filter has to actually cut
    // the result set, not just leave the URL looking different.
    const tiles = page.locator('[data-testid="card-item"]');
    await expect(tiles).toHaveCount(10);
    await expect(page).toHaveURL(/types=Creature/);
  });

  test("should filter by color", async ({ page }) => {
    const searchInput = page.getByPlaceholder(SEARCH_INPUT);

    await searchInput.clear();
    await searchInput.fill("Replica");
    await page.getByRole("button", { name: "Filters", exact: true }).click();
    await page.getByRole("button", { name: /🔴 R/i }).click();
    await page.getByRole("button", { name: /apply filters/i }).click();

    await expect(page.locator('[data-testid="card-item"]')).toHaveCount(2);
  });

  test("should filter by rarity", async ({ page }) => {
    const searchInput = page.getByPlaceholder(SEARCH_INPUT);

    await searchInput.clear();
    await searchInput.fill("Replica");
    await page.getByRole("button", { name: "Filters", exact: true }).click();
    await page.getByRole("button", { name: "mythic", exact: true }).click();
    await page.getByRole("button", { name: /apply filters/i }).click();

    await expect(page.locator('[data-testid="card-item"]')).toHaveCount(5);
  });

  test("should disable search button when input is empty", async ({ page }) => {
    const searchInput = page.getByPlaceholder(SEARCH_INPUT);
    const searchButton = page.getByRole("button", { name: /search/i }).first();

    await searchInput.clear();
    await expect(searchButton).toBeDisabled();

    await searchInput.fill("Test");
    await expect(searchButton).toBeEnabled();
  });

  test("should open the card modal when clicking a card", async ({ page }) => {
    const searchInput = page.getByPlaceholder(SEARCH_INPUT);

    await searchInput.clear();
    await searchInput.fill("Delver");
    await searchInput.press("Enter");

    await page.locator('[data-testid="card-item"]').first().click();

    // #34: this is the intercepting route resolving. It 404s if the route is
    // prerendered, and the dialog never appears.
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page).toHaveURL(/\/card\//);
  });
});
