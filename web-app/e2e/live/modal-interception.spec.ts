import { type APIRequestContext, expect, test } from "@playwright/test";

/**
 * #34 - clicking a card tile 404s instead of opening the modal.
 *
 * Request-level on purpose. The behaviour only exists in RSC routing: the bug
 * is in the module-level exports the Next server reads to decide whether to
 * prerender the intercepting route, not in anything React runs. Import
 * CardModal and render it and it passes, as it always did. Only an HTTP
 * request carrying the router's own headers can see it.
 *
 * Tier C (live) for now: it needs a card id the API actually knows about, and
 * the regression is live in production while the stub does not exist yet.
 * Promote this spec to Tier B (e2e/stubbed/) once branch 0d lands - the
 * assertions are unchanged, only API_URL moves. Do not skip the promotion:
 * against Tier C this test depends on production data.
 */

// What the App Router sends when it navigates to /card/<id> from within the
// app. RSC asks for the flight payload; Next-Url names the route the
// navigation started from, and that is what selects the intercepting route.
// The two requests below differ by nothing else.
const RSC_ONLY = { RSC: "1" };
const RSC_FROM_HOME = { RSC: "1", "Next-Url": "/" };

/** A card id the running API actually knows about, read off the results grid. */
async function firstCardId(request: APIRequestContext): Promise<string> {
  const response = await request.get("/");
  expect(response.status(), "the results grid has to render to supply a card id").toBe(200);

  // Tiles link to /card/<id>. [^"/]+ also skips the id-less link #22 produces,
  // which renders as href="/card" with no id segment at all.
  const match = /href="\/card\/([^"/]+)"/.exec(await response.text());
  expect(match, "no card link on the homepage - is the API returning results?").not.toBeNull();

  return (match as RegExpExecArray)[1];
}

/**
 * Refuse to report a pass unless the server under test actually prerenders.
 *
 * This is not defensive padding - it was measured. `next dev` never prerenders,
 * so the unfixed code answers the request below with 200 there and the
 * assertion passes with the bug fully present. Since `just test-e2e` and
 * `just test-e2e-vps` both boot `pnpm run dev`, that is the default local run.
 *
 * The hour-long s-maxage on the standalone card page is the signal: it comes
 * from `export const revalidate = 3600` in app/card/[id], which only takes
 * effect in a production build.
 */
async function isPrerenderingBuild(request: APIRequestContext, cardId: string): Promise<boolean> {
  const response = await request.get(`/card/${cardId}`);
  expect(response.status(), "the standalone card page must serve a real card").toBe(200);

  return (response.headers()["cache-control"] ?? "").includes("s-maxage=3600");
}

const NOT_PRERENDERING =
  "skipped, not passed: this server does not prerender, and #34 is invisible without " +
  "prerendering. Either (a) it is a `next dev` server - rerun against a deployed " +
  "BASE_URL (`just test-e2e-prod`) or a local `next build && next start`; or (b) it is a " +
  "production build and app/card/[id] has lost `export const revalidate = 3600`, which " +
  "is PR #17's caching win and a defect in its own right. Both need looking at.";

test.describe("intercepted card modal (#34)", () => {
  test("serves the modal payload for an in-app navigation", async ({ request }) => {
    const cardId = await firstCardId(request);
    test.skip(!(await isPrerenderingBuild(request, cardId)), NOT_PRERENDERING);

    const response = await request.get(`/card/${cardId}`, { headers: RSC_FROM_HOME });

    expect(
      response.status(),
      "this is the exact request the router issues when a tile is clicked, so a 404 here " +
        "is the modal failing to open. Prerendering an intercepting route makes the " +
        "response independent of the client's router state tree, so `children` collapses " +
        "to __DEFAULT__ and 404s"
    ).toBe(200);
  });

  test("serves the flight payload for a direct request", async ({ request }) => {
    const cardId = await firstCardId(request);

    // Control: identical to the test above minus Next-Url, and already passing
    // before the fix. A failure here means the card id is bad or the route is
    // broken outright - not that the interception regressed. Deliberately not
    // gated on prerendering, since it is meaningful in every mode.
    const response = await request.get(`/card/${cardId}`, { headers: RSC_ONLY });

    expect(response.status()).toBe(200);
  });
});
