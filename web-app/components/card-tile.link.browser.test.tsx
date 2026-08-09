import { expect, test } from "vitest";
import { render } from "vitest-browser-react";
import { CardTile } from "@/components/card-tile";
import type { OracleCard } from "@/lib/api";

// Issue #39, outbound half. For the card page to be able to offer a back link
// that returns to the right results, the search the user came from has to
// survive the hop - and the only place it can survive is the URL of the card
// itself. The tile is what builds that URL.
//
// Browser Mode for the same reason as card-tile.browser.test.tsx: the subject
// is a real <a href>, which is a thing only a browser has an opinion about.

const CARD: OracleCard = {
  id: "b29c8b8a-2c8f-4891-88bc-f35d07a68293",
  name: "Lightning Bolt",
  card_count: 1,
  cards: [],
  mana_cost: "{R}",
  rarity: "common",
};

async function hrefOf(from?: string): Promise<string | null | undefined> {
  const screen = await render(<CardTile card={CARD} from={from} />);
  return screen.container.querySelector("a")?.getAttribute("href");
}

test("#39 - a tile carries the originating query into the card link", async () => {
  expect(await hrefOf("q=goblin&types=Creature")).toBe(`/card/${CARD.id}?q=goblin&types=Creature`);
});

test("#39 - a tile with no originating query links to the bare card page", async () => {
  expect(await hrefOf()).toBe(`/card/${CARD.id}`);
});

test("#39 - an empty originating query does not leave a trailing '?'", async () => {
  expect(await hrefOf("")).toBe(`/card/${CARD.id}`);
});

test("#39 - an unlinkable card is still not a link, query or no query", async () => {
  // Guard on Branch 3's fix (#22): threading a query must not resurrect the
  // href="/card/" that a card with no id used to produce.
  const screen = await render(<CardTile card={{ ...CARD, id: "" }} from="q=goblin" />);
  expect(screen.container.querySelector("a")).toBeNull();
});
