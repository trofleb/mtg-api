import { expect, test, vi } from "vitest";
import { getCardByOracleId, type OracleCard } from "@/lib/api";
import { generateMetadata } from "./page";

// Issue #41: a card link pasted into Slack, Discord, WhatsApp or a tweet
// unfurls as a bare title with no picture, because generateMetadata only ever
// returned `title`. Every one of those clients reads og: / twitter: tags and
// nothing else.
//
// Logic layer, not Component: generateMetadata is an exported async function
// that returns a plain object. It never renders, so there is nothing for a
// browser to measure - jsdom (the "unit" project) is the right home.

// The page imports notFound from next/navigation. vitest.setup.ts's mock of
// that module does not export it, and a mocked module throws when an export it
// does not define is touched - so this file declares its own.
vi.mock("next/navigation", () => ({
  notFound: vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  }),
}));

vi.mock("@/lib/api", () => ({ getCardByOracleId: vi.fn() }));

const CARD: OracleCard = {
  id: "b29c8b8a-2c8f-4891-88bc-f35d07a68293",
  name: "Lightning Bolt",
  card_count: 3,
  cards: [],
  thumbnail: "https://cards.scryfall.io/normal/front/b/2/lightning-bolt.jpg",
  type_line: "Instant",
  card_text: "Lightning Bolt deals 3 damage to any target.",
};

function metadataFor(card: OracleCard | null) {
  vi.mocked(getCardByOracleId).mockResolvedValue(card);
  return generateMetadata({ params: Promise.resolve({ id: CARD.id }) });
}

test("#41 - a shared card link carries an og: image", async () => {
  const metadata = await metadataFor(CARD);

  expect(
    metadata.openGraph,
    "no openGraph block at all: every unfurl falls back to the bare <title>"
  ).toBeDefined();
  expect(JSON.stringify(metadata.openGraph?.images)).toContain(CARD.thumbnail);
});

test("#41 - the og: block names the card and describes it", async () => {
  const metadata = await metadataFor(CARD);

  expect(metadata.openGraph?.title).toContain("Lightning Bolt");
  expect(metadata.openGraph?.description).toContain("3 damage");
});

test("#41 - twitter: tags are present, with a large image card", async () => {
  const metadata = await metadataFor(CARD);

  expect(metadata.twitter, "X/Twitter ignores og: alone for the card style").toBeDefined();
  expect(JSON.stringify(metadata.twitter)).toContain(CARD.thumbnail);
  // `card` is only on the discriminated members of Next's Twitter union, so
  // this reads it off the serialised object rather than narrowing.
  expect(JSON.stringify(metadata.twitter)).toContain("summary_large_image");
});

test("#41 - a double-faced card falls back to its front face image", async () => {
  const faces = ["https://cards.scryfall.io/normal/front/a/a/front.jpg"];
  const metadata = await metadataFor({
    ...CARD,
    thumbnail: undefined,
    faces_thumbnails: faces,
  });

  expect(JSON.stringify(metadata.openGraph?.images)).toContain(faces[0]);
});

test("#41 - an unknown card is still titled, and advertises no image", async () => {
  const metadata = await metadataFor(null);

  expect(metadata.title).toBe("Card not found");
  // A 404 unfurling with somebody else's artwork would be worse than no card.
  expect(JSON.stringify(metadata.openGraph?.images ?? [])).not.toContain("scryfall");
});
