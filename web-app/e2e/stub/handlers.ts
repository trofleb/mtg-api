import { HttpResponse, http } from "msw";
import { ALL_SETS } from "./fixtures";
import { cardById, search } from "./search";
import { StubContractError, validated } from "./validate";

/**
 * The MSW handler set.
 *
 * One set serves both layers, so the fixtures are defined once:
 *
 *   - Integration (Vitest, node) - `setupServer(...handlers)` intercepts
 *     `lib/api.ts`'s fetch in-process.
 *   - Playwright Tier B - `server.ts` mounts the same handlers on a real
 *     port and the Next server's `API_URL` points at it. It has to be a real
 *     port: `lib/api.ts` fetches server-side, from the Next process, so
 *     nothing running inside the browser or inside the test runner can
 *     intercept it.
 *
 * Only the three endpoints `lib/api.ts` actually calls are stubbed. Anything
 * else falls through to a 404, which is the honest answer - a stub that
 * answers routes the frontend never asks for invites tests that assert
 * against the stub rather than against the app.
 */

/**
 * Match a path on any host.
 *
 * The two layers reach these handlers at different origins - Tier B over
 * HTTP at `http://127.0.0.1:8787`, the integration layer by interception,
 * where MSW resolves a bare path against the test environment's own origin.
 * A host-less pattern would silently match only one of them.
 */
const ANY_ORIGIN = (path: string): string => `*${path}`;

const asNumber = (value: string | null): number | undefined => {
  if (value === null || value === "") return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
};

/** FastAPI's own error shape, so error handling is exercised as it really is. */
const notFound = (detail: string) => HttpResponse.json({ detail }, { status: 404 });

/** A contract violation must stop the run, not quietly serve bad data. */
function guard(build: () => Response): Response {
  try {
    return build();
  } catch (error) {
    if (error instanceof StubContractError) {
      return HttpResponse.json({ detail: error.message }, { status: 500 });
    }
    return HttpResponse.json({ detail: String(error) }, { status: 400 });
  }
}

export const handlers = [
  http.get(ANY_ORIGIN("/ping"), () =>
    HttpResponse.text("pong", { headers: { "content-type": "text/plain; charset=utf-8" } })
  ),

  http.get(ANY_ORIGIN("/sets"), () =>
    guard(() => HttpResponse.json(validated("Sets", { sets: ALL_SETS })))
  ),

  http.get(ANY_ORIGIN("/cards/search/:text"), ({ request, params }) =>
    guard(() => {
      const url = new URL(request.url);
      const response = search({
        text: String(params.text),
        cursor: url.searchParams.get("cursor"),
        pageCount: asNumber(url.searchParams.get("page_count")),
        sets: url.searchParams.getAll("sets"),
        colors: url.searchParams.getAll("colors"),
        colorOperator: url.searchParams.get("color_operator"),
        cmcMin: asNumber(url.searchParams.get("cmc_min")),
        cmcMax: asNumber(url.searchParams.get("cmc_max")),
        types: url.searchParams.getAll("types"),
        rarities: url.searchParams.getAll("rarities"),
      });

      return HttpResponse.json(validated("SearchResponse", response));
    })
  ),

  http.get(ANY_ORIGIN("/cards/oracle/:oracleId/aggregated"), ({ params }) =>
    guard(() => {
      const card = cardById(String(params.oracleId));
      if (!card) return notFound(`No card found with oracle_id ${params.oracleId}`);

      return HttpResponse.json(validated("OracleCard", card));
    })
  ),
];
