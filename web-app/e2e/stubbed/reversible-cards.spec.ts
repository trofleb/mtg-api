import { expect, test } from "@playwright/test";
import { REVERSIBLE_CARD_IDS, REVERSIBLE_SEARCH_TEXT } from "../stub/fixtures";

/**
 * Tier B - reversible cards reach the browser as two linkable tiles (#22).
 *
 * The fixtures behind this come from
 * `e2e/stub/data/reversible-cards.json`, the same file
 * `tests/fixtures/reversible_cards.py` loads - including the query below.
 * pytest asserts the grouping at the aggregation layer; this asserts what
 * the user ends up clicking. Neither suite can drift from the other's idea
 * of what a reversible card is, because there is only one copy of it.
 *
 * Scryfall omits the top-level `oracle_id` on a `reversible_card` and puts
 * one on each face instead, so the group key has to come from a face. When it
 * did not, both cards landed in one null-keyed bucket that sorted first and
 * the first tile of every affected search was a dead link.
 */

test("both reversible cards are returned, with their own ids", async ({ page }) => {
  await page.goto(`/?q=${encodeURIComponent(REVERSIBLE_SEARCH_TEXT)}`);

  const tiles = page.locator('[data-testid="card-item"]');
  await expect(tiles).toHaveCount(2);

  const hrefs = await tiles.evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute("href") ?? "")
  );

  // Compare ids, not whole hrefs: tiles append the originating search (#39), so
  // the href is now `/card/<id>?q=...`. The id is what #22 is about.
  const ids = hrefs.map((href) => href.replace("/card/", "").split("?")[0]);
  expect(ids.sort()).toEqual([...REVERSIBLE_CARD_IDS].sort());
});

test("a reversible card's own page resolves", async ({ page }) => {
  const response = await page.goto(`/card/${REVERSIBLE_CARD_IDS[0]}`);

  // The id the grid links to has to be one the card endpoint answers to.
  // Fixing the grouping key alone produced an id that then 404'd, because
  // the aggregated lookup matched the top-level oracle_id only.
  expect(response?.status()).toBe(200);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Propaganda");
});
