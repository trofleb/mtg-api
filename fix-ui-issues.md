# Fix plan — production bugs #21–#41

Plan for clearing the 21 issues found by exploring <https://mtg.nicocasa.ch> with Playwright
on 2026-08-03. Every issue was reproduced against production before it was filed.

Despite the filename the scope is not only UI: roughly a third of the defects are in the
FastAPI/MongoDB layer, and several of the most visible symptoms (dead first tile, broken
pagination, unranked search) are backend bugs surfacing in the browser.

## Ground rule

**Every branch opens with a failing test.** The test is committed first, observed failing,
and only then is the fix applied. Which *layer* the test belongs to is decided by the table
in [Test architecture](#test-architecture) — not by convenience.

This is not ceremony. Issue #34 shipped precisely because PR #17 verified that the card
route *cached* (it showed `●` in the build output and carried `Vary` headers) but never
verified it still *worked*. A single request-level assertion would have caught it.

---

## Test architecture

Six layers. Each owns a category of defect, and nothing is tested at a more expensive layer
than it needs.

| Layer | Tool | Owns | Status |
|-------|------|------|--------|
| **Logic** | Vitest (node) / pytest | Pure functions, parsers, formatters | ✅ exists |
| **Component** | Vitest Browser Mode | Rendering, interaction, a11y roles, **real layout/focus** | ❌ Branch 0c |
| **Integration** | Vitest + MSW (**node**) | Data-fetching, error states, normalisation | ❌ Branch 0d |
| **Contract** | FastAPI OpenAPI → codegen | The mock↔backend divergence problem | ❌ Branch 0b |
| **E2E** | Playwright, tiered A/B/C | Routing, SSR, headers, caching, real stack | ⚠️ exists, untiered |
| **Visual** | Playwright `toHaveScreenshot` | Design-system regressions | ⏸ deferred, not in scope |

### The seam that makes tiering possible

`lib/api.ts:68`:

```ts
const API_BASE_URL = process.env.API_URL ?? "http://api:8000";
```

All three fetches are **server-side only** — called from server components, running in the
Next.js process. There is no route handler, no proxy rewrite, no client-callable wrapper.

Two consequences, and both shape everything below:

1. **The browser never talks to the API.** MSW-in-browser and Playwright's `page.route()`
   cannot intercept the app's data fetching. MSW must run in **node**, intercepting
   `lib/api.ts`'s `fetch` directly.
2. **`API_URL` is a single-variable process boundary.** Point it at a stub and the Next
   server runs *identically* — real routing, real RSC resolution, real ISR, real headers —
   with no Mongo, no Meilisearch, no API container, and fully deterministic data. Point it
   at the real stack and you have a live smoke test. The same spec can run in both.

### Playwright tiers

| Tier | Boots | Needs a DB | Runs |
|------|-------|-----------|------|
| **A — `static`** | `next start` | no | every PR, ~5s |
| **B — `stubbed`** | `next start` + MSW node stub, `API_URL`→stub | no | every PR |
| **C — `live`** | real API + Mongo + Meili, or deployed `BASE_URL` | yes | post-deploy smoke, 5–10 journeys |

```
e2e/
  static/    tier A
  stubbed/   tier B
  live/      tier C
  stub/      the MSW server + fixtures — not tests
```

Playwright's `webServer` is top-level, not per-project: use two configs
(`playwright.config.ts` for A+B, `playwright.live.config.ts` for C). The existing config
already gates `webServer` on `BASE_URL`, so the pattern is established.

Tier A caveat: `app/page.tsx` calls `searchCards` unconditionally, so `/` cannot render
without an API. Assert security headers on `/robots.txt` instead — `headers()` in
`next.config.ts` matches by source pattern, so it proves the same thing with no data.

### The stub: generated contract, hand-written fixtures

The stub is **not** fully generated. Two parts:

| Part | Source | Guarantee |
|------|--------|-----------|
| Route table + response types | generated from `openapi.json` | cannot drift — CI regenerates and fails on diff |
| ~6 fixture documents | hand-written, typed against the generated types | deterministic; `tsc` fails if the schema moves under them |

Fully-generated response data cannot work, independent of tooling quality:

- **#29/#30 need a 404 for a bogus id.** Prism steers status with a `Prefer: code=404`
  request header, but the client here is the Next server and it cannot be made to send one.
- **#22 needs `oracle_id` to be *absent*.** Generators produce present-and-valid values,
  never structured absence.
- **#21 needs 21+ stable ids across two pages with a round-tripping cursor.** Prism is
  stateless; page 2 would return fresh random cards, possibly overlapping page 1.
- #35 needs exactly two `faces_thumbnails`; #25 needs `has_more: true`.

One MSW handler set serves both the Integration layer and Tier B, so the fixtures are
defined once.

### CI pipeline

```
PR ─┬─ backend:  ruff → pytest → emit openapi.json
    ├─ frontend: biome → tsc → vitest logic + integration → vitest browser (component)
    └─ both ok → contract: committed openapi.json == emitted?
               → e2e-A (static)
               → e2e-B (stubbed)
post-deploy ──── e2e-C live smoke against the deployed URL
nightly ──────── drift: deployed /openapi.json vs committed
```

Backend and frontend jobs stay **parallel** (they are independent, and `paths-filter`
already gates them). Only e2e is gated on both.

`openapi.json` is **committed to the repo**, not passed as an artifact. On a frontend-only
PR the backend job is skipped by `paths-filter`, so an artifact would not exist and e2e-B
could not run. Committing it means the frontend job always has a schema, the backend job
proves it is current, and schema changes are reviewable in the diff.

Generate from the **PR's own code** (`app.openapi()` offline — `api/main.py` holds no
import-time DB connection), not from production. A PR that changes the API should have
Tier B test the frontend against the API *as proposed*. Deploy skew is a different question,
answered by the nightly job.

