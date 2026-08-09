import { expect, test } from "@playwright/test";

test.describe("Homepage", () => {
  test("should load and display the main page elements", async ({ page }) => {
    await page.goto("/");

    // Verify page title
    await expect(page).toHaveTitle(/MTG Card Search/i);

    // Verify main heading
    await expect(
      page.getByRole("heading", { name: "Magic the Gathering Card Search" })
    ).toBeVisible();

    // Verify Scryfall attribution link
    const scryfallLink = page.getByRole("link", { name: "Scryfall API" });
    await expect(scryfallLink).toBeVisible();
    await expect(scryfallLink).toHaveAttribute("href", "https://scryfall.com/docs/api");
    await expect(scryfallLink).toHaveAttribute("target", "_blank");

    // Verify search input is present
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    await expect(searchInput).toBeVisible();

    // Verify search button is present
    const searchButton = page.getByRole("button", { name: /search/i }).first();
    await expect(searchButton).toBeVisible();

    // Verify filters button is present
    const filtersButton = page.getByRole("button", { name: "Filters" });
    await expect(filtersButton).toBeVisible();
  });

  test("should have accessible form controls", async ({ page }) => {
    await page.goto("/");

    // Check that search input has proper attributes
    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    await expect(searchInput).toHaveAttribute("type", "text");

    // Verify buttons are keyboard accessible
    const searchButton = page.getByRole("button", { name: /search/i }).first();
    await searchButton.focus();
    await expect(searchButton).toBeFocused();
  });

  test("should toggle filters panel visibility", async ({ page }) => {
    await page.goto("/");

    // Use first() to get the "Filters" toggle button (not "Apply Filters")
    const filtersButton = page.getByRole("button", { name: "Filters", exact: true });

    // Initially filters should be hidden
    await expect(page.getByText("Card Types")).not.toBeVisible();

    // Click to show filters
    await filtersButton.click();

    // Wait for animation to complete
    await page.waitForTimeout(300);

    // Now filters should be visible
    await expect(page.getByText("Card Types")).toBeVisible();
    await expect(page.getByText("Colors")).toBeVisible();
    await expect(page.getByText("Rarity")).toBeVisible();

    // Click again to hide
    await filtersButton.click();
    await page.waitForTimeout(300);

    // Filters should be hidden again
    await expect(page.getByText("Card Types")).not.toBeVisible();
  });

  test("should display all filter options when filters are expanded", async ({ page }) => {
    await page.goto("/");

    // Open filters
    await page.getByRole("button", { name: "Filters", exact: true }).click();
    await page.waitForTimeout(300);

    // Verify card type filters
    const cardTypes = [
      "Creature",
      "Instant",
      "Sorcery",
      "Enchantment",
      "Artifact",
      "Planeswalker",
      "Land",
      "Battle",
    ];
    for (const type of cardTypes) {
      await expect(page.getByRole("button", { name: type, exact: true })).toBeVisible();
    }

    // Verify color filters (emoji + letter)
    await expect(page.getByRole("button", { name: /⚪ W/i })).toBeVisible(); // White
    await expect(page.getByRole("button", { name: /🔵 U/i })).toBeVisible(); // Blue
    await expect(page.getByRole("button", { name: /⚫ B/i })).toBeVisible(); // Black
    await expect(page.getByRole("button", { name: /🔴 R/i })).toBeVisible(); // Red
    await expect(page.getByRole("button", { name: /🟢 G/i })).toBeVisible(); // Green

    // Verify rarity filters using exact match to avoid confusion
    await expect(page.getByRole("button", { name: "common", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "uncommon", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "rare", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "mythic", exact: true })).toBeVisible();

    // Verify CMC slider
    await expect(page.getByText(/Mana Cost \(CMC\):/i)).toBeVisible();

    // Verify action buttons
    await expect(page.getByRole("button", { name: "Apply Filters" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Clear All" })).toBeVisible();
  });

  test("should update search input value", async ({ page }) => {
    await page.goto("/");

    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");

    // Default value should be "Black Lotus"
    await expect(searchInput).toHaveValue("Black Lotus");

    // Clear and type new value
    await searchInput.clear();
    await searchInput.fill("Lightning Bolt");

    // Verify new value
    await expect(searchInput).toHaveValue("Lightning Bolt");
  });

  test("should disable search button when input is empty", async ({ page }) => {
    await page.goto("/");

    const searchInput = page.getByPlaceholder("Search for cards by name, text, or ability...");
    const searchButton = page.getByRole("button", { name: /search/i }).first();

    // Initially should be enabled (has default value)
    await expect(searchButton).toBeEnabled();

    // Clear input
    await searchInput.clear();

    // Button should be disabled
    await expect(searchButton).toBeDisabled();

    // Type something
    await searchInput.fill("Test");

    // Button should be enabled again
    await expect(searchButton).toBeEnabled();
  });
});
