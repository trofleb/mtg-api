import type { components } from "../../lib/api-types";
import { ALL_CARDS, scoreOf } from "./fixtures";

/**
 * Search, filtering and cursor paging for the stub.
 *
 * Pure functions over the fixtures, so the integration layer can call them
 * directly and Tier B gets the same answers over HTTP.
 *
 * Modelled on the API *after* Branch 2: results are ordered by relevance
 * descending then id ascending, and the cursor is `"<score>:<id>"` - the
 * position the next page continues from. Emitting a cursor that round-trips
 * is the whole of #21, so the stub must not fake it with an offset.
 */

type OracleCard = components["schemas"]["OracleCard"];
type SearchResultCard = components["schemas"]["SearchResultCard"];
type SearchResponse = components["schemas"]["SearchResponse"];

export interface SearchQuery {
  text: string;
  cursor?: string | null;
  pageCount?: number;
  sets?: string[];
  colors?: string[];
  colorOperator?: string | null;
  cmcMin?: number;
  cmcMax?: number;
  types?: string[];
  rarities?: string[];
}

const searchableText = (card: OracleCard): string =>
  [card.name, card.type_line ?? "", card.card_text ?? ""].join(" ").toLowerCase();

/**
 * A card matches if *any* term does, because MongoDB's `$text` is an OR over
 * terms.
 *
 * That is not a detail: `tests/fixtures/reversible_cards.py` picks the query
 * "propaganda tower" precisely because one term hits each of the two shared
 * reversible documents. An AND stub would return nothing for it, and pytest
 * and Tier B would disagree about the fixtures they are both built on.
 */
function matchesText(card: OracleCard, text: string): boolean {
  const haystack = searchableText(card);
  const terms = text.toLowerCase().split(/\s+/).filter(Boolean);
  return terms.some((term) => haystack.includes(term));
}

function matchesColors(card: OracleCard, colors: string[], operator: string | null): boolean {
  if (colors.length === 0) return true;
  const own = card.colors ?? [];

  if (operator === "exactly") {
    return own.length === colors.length && colors.every((c) => own.includes(c));
  }
  if (operator === "and") {
    return colors.every((c) => own.includes(c));
  }
  return colors.some((c) => own.includes(c));
}

function matchesFilters(card: OracleCard, query: SearchQuery): boolean {
  const sets = card.cards.map((printing) => printing.set ?? "");
  const typeLine = (card.type_line ?? "").toLowerCase();
  const cmc = card.cmc ?? 0;

  if (query.sets?.length && !query.sets.some((set) => sets.includes(set))) return false;
  if (!matchesColors(card, query.colors ?? [], query.colorOperator ?? null)) return false;
  if (query.cmcMin !== undefined && cmc < query.cmcMin) return false;
  if (query.cmcMax !== undefined && cmc > query.cmcMax) return false;
  if (query.types?.length && !query.types.some((t) => typeLine.includes(t.toLowerCase()))) {
    return false;
  }
  if (query.rarities?.length && !query.rarities.includes(card.rarity ?? "")) return false;

  return true;
}

/** `"<score>:<id>"`, the same shape the API emits. */
export function encodeCursor(card: SearchResultCard): string {
  return `${card.score}:${card.id}`;
}

function positionOf(ranked: SearchResultCard[], cursor: string): number {
  const [, id] = cursor.split(":");
  const index = ranked.findIndex((card) => card.id === id);
  // An unknown cursor is not silently treated as "start from the top" - that
  // is #24, and a stub that forgives it hides the bug it exists to expose.
  if (index < 0) throw new Error(`unknown cursor: ${cursor}`);
  return index + 1;
}

/** Rank every match, highest score first, ties broken by id. */
export function rankedMatches(query: SearchQuery): SearchResultCard[] {
  return ALL_CARDS.filter((card) => matchesText(card, query.text) && matchesFilters(card, query))
    .map((card) => ({ ...card, score: scoreOf(card.id) }))
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0) || a.id.localeCompare(b.id));
}

export function search(query: SearchQuery): SearchResponse {
  const ranked = rankedMatches(query);
  const pageCount = query.pageCount ?? 20;
  const start = query.cursor ? positionOf(ranked, query.cursor) : 0;
  const page = ranked.slice(start, start + pageCount);
  const hasMore = start + page.length < ranked.length;
  const last = page.at(-1);

  return {
    cards: page,
    has_more: hasMore,
    cursor: hasMore && last ? encodeCursor(last) : null,
  };
}

export function cardById(id: string): OracleCard | undefined {
  return ALL_CARDS.find((card) => card.id === id);
}