---

## What constrains this plan

Five facts about the current setup. All checked, none assumed.

### 1. The API declares no response models

**Zero `response_model` across all 10 endpoints.** `OracleCard` at `api/router/cards.py:33`
is not a Pydantic model — it is a bare class with annotations, never instantiated, never
referenced. The handlers return raw dicts.

So `/openapi.json` today documents request params and nothing about responses. Codegen
against it yields `unknown`; a response validator has nothing to validate. **The Contract
layer cannot exist until this is fixed** (Branch 0b).

This is also the root cause of the drift class of bugs. `_expose_id`
(`api/router/cards.py:15`) is a hand-rolled per-endpoint patch for what one `response_model`
would enforce once, and `lib/api.ts:57`'s `id ?? _id ?? ""` is the frontend compensating for
the same missing contract. #22 is what that compensation costs.

`Card(PrintedCard)` at `api/router/cards.py:29` is already a real Pydantic model and
`common/scyfall_models.py` has a full hierarchy, so the ingredients exist.

### 2. Playwright never runs in CI — because it is entangled with a live API

`.github/workflows/ci.yml` runs `pytest`, Biome, `tsc` and Vitest, with zero references to
Playwright. The reason is structural: `e2e/api.spec.ts` is 153 lines of direct FastAPI
assertions behind a `test.skip` that fires whenever the API is not exposed, and
`card-search.spec.ts` asserts against live production data. The suite *cannot* run in CI as
written.

Tiering fixes this without a Docker stack: Tiers A and B need only `next start` plus a node
process.

### 3. `MockMongoCollection` manufactured false greens ✅ fixed in 0a

**Revised after 0a landed — the original wording understated this.** The mock did not merely
*lack* `$meta`. It **fabricated a relevance score for the buggy `{"$project": {"score": 1}}`
form** — the exact form `api/router/cards.py` uses today — returning one of five constants
(1.0/0.9/0.8/0.6/0.3). So a test for #21 passed whether or not the bug was fixed. The gap was
a false green, not a blind spot.

Fixing it therefore required **removing** behaviour, not just adding it. `{"score": 1}` now
projects the document's own `score` field (i.e. nothing, for card documents) as MongoDB does.
Two pre-existing tests that asserted the fabricated 0.9/0.8 constants encoded the wrong
contract and were **deleted** — `test_text_search_score_in_aggregation` and
`test_text_search_score_sorting`. Net test deletion, surfaced here deliberately.

**Consequence: 0a leaves `pytest` red on its own** —
`tests/api/router/test_cards_search_integration.py::test_search_cursor_pagination` fails with
"Found 3 duplicate cards between pages". That failure *is* issue #21, finally visible. Branch
2's one-line `$meta` fix turns it green. **0a must merge together with Branch 2**, not before.

### 4. The web app has no component tests

`web-app/test/test-utils.tsx` and `vitest.setup.ts` are wired up, but the only test files are
`lib/utils.test.ts`, `lib/search-params.test.ts` and `lib/api.test.ts`.

### 5. jsdom has no layout engine

`getBoundingClientRect()` returns zeros regardless of the `css: true` setting. Four defects
are assertions about *size* or *real focus* and are untestable in jsdom: #36, #37 (the drag,
not the thumb count), and #40's focus restoration and tap targets. These are what Browser
Mode is for; the plan previously called them e2e-only.

---

## Branch 0 — foundations, split by layer

The original single Branch 0 bundled four unrelated pieces of infrastructure. Split so they
can land independently and in parallel where possible.

### 0a — `test/mock-mongo-textscore`

