import type { CardFilter } from "@/lib/api";

// Search state lives in the URL, not in React state. That is what lets the
// server render results: page.tsx reads these params, fetches, and returns
// finished HTML. It also makes every search shareable and the back button
// work for free.

export const DEFAULT_QUERY = "Black Lotus";
export const CMC_MIN = 0;
export const CMC_MAX = 16;

/** Raw searchParams as Next.js hands them to a page. */
export type RawSearchParams = Record<string, string | string[] | undefined>;

export interface SearchState {
  query: string;
  cursor: string | null;
  filters: CardFilter;
}

function toArray(value: string | string[] | undefined): string[] {
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

/**
 * Read a CMC bound as the integer the API will accept.
 *
 * cmc_min and cmc_max are declared `int` on the endpoint, so a fractional
 * bound comes back 422 - and since searchCards runs inside a server
 * component, that 422 surfaces to the user as a 500 page instead of a
 * search (issue #28). The slider only ever produces integers, so a fraction
 * here means a hand-edited or stale URL: round it rather than discard a
 * filter the URL plainly asks for.
 */
function toIntegerBound(value: string | string[] | undefined): number | undefined {
  const raw = Array.isArray(value) ? value[0] : value;
  if (raw === undefined || raw === "") return undefined;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? Math.round(parsed) : undefined;
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/** Read a URL query string into the state a search needs. */
export function parseSearchParams(params: RawSearchParams): SearchState {
  const sets = toArray(params.sets);
  const colors = toArray(params.colors);
  const types = toArray(params.types);
  const rarities = toArray(params.rarities);

  const cmcMin = toIntegerBound(params.cmc_min);
  const cmcMax = toIntegerBound(params.cmc_max);

  const colorOperator = first(params.color_operator);
  const isOperator =
    colorOperator === "or" || colorOperator === "and" || colorOperator === "exactly";

  return {
    query: first(params.q) || DEFAULT_QUERY,
    cursor: first(params.cursor) ?? null,
    filters: {
      sets: sets.length > 0 ? sets : undefined,
      colors: colors.length > 0 ? colors : undefined,
      color_operator: colors.length > 0 && isOperator ? colorOperator : undefined,
      cmc_min: cmcMin !== undefined && cmcMin > CMC_MIN ? cmcMin : undefined,
      cmc_max: cmcMax !== undefined && cmcMax < CMC_MAX ? cmcMax : undefined,
      types: types.length > 0 ? types : undefined,
      rarities: rarities.length > 0 ? rarities : undefined,
    },
  };
}

/**
 * Build a query string from search state. `cursor` is passed explicitly so
 * paging links can advance it while keeping the query and filters intact.
 */
export function buildSearchParams(state: SearchState): string {
  const params = new URLSearchParams();
  const { query, cursor, filters } = state;

  if (query) params.set("q", query);

  for (const set of filters.sets ?? []) params.append("sets", set);
  for (const color of filters.colors ?? []) params.append("colors", color);
  for (const type of filters.types ?? []) params.append("types", type);
  for (const rarity of filters.rarities ?? []) params.append("rarities", rarity);

  if (filters.color_operator) params.set("color_operator", filters.color_operator);
  if (filters.cmc_min !== undefined) params.set("cmc_min", String(filters.cmc_min));
  if (filters.cmc_max !== undefined) params.set("cmc_max", String(filters.cmc_max));

  // Deliberately last: a cursor is only meaningful for the exact query and
  // filters above, so changing any of them must drop it.
  if (cursor) params.set("cursor", cursor);

  return params.toString();
}
