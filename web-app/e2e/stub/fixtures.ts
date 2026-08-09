import type { components } from "../../lib/api-types";
import reversibleDocument from "./data/reversible-cards.json";

/**
 * Deterministic fixtures for the API stub.
 *
 * Typed against `lib/api-types.ts`, which is generated from the committed
 * `openapi.json` - so the stub cannot drift from the contract without `tsc`
 * saying so, and `validate.ts` re-checks every response at runtime.
 *
 * Hand-written rather than generated, because every interesting case here is
 * a shape a generator cannot produce: a *missing* field, stable ids across
 * two pages, a specific status for a specific id. See "The stub: generated
 * contract, hand-written fixtures" in fix-ui-issues.md.
 */

type OracleCard = components["schemas"]["OracleCard"];
type CardPrinting = components["schemas"]["CardPrinting"];

/** A Scryfall document as it sits in Mongo, before any projection. */
interface SourceCard {
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

const REVERSIBLE_SOURCE = reversibleDocument.cards as SourceCard[];

/** Search text that returns exactly the two reversible cards, as in pytest. */
export const REVERSIBLE_SEARCH_TEXT: string = reversibleDocument.search_text;

/**
 * An oracle id no fixture carries, for #29 and #30.
 *
 * Well-formed on purpose: a malformed id could 404 for the wrong reason
 * (rejected before lookup) and the not-found page would never be exercised.
 */
export const BOGUS_CARD_ID = "00000000-0000-4000-8000-000000000000";

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
function aggregate(source: SourceCard, id: string, printingOracleId?: string): OracleCard {
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

/**
 * #22 - reversible cards, keyed on the *face* oracle id.
 *
 * Two of them, so a test can tell "grouped correctly" apart from "collapsed
 * into a single null-keyed bucket". Their printings carry no `oracle_id`,
 * exactly as the shared source documents do.
 */
const REVERSIBLE_CARDS: OracleCard[] = REVERSIBLE_SOURCE.map((source) =>
  aggregate(source, source.card_faces?.[0]?.oracle_id ?? source.id)
);

/** #35 - a transform card, so exactly two `faces_thumbnails` reach the client. */
const DOUBLE_FACED_CARD: OracleCard = aggregate(
  {
    id: "aaaa1111-2222-4333-8444-555566667777",
    name: "Delver of Secrets // Insectile Aberration",
    layout: "transform",
    cmc: 1,
    type_line: "Creature - Human Wizard // Creature - Human Insect",
    oracle_text: "At the beginning of your upkeep, look at the top card of your library.",
    mana_cost: "{U}",
    colors: ["U"],
    rarity: "common",
    set: "isd",
    set_name: "Innistrad",
    released_at: "2011-09-30",
    card_faces: [
      {
        name: "Delver of Secrets",
        oracle_id: "dddd1111-2222-4333-8444-555566667777",
        image_uris: { normal: "https://cards.scryfall.io/normal/delver-front.jpg" },
      },
      {
        name: "Insectile Aberration",
        oracle_id: "dddd1111-2222-4333-8444-555566667777",
        image_uris: { normal: "https://cards.scryfall.io/normal/delver-back.jpg" },
      },
    ],
  },
  "dddd1111-2222-4333-8444-555566667777",
  "dddd1111-2222-4333-8444-555566667777"
);

/** #26 - a name containing `//`, the character that breaks the path form. */
const SPLIT_CARD: OracleCard = aggregate(
  {
    id: "bbbb1111-2222-4333-8444-555566667777",
    name: "Fire // Ice",
    layout: "split",
    cmc: 2,
    type_line: "Instant // Instant",
    oracle_text: "Fire deals 2 damage divided as you choose. // Tap target permanent.",
    mana_cost: "{1}{R} // {1}{U}",
    colors: ["R", "U"],
    rarity: "uncommon",
    set: "apc",
    set_name: "Apocalypse",
    released_at: "2001-06-01",
  },
  "ffff1111-2222-4333-8444-555566667777",
  "ffff1111-2222-4333-8444-555566667777"
);

const BLACK_LOTUS: OracleCard = aggregate(
  {
    id: "cccc1111-2222-4333-8444-555566667777",
    name: "Black Lotus",
    cmc: 0,
    type_line: "Artifact",
    oracle_text: "{T}, Sacrifice Black Lotus: Add three mana of any one color.",
    mana_cost: "{0}",
    colors: [],
    rarity: "rare",
    set: "lea",
    set_name: "Limited Edition Alpha",
    released_at: "1993-08-05",
  },
  "eeee1111-2222-4333-8444-555566667777",
  "eeee1111-2222-4333-8444-555566667777"
);

const COLOR_CYCLE = ["W", "U", "B", "R", "G"];
const RARITY_CYCLE = ["common", "uncommon", "rare", "mythic"];

/**
 * #21 - filler so a search runs past one page.
 *
 * 21 of them plus Black Lotus is 22 matches for the app's default query,
 * which pages at 20: page 1 is full, page 2 has 2, and the ids are stable
 * across both requests - so an overlap between pages is a real finding rather
 * than a fresh roll of random data.
 */
const FILLER_CARDS: OracleCard[] = Array.from({ length: 21 }, (_, index) => {
  const n = String(index + 1).padStart(2, "0");
  const oracleId = `a111ca1d-0000-4000-8000-0000000000${n}`;
  return aggregate(
    {
      id: `f111e100-0000-4000-8000-0000000000${n}`,
      name: `Black Lotus Replica ${n}`,
      cmc: (index % 7) + 1,
      type_line: index % 2 === 0 ? "Artifact" : "Creature - Construct",
      oracle_text: `Replica number ${n}.`,
      mana_cost: `{${(index % 7) + 1}}`,
      colors: index % 3 === 0 ? [] : [COLOR_CYCLE[index % COLOR_CYCLE.length]],
      rarity: RARITY_CYCLE[index % RARITY_CYCLE.length],
      set: "tst",
      set_name: "Test Set",
      released_at: "2020-01-01",
    },
    oracleId,
    oracleId
  );
});

/** Every card the stub knows about, in a fixed order. */
export const ALL_CARDS: OracleCard[] = [
  BLACK_LOTUS,
  ...REVERSIBLE_CARDS,
  DOUBLE_FACED_CARD,
  SPLIT_CARD,
  ...FILLER_CARDS,
];

export const REVERSIBLE_CARD_IDS: string[] = REVERSIBLE_CARDS.map((card) => card.id);
export const DOUBLE_FACED_CARD_ID = DOUBLE_FACED_CARD.id;
export const SPLIT_CARD_ID = SPLIT_CARD.id;
export const BLACK_LOTUS_ID = BLACK_LOTUS.id;

export const ALL_SETS: string[] = [
  ...new Set(ALL_CARDS.flatMap((card) => card.cards.map((p) => p.set ?? ""))),
]
  .filter(Boolean)
  .sort();

/** Relevance score for a card: highest first, stable across requests. */
export function scoreOf(cardId: string): number {
  const rank = ALL_CARDS.findIndex((candidate) => candidate.id === cardId);
  return Number((10 - rank * 0.1).toFixed(4));
}