Blocks Branch 2 only.

**First failing test:** assert `MockMongoCollection` projects a score for
`{"$meta": "textScore"}`. Watch it fail. Then implement, with coverage in
`tests/mocks/test_mongodb.py`. Scores must differ per document so ordering is observable.

### 0b — `test/api-contract`

Blocks 0d and the Contract layer. The largest of the four.

- `response_model` on all 5 card endpoints; promote `OracleCard` to a `BaseModel` deriving
  from the `common/scyfall_models.py` hierarchy
- `id` declared in the model, so `_expose_id` becomes an implementation detail rather than
  the contract
- emit `openapi.json` offline via `app.openapi()`; commit it
- CI step: regenerate and fail on diff
- `openapi-typescript` → `web-app/lib/api-types.ts`; derive `OracleCard`/`SearchResponse`
  from it instead of the hand-maintained interfaces at `lib/api.ts:3-56`
- **add `openapi.json` and `scripts/**` to the `backend` paths-filter in `ci.yml`.** Without
  this the staleness gate is bypassable: a commit touching only `openapi.json` skips the
  backend job entirely, so `generate_openapi.py --check` never runs — and the web-app job then
  regenerates types from the tampered document and passes. The branch's whole premise is that
  the committed document cannot drift.

**First failing test:** a pytest assertion that `app.openapi()` describes a response schema
for `/cards/oracle/{oracle_id}/aggregated` including a required `id`.

**Corrected after the first attempt — do NOT derive from the `scyfall_models` hierarchy.** The
original instruction here said to, and it is wrong: `CARD_PROJECTION` drops most of what
`PrintedCard` declares required, and the hierarchy's `UUID4`/`AnyUrl`/`Literal` types convert
odd-but-serviceable production data into 500s. Mirror the projections with independent models,
pin them to the projections with tests, and reuse a hierarchy type **only** where the value set
is closed *and verified against production*. The one hierarchy type the first attempt did reuse
— `Color = Literal["W","U","B","R","G"]` on `colors`/`color_identity` — is exactly what
reintroduced the risk: a card with `colors=["C"]` now raises `ResponseValidationError` → HTTP
500. Widen it, or add a validator that drops unknown codes, and add a test with `colors=["C"]`.

### 0c — `test/component-layer`

Independent of everything. Can land in parallel with 0a/0b.

- `@vitest/browser`, `@vitest/browser-playwright`, `vitest-browser-react` (Playwright 1.56.1
  is already a devDependency)
- Vitest 4 `projects`: a fast jsdom project for `lib/*.test.ts`, a browser project matched on
  `*.browser.test.tsx`
- **Import `app/globals.css` in the browser setup file.** Without Tailwind v4 actually
  loaded, every measurement is the unstyled default and #36's test passes for the wrong
  reason. This is the single most likely thing to go wrong — **and it fails by 4%, not
  obviously**: measured without Tailwind the input/container ratio is 0.478 against a 0.5
  threshold. It looks like a marginal miss, not a broken harness. That is why the spec carries
  a guard assertion that Tailwind is really applied before it trusts any measurement.
- `playwright install --with-deps chromium` in the `test-web-app` CI job

Note two render idioms will coexist: `@testing-library/react` for jsdom,
`vitest-browser-react` locators for browser. `vi.mock` works in both, so the
`next/navigation` and `next/image` mocks carry over unchanged.

**First failing test:** render `SearchForm` at a 320px viewport and assert the input's width
as a *ratio* of its container. Absolute px thresholds are brittle — see the fidelity caveat
in Branch 6.

### 0d — `test/e2e-tiers`

Depends on 0b for the generated types.

