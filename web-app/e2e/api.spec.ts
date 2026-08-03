import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.API_URL || "http://localhost:8000";

test.describe("MTG API Endpoints", () => {
  // These talk to the API directly, which only works where the API is
  // reachable: a local stack, or a VPS tunnel that publishes it on
  // localhost. Production deliberately does not expose it - the browser can
  // only ever reach the Next.js server - so against a remote BASE_URL these
  // would fail for the very reason the deployment is considered correct.
  // Skip rather than fail, and say so, so a red run always means a real bug.
  test.skip(
    () => Boolean(process.env.BASE_URL) && !process.env.API_URL,
    "API is not exposed publicly; set API_URL (e.g. via the VPS tunnel) to run these"
  );

  test("should respond to ping endpoint", async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/ping`);

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const text = await response.text();
    expect(text).toBe("pong");
  });

  test("should search for cards by name", async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/cards/search/lightning bolt`);

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty("cards");
    expect(Array.isArray(data.cards)).toBeTruthy();

    if (data.cards.length > 0) {
      const card = data.cards[0];
      expect(card).toHaveProperty("id");
      expect(card).toHaveProperty("name");
    }
  });

  test("should get a specific card by name", async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/cards/Black Lotus`);

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty("id");
    expect(data).toHaveProperty("name");
    expect(data.name).toContain("Black Lotus");
  });

  test("should handle card not found", async ({ request }) => {
    const response = await request.get(
      `${API_BASE_URL}/cards/ThisCardDefinitelyDoesNotExistInMTG123456`
    );

    expect(response.status()).toBe(404);
  });

  test("should search with filters", async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/cards/search/dragon`, {
      params: {
        colors: "R",
        types: "Creature",
      },
    });

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty("cards");
    expect(Array.isArray(data.cards)).toBeTruthy();
  });

  test("should support pagination with cursor", async ({ request }) => {
    // First request to get initial results
    const firstResponse = await request.get(`${API_BASE_URL}/cards/search/dragon`);

    expect(firstResponse.ok()).toBeTruthy();
    const firstData = await firstResponse.json();

    expect(firstData).toHaveProperty("cards");
    expect(firstData).toHaveProperty("cursor");
    expect(firstData).toHaveProperty("has_more");

    // If there are more results, test pagination
    if (firstData.has_more && firstData.cursor) {
      const secondResponse = await request.get(`${API_BASE_URL}/cards/search/dragon`, {
        params: {
          cursor: firstData.cursor,
        },
      });

      expect(secondResponse.ok()).toBeTruthy();
      const secondData = await secondResponse.json();

      expect(secondData).toHaveProperty("cards");
      expect(Array.isArray(secondData.cards)).toBeTruthy();
    }
  });

  test("should get card by scryfall ID", async ({ request }) => {
    // Search groups printings by oracle_id, so a result's own "id" is an
    // oracle id. /cards/id/ addresses a single printing by scryfall id, so
    // take one from the nested printings instead.
    //
    // Asserted unconditionally: the previous version wrapped this in an
    // `if (cards[0].id)` that was never true, so the test passed without
    // exercising anything.
    const searchResponse = await request.get(`${API_BASE_URL}/cards/search/lightning bolt`);
    expect(searchResponse.ok()).toBeTruthy();

    const searchData = await searchResponse.json();
    expect(searchData.cards.length).toBeGreaterThan(0);

    const printings = searchData.cards[0].cards;
    expect(printings.length).toBeGreaterThan(0);

    const scryfallId = printings[0].id;
    const response = await request.get(`${API_BASE_URL}/cards/id/${scryfallId}`);

    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.id).toBe(scryfallId);
  });

  test("should handle API errors gracefully", async ({ request }) => {
    // Test with invalid endpoint
    const response = await request.get(`${API_BASE_URL}/invalid-endpoint-12345`);

    expect(response.status()).toBe(404);
  });

  test("should return JSON content type for card endpoints", async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/cards/search/test`);

    const contentType = response.headers()["content-type"];
    expect(contentType).toContain("application/json");
  });

  test("should handle empty search gracefully", async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/cards/search/ `);

    // Should either return 200 with empty results or 422 for validation error
    expect([200, 422, 404]).toContain(response.status());
  });
});
