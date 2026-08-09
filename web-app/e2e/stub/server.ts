import { createMiddleware } from "@mswjs/http-middleware";
import express, { type NextFunction, type Request, type Response } from "express";
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

/**
 * Reproduce the ASGI server's percent-decoding of the path *before* routing.
 *
 * `lib/api.ts` builds `/cards/search/${encodeURIComponent(text)}`, so a card
 * name containing `//` arrives as `%2F%2F`. Uvicorn decodes that into real
 * separators before FastAPI matches, at which point the `{text}` segment
 * (`[^/]+`) no longer matches and the request dies - issue #26.
 *
 * Express and MSW would both happily match the escaped form, so without this
 * the stub would answer 200 where the real API cannot, and #26 would be
 * invisible to every test that runs against the stub. A stub that is more
 * forgiving than the thing it stands in for is a false green generator.
 *
 * Delete this once #26 moves the search text into a query parameter - and
 * only then.
 */
function decodePathSeparators(req: Request, _res: Response, next: NextFunction): void {
  if (/%2f/i.test(req.url)) {
    req.url = req.url.replace(/%2f/gi, "/");
  }
  next();
}

const app = express();
app.use(decodePathSeparators);
app.use(createMiddleware(...handlers));

app.listen(PORT, () => {
  console.log(`[stub] API stub listening on http://localhost:${PORT}`);
});
