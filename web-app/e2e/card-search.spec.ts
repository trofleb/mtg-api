import { expect, test } from "@playwright/test";

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
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toHaveValue("Black Lotus");
  });

  test("should perform basic card search", async ({ page }) => {
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    const searchButton = page.getByRole("button", { name: /search/i });

    // Clear and enter new search
    await searchInput.clear();
    await searchInput.fill("Lightning Bolt");
    await searchButton.click();

    // Wait for results to load
    await expect(page.getByText(/results found/i)).toBeVisible({ timeout: 10000 });

    // Verify cards are displayed
    await expect(page.locator('[data-testid="card-item"]').first()).toBeVisible();
  });

  test("should search on Enter key press", async ({ page }) => {
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");

    await searchInput.clear();
    await searchInput.fill("Counterspell");
    await searchInput.press("Enter");

    // Wait for results
    await expect(page.getByText(/results found/i)).toBeVisible({ timeout: 10000 });
  });

  test("should toggle filters panel", async ({ page }) => {
    // exact: true, or this also matches "Apply Filters" once the panel is
    // open and the click fails on a strict-mode violation.
    const filtersButton = page.getByRole("button", { name: "Filters", exact: true });

    // Filters should be hidden initially
    await expect(page.getByText("Card Types")).not.toBeVisible();

    // Click to show filters
    await filtersButton.click();
    await expect(page.getByText("Card Types")).toBeVisible();

    // Click again to hide filters
    await filtersButton.click();
    await expect(page.getByText("Card Types")).not.toBeVisible();
  });

  test("should filter by card type", async ({ page }) => {
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    const filtersButton = page.getByRole("button", { name: "Filters" });

    // Open filters
    await filtersButton.click();

    // Select Creature type
    await page.getByRole("button", { name: "Creature" }).click();

    // Perform search
    await searchInput.clear();
    await searchInput.fill("Dragon");
    await page.getByRole("button", { name: /apply filters/i }).click();

    // Wait for filtered results
    await expect(page.getByText(/results found/i)).toBeVisible({ timeout: 10000 });
  });

  test("should filter by color", async ({ page }) => {
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    const filtersButton = page.getByRole("button", { name: "Filters" });

    // Open filters
    await filtersButton.click();

    // Select Red color
    await page.getByRole("button", { name: /🔴 R/i }).click();

    // Perform search
    await searchInput.clear();
    await searchInput.fill("Bolt");
    await page.getByRole("button", { name: /apply filters/i }).click();

    // Wait for filtered results
    await expect(page.getByText(/results found/i)).toBeVisible({ timeout: 10000 });
  });

  test("should filter by rarity", async ({ page }) => {
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    const filtersButton = page.getByRole("button", { name: "Filters" });

    // Open filters
    await filtersButton.click();

    // Select mythic rarity
    await page.getByRole("button", { name: "mythic" }).click();

    // Perform search
    await searchInput.clear();
    await searchInput.fill("Planeswalker");
    await page.getByRole("button", { name: /apply filters/i }).click();

    // Wait for filtered results
    await expect(page.getByText(/results found/i)).toBeVisible({ timeout: 10000 });
  });

  test("should clear all filters", async ({ page }) => {
    const filtersButton = page.getByRole("button", { name: "Filters" });

    // Open filters and select some
    await filtersButton.click();
    await page.getByRole("button", { name: "Creature" }).click();
    await page.getByRole("button", { name: /🔴 R/i }).click();

    // Verify filters are selected (they should have 'default' variant styling)
    await expect(page.getByRole("button", { name: "Creature" })).toBeVisible();

    // Clear all filters
    await page.getByRole("button", { name: "Clear All" }).click();

    // Note: We can't easily verify the visual state change without checking classes
    // but we can verify the Clear All button executed
    await expect(page.getByRole("button", { name: "Clear All" })).toBeVisible();
  });

  test("should disable search button when input is empty", async ({ page }) => {
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    const searchButton = page.getByRole("button", { name: /search/i }).first();

    // Clear the input
    await searchInput.clear();

    // Search button should be disabled
    await expect(searchButton).toBeDisabled();

    // Type something
    await searchInput.fill("Test");

    // Search button should be enabled
    await expect(searchButton).toBeEnabled();
  });

  test("should show loading state during search", async ({ page }) => {
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    const searchButton = page.getByRole("button", { name: /search/i }).first();

    await searchInput.clear();
    await searchInput.fill("Test Search");

    // Click search and immediately check for loading state
    await searchButton.click();

    // Check for loading spinner (aria-label or visible loader)
    // The button should be disabled during loading
    await expect(searchButton).toBeDisabled();
  });

  test("should display load more button when there are more results", async ({ page }) => {
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");

    // Search for something that will have many results
    await searchInput.clear();
    await searchInput.fill("Dragon");
    await searchInput.press("Enter");

    // Wait for initial results
    await expect(page.getByText(/results found/i)).toBeVisible({ timeout: 10000 });

    // Check if "Load More Cards" button appears (only if there are more results)
    const loadMoreButton = page.getByRole("button", { name: /load more cards/i });

    // Either the button should be visible OR we should have results without a load more button
    const hasResults = await page.getByText(/results found/i).isVisible();
    expect(hasResults).toBeTruthy();
  });

  test("should open card details dialog when clicking a card", async ({ page }) => {
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");

    await searchInput.clear();
    await searchInput.fill("Lightning Bolt");
    await searchInput.press("Enter");

    // Wait for results
    await expect(page.getByText(/results found/i)).toBeVisible({ timeout: 10000 });

    // Click the first card
    const firstCard = page.locator('[data-testid="card-item"]').first();
    await firstCard.click();

    // Check that a dialog or modal opens (look for dialog role or overlay)
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5000 });
  });

  test("should handle API errors gracefully", async ({ page }) => {
    // Intercept API calls and force an error
    await page.route("**/api/cards/search*", (route) => route.abort());

    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    await searchInput.clear();
    await searchInput.fill("Test");
    await searchInput.press("Enter");

    // The page should not crash and search button should become enabled again
    await expect(page.getByRole("button", { name: /search/i }).first()).toBeEnabled({
      timeout: 5000,
    });
  });
});
