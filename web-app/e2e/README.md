# End-to-End Tests

Playwright tests for the MTG Card Search web app, in three tiers.

```
e2e/
  static/    Tier A - next start, no data at all
  stubbed/   Tier B - next start + the node API stub, API_URL pointed at it
  live/      Tier C - the real stack, or a deployed BASE_URL
  stub/      the MSW server and its fixtures - not tests
```

| Tier | Boots | Needs a database | Runs |
|------|-------|------------------|------|
| A `static` | `next start` | no | every PR, seconds |
| B `stubbed` | `next start` + node stub | no | every PR |
| C `live` | real API + Mongo + Meili, or a deployed URL | yes | post-deploy smoke |

## Running them

```bash
just test-e2e            # tiers A and B - boots everything itself
just test-e2e-static     # tier A only
just test-e2e-stubbed    # tier B only
just test-e2e-live       # tier C against a local stack
BASE_URL=https://mtg.nicocasa.ch just test-e2e-live   # tier C, deployed
```

Nothing in tiers A or B needs Docker, a database or the VPS tunnel. They are
what CI runs.

## Why the stub exists, and why it is a separate process

`lib/api.ts` fetches **server-side only**:

```ts
const API_BASE_URL = process.env.API_URL ?? "http://api:8000";
```

Every call is made from a server component, inside the Next.js process. The
browser never talks to the API, so **MSW-in-browser and `page.route()` cannot
intercept the app's data fetching** - there is nothing to intercept on the
client. What works instead is to run the handlers in a node process that
listens on a port and point `API_URL` at it. That single variable is the whole
process boundary: aim it at the stub and the Next server runs identically -
real routing, real RSC resolution, real ISR, real headers - with deterministic
data and no Mongo, no Meilisearch and no API container.

`e2e/stub/server.ts` is that process. `playwright.config.ts` starts it as the
first of two `webServer` entries.

## The stub: generated contract, hand-written fixtures

| Part | Source | Guarantee |
|------|--------|-----------|
| Response types | generated from `openapi.json` into `lib/api-types.ts` | cannot drift - CI regenerates and fails on a diff |
| Fixture documents | hand-written, typed against those types | deterministic; `tsc` fails if the schema moves under them |
| Every response | re-checked at runtime against `openapi.json` (`stub/validate.ts`) | a stub that drifts stops the run instead of serving fiction |

Fully generated response data cannot work here, whatever the tooling:

- #29/#30 need a **404 for a specific id**. Prism steers status with a
  `Prefer: code=404` request header, and the client is the Next server, which
  cannot be made to send one.
- #22 needs `oracle_id` to be **absent**. Generators produce present-and-valid
  values, never structured absence.
- #21 needs 21+ **stable** ids across two pages with a round-tripping cursor.
  A stateless generator would return fresh cards for page 2.

## Shared fixtures

`stub/data/reversible-cards.json` is loaded by **both**
`tests/fixtures/reversible_cards.py` and `stub/fixtures.ts`, so pytest and
Tier B cannot disagree about what a reversible card is. Editing it changes
both suites; `ci.yml`'s `backend` paths-filter includes it for that reason.

The stub's `$text` matching is an OR over terms, as MongoDB's is - which is
why the shared query `"propaganda tower"` returns both documents in either
suite.

## Why the configs are split

Playwright's `webServer` is top-level, not per-project, and Tier C needs a
different server from A and B. So: `playwright.config.ts` for A+B,
`playwright.live.config.ts` for C.

`test/e2e-tiers.test.ts` asserts the split holds - that neither config
discovers the other's specs, and that no spec sits in a directory neither
config runs.

## Tier B runs a production build

`next dev` never prerenders, so anything about caching, ISR or prerendering is
invisible against it. Measured: with #34's bug present, a dev server answers
the intercepting route with 200 and the test passes. Tier B therefore boots
`next build && next start`. `E2E_DEV_SERVER=1` swaps back for fast local
iteration, at the cost of the specs that need a real build skipping themselves
- loudly.

## What no tier can catch

- **The image optimizer**, below Tier C. jsdom and Browser Mode both mock
  `next/image` away and neither harness runs a Next server, so `/_next/image`
  just 404s there. `live/smoke.spec.ts` is the only thing watching it.
- **The real network.** `API_URL=http://api:8000` resolving inside the Docker
  network, real Mongo indexes, Meilisearch availability - all Tier C.
- **Whether the stub matches production.** It matches the *committed contract*,
  which the backend job proves is current. Deploy skew is a different
  question.

## Writing a new spec

Pick the tier by what the spec needs, not by convenience:

- asserts something true with no data at all → `static/`
- needs card data, but any deterministic card data will do → `stubbed/`
- needs *real* data, a real database, or a real deploy → `live/`

If a spec would be equally true in two tiers, put it in the cheaper one.
