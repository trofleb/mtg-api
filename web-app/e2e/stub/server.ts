import { createMiddleware } from "@mswjs/http-middleware";
import express from "express";
import { handlers } from "./handlers";

/**
 * The stub as a standalone HTTP server - Playwright Tier B's whole point.
 *
 * `lib/api.ts` fetches server-side, from inside the Next process
 * (`API_BASE_URL = process.env.API_URL`), so the browser never talks to the
 * API. MSW-in-browser and `page.route()` therefore cannot see the app's data
 * fetching at all. What *can*: run the handlers in a node process that
 * listens on a port and point `API_URL` at it. The Next server then runs
 * identically - real routing, real RSC resolution, real ISR, real headers -
 * with no Mongo, no Meilisearch and fully deterministic data.
 *
 * Started by `playwright.config.ts`'s `webServer` and by `pnpm run stub`.
 */

const PORT = Number(process.env.STUB_PORT ?? 8787);

// The decodePathSeparators middleware that used to sit here reproduced the ASGI
// server's percent-decoding of the path before routing, so that #26 stayed
// visible through the stub instead of being papered over. #26 is fixed - the
// search text is a `?q=` parameter now, never a path segment - so there is no
// path left to decode, and its own comment said to delete it at exactly this
// point. The principle it stood for still holds: a stub more forgiving than the
// thing it stands in for is a false-green generator.

const app = express();
app.use(createMiddleware(...handlers));

app.listen(PORT, () => {
  console.log(`[stub] API stub listening on http://localhost:${PORT}`);
});
