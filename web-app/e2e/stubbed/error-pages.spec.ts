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
 *   - The subject is Next's boundary resolution walking the route tree, not a
 *     component. Rendering `app/not-found.tsx` directly - which
 *     `test/route-boundaries.test.tsx` does - says nothing about whether the
 *     router ever reaches it, which is the whole question.
 *   - "Without JavaScript" is a property of the transport, not of the tree.
 *     A component test cannot observe pre-hydration HTML; Browser Mode always
 *     has JS. This is what caught the fact that a boundary file does not fix
 *     the no-JS case at all - see the last group in this file.
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

test.describe("an unknown card (#29)", () => {
  test("renders the app's own not-found page, with a way out", async ({ page }) => {
    const response = await page.goto(`/card/${BOGUS_CARD_ID}`);

    expect(response?.status(), "an id no card has must answer 404").toBe(404);

    // The half of #29 that a boundary file does fix. Next's built-in fallback
    // is a bare "404 | This page could not be found" with no links in it at
    // all, so a visitor who followed a stale shared link had nothing to click.
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(
      page.locator('a[href="/"]'),
      "the not-found page has to offer a way back to the search"
    ).toHaveCount(1);
  });
});

test.describe("a URL that matches no route, without JavaScript (#29)", () => {
  test.use({ javaScriptEnabled: false });

  test("renders visible text rather than an empty page", async ({ page }) => {
    // An unmatched URL is served from the prerendered /_not-found route, which
    // is an ordinary successful render - so app/not-found.tsx reaches the HTML
    // here, and this is the case where the boundary file fixes the no-JS
    // experience outright. Contrast the test below.
    const response = await page.goto("/no-such-page-at-all");

    expect(response?.status()).toBe(404);

    const visible = (await page.locator("body").innerText()).trim();

    expect(
      visible.length,
      `nothing was painted before hydration: ${JSON.stringify(visible)}`
    ).toBeGreaterThan(0);
    await expect(page.locator('a[href="/"]')).toHaveCount(1);
  });
});

/**
 * The half of #29 that adding a boundary file does NOT fix.
 *
 * Held red on purpose, in the same way #36 is: the assertion is the behaviour
 * we want, `test.fail()` records that Next does not currently provide it, and
 * the run goes red the day it starts passing - which is the signal to delete
 * this wrapper.
 *
 * The plan attributed the blank page to the `@modal` parallel slot making
 * Next's built-in fallback resolve client-side. That is not the cause, and it
 * was worth finding out, because it means the plan's fix could not have worked:
 *
 *   - with `app/@modal/` moved out of the route tree entirely, `/card/<bogus>`
 *     still served `<html id="__next_error__">` with an empty body;
 *   - a three-line probe page whose whole body is `notFound()`, with no data,
 *     no `revalidate` and no `generateStaticParams`, did the same;
 *   - so did a probe page that simply threw, which is `error.tsx`'s case.
 *
 * The cause is in `next/dist/server/app-render/app-render.js`: `notFound()`
 * propagates out of the HTML render, and the catch block answers with
 * `getErrorRSCPayload`, whose seed data is a hardcoded empty
 * `<html id="__next_error__">`. The real boundary tree only ever reaches the
 * browser inlined in the flight payload, so it cannot paint until React runs.
 * `createNotFoundLoaderTree`, the function that would render a not-found tree
 * server-side, is called on exactly one path in that file: server actions.
 *
 * Next 16, re-checked on 16.3.3. Nothing in `app/` can change it - the levers
 * are all inside the framework's error path. `experimental.globalNotFound` is
 * the one avenue not tried here; reading the code it does not touch this path,
 * and it is an experimental flag, so it was not worth spending the app's
 * stability on.
 */
test.describe("an unknown card without JavaScript (#29, unfixed)", () => {
  test.use({ javaScriptEnabled: false });

  test.fail(
    true,
    "Next 16.3.3 serves notFound() as an empty __next_error__ document; the 404 UI is " +
      "client-rendered from the flight payload"
  );

  test("renders visible text rather than an empty page", async ({ page }) => {
    const response = await page.goto(`/card/${BOGUS_CARD_ID}`);

    expect(response?.status(), "an id no card has must answer 404").toBe(404);

    const visible = (await page.locator("body").innerText()).trim();

    expect(
      visible.length,
      `nothing was painted before hydration: ${JSON.stringify(visible)}`
    ).toBeGreaterThan(0);
  });
});

/**
 * The assertion below is about the *lifetime* of the cached 404, not about
 * whether it is cached at all - and that is a correction to this plan, made
 * after measuring rather than by preference.
 *
 * The intended assertion was "two requests, x-nextjs-cache MISS then HIT",
 * i.e. an unknown card must not be replayed from the cache at all. Not
 * reachable: `generateStaticParams` on this route puts on-demand renders in
 * *prerender* mode, and the one API that would opt a render out of the cache
 * - `connection()` - is a dynamic API, which prerender mode answers with a
 * hard `DYNAMIC_SERVER_USAGE` 500. Attested: with `connection()` in the
 * not-found branch, every unknown id returned HTTP 500 instead of 404.
 *
 * So a cache HIT is not the defect and never could have been. The defect is
 * the *hour*: the 404 inheriting the lifetime of a real card page. That is
 * both what the issue describes and what the plan's own Fix section asks for
 * ("give the not-found branch its own short revalidate"), so the assertion
 * moved onto it. It still fails on the unfixed code, with the same two
 * requests - see the second test in this group, whose red was
 * `Cache-Control: s-maxage=3600 [...] will hold "this card does not exist"
 * for 3600s`.
 */
test.describe("the 404 for an unknown card and the ISR cache (#30)", () => {
  test("is not replayed from an hour-old cache entry", async ({ request }) => {
    const path = `/card/${freshUnknownCardId()}`;

    const first = await request.get(path);
    const second = await request.get(path);

    expect(first.status(), "an id no card has must answer 404").toBe(404);
    expect(second.status(), "and must keep answering 404").toBe(404);

    const maxAge = sMaxAge(second.headers()["cache-control"]);

    expect(
      maxAge !== null && maxAge <= NOT_FOUND_MAX_AGE_CEILING_SECONDS,
      "the second request was answered from the ISR cache with a real card page's " +
        `lifetime. x-nextjs-cache: ${first.headers()["x-nextjs-cache"]} then ` +
        `${second.headers()["x-nextjs-cache"]}; cache-control: ` +
        `${second.headers()["cache-control"]}. The route's ` +
        "`export const revalidate = 3600` is a segment-level value, so it applied to the " +
        "not-found branch exactly as it did to a real card - and a card ingested a minute " +
        "later stayed missing for the rest of the hour, for everyone who asked"
    ).toBe(true);
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