- `e2e/stub/`: MSW handlers + the deterministic fixtures, typed against `lib/api-types.ts`
  - a reversible card with **no** `oracle_id` (#22)
  - a two-face double-faced card (#35)
  - a card whose name contains `//` (#26)
  - at least 21 cards, so pagination past a page is observable (#21)
  - a known-bogus id that 404s (#29, #30)
- runtime validation of every stub response against the schema
- `e2e/{static,stubbed,live}/` split; move `api.spec.ts`'s assertions to pytest and delete it
  from the Playwright suite
- both Playwright configs; Tiers A and B in the `test-web-app` job

---

## Branches

| # | Branch | Issues | Layer | First failing test |
|---|--------|--------|-------|--------------------|
| 1 | `fix/modal-interception` | #34 | E2E-B | request-level, `Next-Url` header |
| 2 | `fix/search-relevance-and-cursor` | #21, #24 | Logic (pytest) | pytest |
| 3 | `fix/reversible-card-ids` | #22 | Contract + Integration + Component | pytest + msw + browser |
| 4 | `fix/search-query-encoding` | #26 | Contract + Integration | pytest + msw |
| 5 | `fix/filter-validation` | #27, #28 | Logic | pytest + vitest node |
| 6 | `fix/search-form` | #23, #33, #36, #38, part of #40 | Component (browser) + E2E-B | browser + e2e-B |
| 7 | `fix/error-pages` | #29, #30 | E2E-B | e2e-B |
| 8 | `fix/double-faced-cards` | #35 | Component (jsdom) | vitest |
| 9 | `fix/card-page-metadata` | #39, #41 | Logic + Component | vitest |
| 10 | `fix/slider-range` | #37 | Component (browser) | browser, real drag |
| 11 | `fix/modal-a11y` | rest of #40 | Component (browser) | browser |
| 12 | `chore/headers-and-static` | #31, #32 | E2E-A | e2e-A |
| 13 | `feat/result-total` | #25 | Contract + E2E-B | pytest + e2e-B |

---

### Branch 1 — `fix/modal-interception` (#34)

Goes **first, ahead of all foundations.** It is a live regression from PR #17 degrading every
card click right now, and the fix is deleting two lines.

**First failing test** — Playwright `request` fixture:

```
GET /card/<id>  with headers  RSC: 1, Next-Url: /   →  expect 200   (currently 404)
GET /card/<id>  with headers  RSC: 1                →  expect 200   (already passes)
```

The two differ only by `Next-Url`, which is what the router sends when navigating from within
the app.

**Fix:** remove `export const revalidate` and `generateStaticParams` from
`app/@modal/(.)card/[id]/page.tsx:11-15`. Prerendering an *intercepting* route makes the
response independent of the client's router state tree, so `children` collapses to
`__DEFAULT__` and 404s.

Keep the identical exports on `app/card/[id]/page.tsx` — the standalone page is where the
caching win actually is, and it is unaffected. Adding `app/default.tsx` also returns 200 but
serves the default component instead of the real grid, so it is not the right fix.

**Tier note:** run it against Tier C now, using a card id from the live API, because the
regression is live and the stub does not exist yet. **Promote the same spec to Tier B once
0d lands** — the assertion is unchanged, only `API_URL` moves. Do not skip the promotion:
against Tier C the test depends on production data.

**`next dev` never prerenders — so this test is invisible in the default local run.** Measured:
against a dev server the *unfixed* code answers the `Next-Url` request with 200 and the
assertion passes with the bug fully present. Both `just test-e2e` and `just test-e2e-vps` boot
`pnpm run dev`. The spec therefore detects whether the server under test actually prerenders
(the hour-long `s-maxage` on the standalone card page, which only appears in a production
build) and skips loudly rather than reporting a false pass. **To attest the red you need
`next build && next start` or `just test-e2e-prod`.**

**Two open loops on this branch:** the spec now self-skips, which is the same
always-firing-skip pattern §2 criticises in `api.spec.ts` — acceptable only because the skip
message is diagnostic. And `e2e/live/` sits inside `playwright.config.ts`'s default
`testDir: "./e2e"`, so it is picked up by the ordinary run. **0d must split the configs** —
folded into its checklist.

Not unit-testable: the behaviour only exists in RSC routing. The bug is in module-level
exports the server reads to decide whether to prerender, not in code React runs — import
`CardModal` and render it and it passes, as it always did.

---

### Branch 2 — `fix/search-relevance-and-cursor` (#21, #24)

Depends on 0a. Grouped because one line causes both.

**First failing tests** (pytest):

1. searching an exact card name returns that card in the results
2. the emitted cursor's score component parses as a float
3. page 2 shares no ids with page 1
4. an unparseable cursor logs a warning instead of being silently dropped

**Fix:** project the text score properly —
`{"$project": {"score": {"$meta": "textScore"}, **CARD_PROJECTION}}` — then confirm `$sort`
orders by real relevance and the cursor round-trips.

Today `score` is null for every card, so `$sort` degenerates to `_id` ascending, the cursor is
emitted as the literal string `None:<id>`, and `float("None")` throws on the next request into
a bare `except: pass`. The result is a pagination loop that returns HTTP 200 throughout with
nothing in the logs.

**Files:** `api/router/cards.py`

---

### Branch 3 — `fix/reversible-card-ids` (#22)

Depends on 0b (the model that makes `id` required) and 0d (the fixture).

**First failing tests:**

- pytest: every card in a search response has a non-null id; two reversible cards do not
  merge into one result
- msw/integration: `normaliseCard` given a document with neither `id` nor `_id` does not
  silently produce `""`
- browser: `CardTile` given a card with an empty id renders no `<Link>`

**Fix:** group on something that exists for reversible layouts (the face oracle id, or the
card id) instead of `"_id": "$oracle_id"`. Scryfall omits top-level `oracle_id` on
`reversible_card` layouts because each face carries its own, so today every such card lands
in one `_id: null` bucket that sorts first — and `normaliseCard`'s `?? ""` fallback turns it
into `href="/card"`.

Add the client guard regardless: a card with no id should not render as a link. It also breaks
React's `key={card.id}` if two ever share a page.

With 0b landed, the `id`-required response model turns this from a silent `""` into a
validation error at the boundary — which is the real fix. The guard is defence in depth.

**Files:** `api/helpers/cards_mongo.py`, `web-app/components/card-tile.tsx`,
`web-app/lib/api.ts`

---

### Branch 4 — `fix/search-query-encoding` (#26)

**First failing tests:**

- pytest: searching `Fire // Ice` returns 200
- msw/integration: `searchCards` builds a query parameter, not a path segment

**Fix:** move the search text out of the URL path and into a query parameter. The endpoint
already takes query params for every filter. Today `encodeURIComponent` produces `%2F`, the
ASGI server decodes it before routing, and FastAPI's `{text}` segment (`[^/]+`) stops matching
— so any name containing `//` 500s, including names the app itself displays.

**Breaking change — see Open decisions.**

**Files:** `api/router/cards.py`, `web-app/lib/api.ts`, `web-app/lib/api.test.ts`,
`app/utils/api.py`

---

### Branch 5 — `fix/filter-validation` (#27, #28)

Grouped as one pass over filter input handling across both layers.

**First failing tests:**

- pytest: `types=(` returns 200 rather than 500; `types=.*` does not return the unfiltered set
- vitest (node): `parseSearchParams` drops or rounds `cmc_min=1.5`

**Fix:** validate `types` against the known set (the UI only ever sends 8 values) or drop the
regex for an `$in` match; `re.escape` if a regex must stay. Reject non-integer CMC in
`toNumber` so the client cannot send a value the API's own type contract forbids.

`types=Cre.ture` currently returns the full result set, which is what proves the value is used
as a live regex.

**Files:** `api/router/cards.py`, `web-app/lib/search-params.ts`

---

### Branch 6 — `fix/search-form` (#23, #33, #36, #38, part of #40)

Everything that rewrites `search-form.tsx`, kept together so the edits do not collide.
Includes the search-input label and set-badge button names from #40.

**First failing tests:**

- browser: rerendering with new props updates the input (Back-button desync)
- browser: Clear All triggers a submit rather than only local state
- browser: a `<form method="GET">` exists with `name="q"` on the input
- browser: the input has an accessible name; badge remove buttons have accessible names
- browser: input width as a ratio of its container at 320px and 375px
- e2e-B: the same width assertion on the real page

**Fix:** key the component off the URL (or sync state to props); make `clearFilters` submit;
wrap the input in a GET form; let the flex row wrap below `sm` and give the input `min-w-0`.

At 320px the input is currently 26px wide, of which ~24px is padding — the primary control of
the app is unusable on every phone.

**Fidelity caveat:** the collapse depends on `<main className="min-h-screen p-8">` and
`max-w-7xl mx-auto` from `app/page.tsx:31-32`, not on `search-form.tsx` alone. A component
test must wrap `SearchForm` in a reconstruction of that container, and reconstructions drift.
Assert a **ratio**, not absolute px, and keep the one thin e2e-B check on the real page.

**Note:** #38's *markup* is browser-testable (`<form method="GET">` with `name="q"` exists).
Whether it actually submits **without JavaScript** is not — Browser Mode always has JS. That
half stays e2e-B with `javaScriptEnabled: false`.

**Files:** `web-app/components/search-form.tsx`, `web-app/app/page.tsx`

---

### Branch 7 — `fix/error-pages` (#29, #30)

**First failing tests** (e2e-B, against the stub's known-bogus id):

- with JavaScript disabled, `/card/<bogus-id>` renders visible text (currently 0 characters)
- a 404 for an unknown card is not served from cache for an hour (`x-nextjs-cache` MISS→HIT
  across two requests)

**Fix:** add `app/not-found.tsx` and `app/error.tsx`; give the not-found branch its own short
revalidate. There are currently no error boundaries anywhere in `web-app/app/` — the route
tree is only 6 files — so with the `@modal` parallel slot the built-in fallback resolves
client-side only. That also means the `generateMetadata` "Card not found" title never reaches
the user, and the 404 page has no links at all.

Not component-testable, for two stacked reasons: the fix is a file that does not exist yet
(the test subject is Next's boundary resolution walking the route tree), and "without JS" is a
property of the transport, not of the tree — a component test cannot observe pre-hydration
HTML. #30 additionally lives in server-side `.next/cache` state and is only visible across two
requests.

**Files:** `web-app/app/not-found.tsx` (new), `web-app/app/error.tsx` (new),
`web-app/app/card/[id]/page.tsx`

---

### Branch 8 — `fix/double-faced-cards` (#35)

**First failing test** (vitest, jsdom is sufficient — this counts nodes, not pixels):
`CardDetails` given a card with two `faces_thumbnails` renders two images.

**Fix:** decide the branch on face count rather than on a derived thumbnail. The current
condition is a contradiction — the faces branch requires `!thumbnail`, but `thumbnail` is
`card.thumbnail || card.faces_thumbnails?.[0]`, so a non-empty array guarantees it is truthy.
The two-face renderer is unreachable and no back face has ever been displayed.

**Files:** `web-app/components/card-details.tsx`

---

### Branch 9 — `fix/card-page-metadata` (#39, #41)

**First failing tests:**

- vitest (node): `generateMetadata` returns `openGraph` including the card image
- browser: the "Back to search" link carries the originating query

**Fix:** thread the search query through to the card page; extend the existing
`generateMetadata` with `openGraph` and `twitter`. Today "Back to search" is a fixed
`<Link href="/">`, which re-runs the hardcoded `DEFAULT_QUERY`.

**Files:** `web-app/app/card/[id]/page.tsx`, `web-app/components/card-tile.tsx`

---

### Branch 10 — `fix/slider-range` (#37)

Depends on 0c.

**First failing tests** (browser):

- `Slider` given `[0, 16]` renders two elements with `role="slider"`
- **dragging the max thumb changes `cmc_max`**

**Fix:** map over `value` to render one `<Thumb>` per entry, as current shadcn/ui does, and
label them Minimum/Maximum. `components/ui/slider.tsx:19` hard-codes a single thumb while
`search-form.tsx` drives it with a two-value range, so `cmc_max` is unreachable by mouse,
touch and keyboard alike.

**Why browser, not jsdom:** counting `role="slider"` passes in jsdom, but that asserts DOM
shape rather than the bug. Radix Slider derives its value from the track's
`getBoundingClientRect()` during a pointer drag — zeros in jsdom. Only a real drag proves
`cmc_max` is reachable, which is what the issue actually claims.

**Files:** `web-app/components/ui/slider.tsx`

---

### Branch 11 — `fix/modal-a11y` (remainder of #40)

Depends on 0c.

**First failing tests** (browser):

- focus returns to the originating tile after closing the modal with Escape
- the dialog has no dangling `aria-describedby`
- the badge remove button's hit area meets the minimum tap target

**Fix:** restore focus explicitly on close (the modal closes via `router.back()`, so the grid
re-mounts and Radix's stored trigger node is gone); pass `aria-describedby={undefined}`; hide
decorative mana-symbol and emoji text from the tile's accessible name; add the missing `<h2>`
level.

The focus *trap* already works correctly and `<main>` is properly `aria-hidden` — only
restoration is broken.

**Moved from e2e to Component.** jsdom tracks `activeElement` but not Radix's focus guards,
`pointer-events: none`, or `aria-hidden` siblings; Browser Mode has all three. Tap targets
need real layout.

**Files:** `web-app/components/route-modal.tsx`, `web-app/components/card-tile.tsx`

---

### Branch 12 — `chore/headers-and-static` (#31, #32)

**First failing tests** (e2e-A — needs no API, so this can land before 0d):

- security headers present on `/robots.txt`
- `/robots.txt` and `/favicon.ico` return 200

**Fix:** add a `headers()` block in `next.config.ts` (or set them at the reverse proxy),
`poweredByHeader: false`, `app/robots.ts`, `app/sitemap.ts`, and an `icon` route. Land the
simple headers first; CSP needs care because of the inline styles.

HSTS is the one that matters — `http://` redirects with a 301, so the first request of a
session still goes out in the clear. It is also inherently untestable below the HTTP layer:
it applies to the first plaintext request, before any document exists to run a test inside.

`public/` holds only `favicon.png`, and `app/layout.tsx:14` declares `icon: "/favicon.png"` —
so the app's own reference resolves. What 404s is the conventional `/favicon.ico`, a request
the browser chrome issues unprompted that none of our code makes.

**Files:** `web-app/next.config.ts`, `web-app/app/robots.ts` (new),
`web-app/app/sitemap.ts` (new)

---

### Branch 13 — `feat/result-total` (#25)

**First failing tests:** pytest — the search response includes a total; e2e-B — the page
renders it.

**Fix:** return a `$count` alongside the page. The count is currently derived from the page
array, so it reads "20+ results found" on every page of every search and would still say so on
page 5.

**Not component-testable:** `app/page.tsx` is an async server component, unrenderable in both
jsdom and Browser Mode. Either extract the count into a small synchronous component or assert
it at Tier B. Lowest value of the set; fine to defer.

**Files:** `api/router/cards.py`, `web-app/lib/api.ts`, `web-app/app/page.tsx`

---

## Sequencing and conflicts

**Branch 1 first**, before any foundation. Live regression, two-line fix, request-level test
that runs against Tier C today and gets promoted to Tier B later.

**0c and 0b are independent** and can run in parallel — 0c touches only `web-app/`, 0b only
`api/` plus generated types.

**Branch 12 does not wait for 0d.** Tier A needs only `next start`, so #31/#32 can land as a
CI step against a bare build.

**Branches 2, 4, 5 and 13 all touch `api/router/cards.py`.** Run them in that order rather
than in parallel.

**#40 is split deliberately.** Its search-form parts ride with Branch 6 because both rewrite
that component; the modal and tile parts stay in Branch 11.

**`[0a ‖ 0b ‖ 0c]` was wrong — corrected.** Only **0c** is independently mergeable. 0a leaves
CI red until Branch 2 lands, and 0b is a production regression until Branch 3 lands. The three
are *implementable* in parallel but not *mergeable* in parallel.

Suggested order:

```
1  →  0c  →  12  →  [0a + 2]  →  [0b + 3]  →  0d  →  4  →  5  →  7  →  6  →  8  →  9  →  10  →  11  →  13
                     └─ merge as one unit ─┘
```

Branches 8–11 are Component-layer only and fully parallel once 0c has landed — they need
neither 0b nor 0d.

### Status as of 2026-08-07

| | State |
|---|---|
| **0c** | ✅ **merged** — `test/component-layer`. Real Chromium in CI, 37 unit + 2 browser specs green. |
| **1** (#34) | 🟡 implemented, **red never attested**. Needs a production build to verify. |
| **0a** | 🟡 implemented, holds CI red by design. Merge with Branch 2. |
| **0b** | 🟡 implemented, **two open defects**: `colors` literal 500s, and the paths-filter bypass. Do not deploy without Branch 3. |

1, 0a and 0b are preserved on `wip/foundations-0a-0b-34`, off `test/component-layer`. Snapshot
of the raw workflow output is on `wip/workflow-snapshot`.

**Next unit of work:** `[0a + 2]` then `[0b + 3]`, including the two 0b defect fixes. That
restores a green suite, makes 0b safe to deploy, and closes #21, #22 and #24.

---

## Open decisions

**#26 is a breaking API change.** `/cards/search/{text}` has two callers:
`web-app/lib/api.ts` and `app/utils/api.py` (the Streamlit app). Moving the query into a
parameter means updating both, plus `web-app/lib/api.test.ts`, which currently asserts the
path form. Worth noting `documentation/fastapi-testing-guide.md` already writes it as `?q=`
throughout, which suggests the parameter form was the original intent.

Alternative: keep the path form and double-encode on the client. Fragile enough that the
parameter version is worth preferring.

**#33 may be intended.** "Clear All" pairs with an explicit "Apply Filters" button, so
deferring is defensible. It is in the plan because the intermediate state shows "no filters
active" above a filtered result set. If the deferred model stays, the fix is to label the
pending state instead.

**How strict should the response models be? — RESOLVED, with a corollary learned the hard way.**
Strict on the aggregated endpoints only. But the corollary matters more than the answer:

> **Strictness on a *response* model is an availability risk, not a test-coverage question.**
> A request model rejects bad input; a response model returns HTTP 500. Any newly-required or
> newly-narrowed field must ship in the **same deploy** as the branch that guarantees it.

Two concrete consequences, both found by adversarial verification of 0b:

- **0b must not deploy without Branch 3.** Required `id` turns #22 from one dead tile into a
  `ResponseValidationError`. Because the null-keyed group sorts *first*, affected searches would
  return **nothing** instead of 20 results with one bad tile. 0b alone is a regression.
- **Narrowing is as dangerous as requiring.** `colors: list[Color]` 500s on `colors=["C"]`.
  Whether production emits `"C"` is still **unverified** — the API is not publicly exposed. That
  unquantified exposure is itself the problem.

**Visual regression is deferred.** Not in scope; revisit once the Component layer has settled
and there is a design system worth pinning.

---

## Known test blind spots

Stated so nobody writes a test that passes for the wrong reason:

- **`vitest.setup.ts` mocks `next/image` to a plain `<img>`.** Fine for Branch 8, which counts
  images. But **no test at any layer can catch an image-optimizer defect** — Browser Mode
  would let the mock go, but there is no Next server in the harness, so `/_next/image` just
  404s. This is how the Scryfall 400 reached production, and it remains a Tier C-only concern.
- **The stub can only be as honest as the contract.** Before 0b there is no response schema,
  so a stub written today could return anything and Tier B would still pass. That is exactly
  the divergence `lib/api.ts:52`'s "deploy independently" comment is a monument to.
- **Tier B does not test the real network.** `API_URL=http://api:8000` resolving inside the
  Docker network, real Mongo indexes, Meilisearch availability — all Tier C.
- **Integration (MSW node) does not test caching.** The fetches pass
  `next: { revalidate, tags }`; in plain Vitest that is an ignored extra property on the init
  object. Cache behaviour is Tier B/C only.
- **Component-layer layout assertions test a reconstruction**, not the real page. See Branch
  6's fidelity caveat.
- **`tests/mocks/mongodb.py` is an approximation of MongoDB.** Passing against it is not proof
  of production behaviour, particularly for `$text`, `$meta` and regex semantics. Two specific
  divergences found while implementing 0a:
  - **`$text` matching and `$meta` scoring disagree.** Matching is a substring test against
    `str(doc).lower()` — the whole document repr, including field names, UUIDs and image URLs —
    while scoring only weighs six whitelisted fields. A document can therefore match and score
    0.0, and short queries match everything: the query `"a"` matches all 12 sample cards. A test
    written on top of this can assert against an artificially broad result set.
  - **`_apply_projection` silently drops `CARD_PROJECTION`'s computed fields**
    (`thumbnail: "$image_uris.normal"`, `faces_thumbnails`), so they are always absent from
    mocked results. Directly relevant to Branch 8/#35 backend coverage.
- **Browser specs are excluded from coverage.** `test:coverage` is scoped `--project unit`, so
  once Branches 8–11 add browser specs their coverage never appears in the report.

---

## Issue index

| Issue | Severity | Branch | Layer |
|-------|----------|--------|-------|
| [#21](https://github.com/trofleb/mtg-api/issues/21) No relevance ranking; pagination loops forever | high | 2 | Logic |
| [#22](https://github.com/trofleb/mtg-api/issues/22) Reversible cards collapse to a null id; first tile 404s | high | 3 | Contract |
| [#23](https://github.com/trofleb/mtg-api/issues/23) Search box keeps old query after Back | medium | 6 | Component |
| [#24](https://github.com/trofleb/mtg-api/issues/24) Invalid cursors silently swallowed | medium | 2 | Logic |
| [#25](https://github.com/trofleb/mtg-api/issues/25) Result count only reports the current page | low | 13 | Contract + E2E-B |
| [#26](https://github.com/trofleb/mtg-api/issues/26) Names containing `/` return 500 | high | 4 | Contract |
| [#27](https://github.com/trofleb/mtg-api/issues/27) `types` filter interpolates into a `$regex` | medium | 5 | Logic |
| [#28](https://github.com/trofleb/mtg-api/issues/28) Non-integer CMC returns 500 | medium | 5 | Logic |
| [#29](https://github.com/trofleb/mtg-api/issues/29) Unknown card renders blank without JS | medium | 7 | E2E-B |
| [#30](https://github.com/trofleb/mtg-api/issues/30) 404s written to the ISR cache | low | 7 | E2E-B |
| [#31](https://github.com/trofleb/mtg-api/issues/31) No security headers | low | 12 | E2E-A |
| [#32](https://github.com/trofleb/mtg-api/issues/32) favicon.ico / robots.txt / sitemap 404 | low | 12 | E2E-A |
| [#33](https://github.com/trofleb/mtg-api/issues/33) "Clear All" leaves results filtered | low | 6 | Component |
| [#34](https://github.com/trofleb/mtg-api/issues/34) Intercepted modal 404s — regression from #17 | high | 1 | E2E-B |
| [#35](https://github.com/trofleb/mtg-api/issues/35) Back face never renders; branch unreachable | medium | 8 | Component |
| [#36](https://github.com/trofleb/mtg-api/issues/36) Search input collapses to 26px on phones | high | 6 | Component |
| [#37](https://github.com/trofleb/mtg-api/issues/37) CMC slider renders one thumb | medium | 10 | Component |
| [#38](https://github.com/trofleb/mtg-api/issues/38) Search and filters dead without JS | medium | 6 | Component + E2E-B |
| [#39](https://github.com/trofleb/mtg-api/issues/39) "Back to search" discards query and filters | medium | 9 | Component |
| [#40](https://github.com/trofleb/mtg-api/issues/40) Accessibility: labels, names, focus, tap targets | medium | 6, 11 | Component |
| [#41](https://github.com/trofleb/mtg-api/issues/41) No og:/twitter: preview on shared card links | low | 9 | Logic |
