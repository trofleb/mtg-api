// @vitest-environment node
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import {
  BOGUS_CARD_ID,
  DOUBLE_FACED_CARD_ID,
  REVERSIBLE_CARD_IDS,
  REVERSIBLE_SEARCH_TEXT,
} from "../e2e/stub/fixtures";
import { handlers } from "../e2e/stub/handlers";

/**
 * The Integration layer: `lib/api.ts` against the MSW stub, in node.
 *
 * Same handlers Playwright Tier B mounts on a port - here they intercept
 * `fetch` in-process instead, so the fixtures are defined once and the two
 * layers cannot disagree. What this catches that Tier B cannot is cheap and
 * specific: normalisation, error branches, and the exact shape handed back to
 * a server component.
 *
 * What it does *not* catch, so nobody mistakes a green run for more than it
 * is: the `next: { revalidate, tags }` options on those fetches are an
 * ignored extra property here. Caching is Tier B and Tier C only.
 */

const server = setupServer(...handlers);
const API_URL = "http://api.test";

beforeAll(() => {
  process.env.API_URL = API_URL;
  server.listen({ onUnhandledRequest: "error" });
});
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

/** Imported lazily: lib/api.ts reads API_URL at module scope. */
async function api() {
  return await import("./api");
}

describe("searchCards against the stub", () => {
  it("returns a full page and a cursor that continues it", async () => {
    const { searchCards } = await api();

    const first = await searchCards("Black Lotus");
    expect(first.cards).toHaveLength(20);
    expect(first.has_more).toBe(true);
    expect(first.cursor).toBeTruthy();

    const second = await searchCards("Black Lotus", first.cursor);
    expect(second.cards.length).toBeGreaterThan(0);

    const firstIds = first.cards.map((card) => card.id);
    const secondIds = second.cards.map((card) => card.id);
    expect(secondIds.filter((id) => firstIds.includes(id))).toEqual([]);
  });

  it("gives every card a usable id, reversible ones included", async () => {
    const { searchCards } = await api();

    const results = await searchCards(REVERSIBLE_SEARCH_TEXT);

    expect(results.cards.map((card) => card.id).sort()).toEqual([...REVERSIBLE_CARD_IDS].sort());
    for (const card of results.cards) {
      expect(card.id).not.toBe("");
    }
  });

  it("returns nothing rather than throwing when a query matches no card", async () => {
    const { searchCards } = await api();

    const results = await searchCards("NoSuchCardExistsAnywhere");
    expect(results.cards).toEqual([]);
    expect(results.has_more).toBe(false);
  });
});

describe("getCardByOracleId against the stub", () => {
  it("returns null for an id the API does not know", async () => {
    const { getCardByOracleId } = await api();

    // #29/#30 both start here: the page can only render a not-found state if
    // the client turns a 404 into null instead of throwing.
    expect(await getCardByOracleId(BOGUS_CARD_ID)).toBeNull();
  });

  it("keeps both faces of a double-faced card", async () => {
    const { getCardByOracleId } = await api();

    const card = await getCardByOracleId(DOUBLE_FACED_CARD_ID);
    expect(card?.faces_thumbnails).toHaveLength(2);
  });
});
