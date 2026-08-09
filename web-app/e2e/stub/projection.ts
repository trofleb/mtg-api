import type { components } from "../../lib/api-types";

/**
 * Turning a Scryfall document into what the API returns.
 *
 * The stub's fixtures are written as source documents - the shape that sits
 * in Mongo - and projected here, rather than being written directly as
 * responses. That is deliberate: `CARD_PROJECTION` and `AGGREGATE_CARD` are
 * where several of these bugs live, so a fixture that skipped the projection
 * would be asserting against a shape nothing produces.
 */

type OracleCard = components["schemas"]["OracleCard"];
type CardPrinting = components["schemas"]["CardPrinting"];

/** A Scryfall document as it sits in Mongo, before any projection. */
export interface SourceCard {
  id: string;
  name: string;
  lang?: string;
  layout?: string;
  cmc?: number;
  type_line?: string;
  oracle_text?: string;
  mana_cost?: string;
  colors?: string[];
  color_identity?: string[];
  rarity?: string;
  set?: string;
  set_name?: string;
  artist?: string;
  released_at?: string;
  card_faces?: { name: string; oracle_id?: string; image_uris?: Record<string, string> }[];
}

function thumbnailsOf(source: SourceCard): string[] {
  const faces = source.card_faces ?? [];
  if (faces.length > 0) {
    return faces.map((face, i) => face.image_uris?.normal ?? `${source.id}-face-${i}.jpg`);
  }
  return [`https://cards.scryfall.io/normal/${source.id}.jpg`];
}

/**
 * Project one printing the way `CARD_PROJECTION` does.
 *
 * `oracleId` is optional and the key is omitted when it is absent, not set to
 * null: a `reversible_card` has no top-level oracle_id in Scryfall's data at
 * all, and that absence is the whole of #22.
 */
function printing(source: SourceCard, oracleId: string | undefined): CardPrinting {
  const faces = source.card_faces ?? [];
  const thumbnails = thumbnailsOf(source);

  return {
    id: source.id,
    name: source.name,
    ...(oracleId === undefined ? {} : { oracle_id: oracleId }),
    lang: source.lang ?? "en",
    layout: source.layout ?? "normal",
    cmc: source.cmc ?? 0,
    type_line: source.type_line ?? null,
    oracle_text: source.oracle_text ?? null,
    mana_cost: source.mana_cost ?? null,
    colors: source.colors ?? [],
    color_identity: source.color_identity ?? source.colors ?? [],
    rarity: source.rarity ?? "common",
    set: source.set ?? "tst",
    set_name: source.set_name ?? "Test Set",
    artist: source.artist ?? null,
    released_at: source.released_at ?? null,
    thumbnail: faces.length > 1 ? null : thumbnails[0],
    faces_thumbnails: faces.length > 1 ? thumbnails : null,
  };
}

/** Aggregate a source document across its printings, the way `AGGREGATE_CARD` does. */
export function aggregate(source: SourceCard, id: string, printingOracleId?: string): OracleCard {
  const thumbnails = thumbnailsOf(source);
  const twoFaced = (source.card_faces ?? []).length > 1;

  return {
    id,
    name: source.name,
    card_count: 1,
    cards: [printing(source, printingOracleId)],
    card_text: source.oracle_text ?? null,
    cmc: source.cmc ?? 0,
    colors: source.colors ?? [],
    mana_cost: source.mana_cost ?? null,
    rarity: source.rarity ?? "common",
    type_line: source.type_line ?? null,
    thumbnail: twoFaced ? null : thumbnails[0],
    faces_thumbnails: twoFaced ? thumbnails : null,
    // Structurally null in production too: both ingestion tasks delete
    // edhrec_rank before insert and CARD_PROJECTION projects neither rank.
    edhrec_rank: null,
    penny_rank: null,
  };
}
