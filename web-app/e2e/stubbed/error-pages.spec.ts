import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { ALL_CARDS, BLACK_LOTUS_ID, BOGUS_CARD_ID } from "../stub/fixtures";

/**
 * Tier B - what a visitor gets when the card id in the URL is not a card
 * (#29), and how long that answer is kept (#30).
 *
 * Both are Tier B and neither is component-testable, for reasons worth
 * restating so nobody "promotes" them down a layer later:
 *
 *   - The subject is Next's boundary resolution walking the route tree. The
 *     fix is a *file that does not exist yet*, not a change to a component,
 *     so there is no component to render in a component test.
 *   - "Without JavaScript" is a property of the transport, not of the tree.
 *     A component test cannot observe pre-hydration HTML; Browser Mode always
 *     has JS.
 *   - The ISR cache is server-side state in `.next/cache`, visible only
 *     across two requests to the same running server.
 *
 * And #30 needs a *production* build: `next dev` never populates the ISR
 * cache, so `x-nextjs-cache` is absent there and the bug is invisible. Tier B
 * boots `next build && next start` - see `playwright.config.ts`.
 */

/** The hour PR #17 bought for a card page, and the value #30 is about. */
const CARD_PAGE_MAX_AGE_SECONDS = 3600;

/**
 * The longest a "no such card" answer may be kept.
 *
 * Not a round number picked for looks: a card id that 404s today is one an
 * ingest run can make real at any moment, so the answer has to be cheap to be
 * wrong about. Five minutes is the same order as Next's own stale time.
 */
const NOT_FOUND_MAX_AGE_CEILING_SECONDS = 300;

function sMaxAge(cacheControl: string | undefined): number | null {
  const match = /s-maxage=(\d+)/.exec(cacheControl ?? "");
  return match === null ? null : Number(match[1]);
}

/**
 * An unknown id that has never been requested, so the first request below is
 * a genuinely cold miss.
 *
 * Fresh per call rather than the shared `BOGUS_CARD_ID` because the cache is
 * the thing under test: any earlier request for the same id - from another
 * spec in this file, or from a previous run against a reused server
 * (`reuseExistingServer` is on outside CI) - would warm the entry and turn
 * the first response into a HIT before the test starts.
 *
 * Well-formed on purpose, for the same reason `BOGUS_CARD_ID` is: a malformed
 * id could 404 for the wrong reason and never reach the lookup at all.
 */
function freshUnknownCardId(): string {
  const id = randomUUID();

  expect(
    ALL_CARDS.some((card) => card.id === id),
    "the probe id has to be one the stub does not know"
  ).toBe(false);

  return id;
}

test.describe("an unknown card without JavaScript (#29)", () => {
  test.use({ javaScriptEnabled: false });

  test("renders visible text rather than an empty page", async ({ page }) => {
    const response = await page.goto(`/card/${BOGUS_CARD_ID}`);

    expect(response?.status(), "an id no card has must answer 404").toBe(404);

    const visible = (await page.locator("body").innerText()).trim();

    expect(
      visible.length,
      "the 404 body is empty before hydration. With no not-found boundary in the route " +
        "tree, Next falls back to its built-in one - which the @modal parallel slot makes " +
        "a client component prop, so the server streams the page's entire visible content " +
        "inside the flight payload and paints nothing until JS runs. What actually reached " +
        `the browser here: ${JSON.stringify(visible)}`
    ).toBeGreaterThan(0);
  });

  test("offers a link back into the app", async ({ page }) => {
    await page.goto(`/card/${BOGUS_CARD_ID}`);

    // A dead end is the other half of #29: even once it hydrates, the built-in
    // fallback is a bare "404 | This page could not be found" with no links at
    // all, so the only way out is the back button - and there is none at all on
    // a shared link opened cold.
    await expect(
      page.locator('a[href="/"]'),
      "the not-found page has to offer a way back to the search"
    ).toHaveCount(1);
  });
});

test.describe("the 404 for an unknown card and the ISR cache (#30)", () => {
  test("is not replayed from the cache on the next request", async ({ request }) => {
    const path = `/card/${freshUnknownCardId()}`;

    const first = await request.get(path);
    const second = await request.get(path);

    expect(first.status(), "an id no card has must answer 404").toBe(404);
    expect(second.status(), "and must keep answering 404").toBe(404);

    expect(
      second.headers()["x-nextjs-cache"],
      "the 404 was written to the ISR cache and served back from it. " +
        `First request: x-nextjs-cache=${first.headers()["x-nextjs-cache"]}, ` +
        `cache-control=${first.headers()["cache-control"]}. The route's ` +
        "`export const revalidate = 3600` is a segment-level value, so it applies to the " +
        "not-found branch exactly as it does to a real card - and a card that gets ingested " +
        "in the next hour stays a 404 for everyone who already asked"
    ).not.toBe("HIT");
  });

  test("is not given a real card page's hour-long lifetime", async ({ request }) => {
    const response = await request.get(`/card/${freshUnknownCardId()}`);

    expect(response.status()).toBe(404);

    const cacheControl = response.headers()["cache-control"];
    const maxAge = sMaxAge(cacheControl);

    expect(
      maxAge === null || maxAge <= NOT_FOUND_MAX_AGE_CEILING_SECONDS,
      `the 404 is served with Cache-Control: ${cacheControl}. Any shared cache in front of ` +
        `the app will hold "this card does not exist" for ${maxAge}s`
    ).toBe(true);
  });

  test("a card that does exist still caches for an hour", async ({ request }) => {
    // The control, and not a formality: the fix for #30 must narrow the
    // not-found branch *only*. Lowering the segment's revalidate would pass
    // both tests above while throwing away PR #17's caching win - and would
    // silently disarm #34's spec, which reads exactly this header to decide
    // whether the server under test prerenders at all.
    const response = await request.get(`/card/${BLACK_LOTUS_ID}`);

    expect(response.status()).toBe(200);
    expect(
      sMaxAge(response.headers()["cache-control"]),
      "a real card page must keep its hour"
    ).toBe(CARD_PAGE_MAX_AGE_SECONDS);
  });
});
