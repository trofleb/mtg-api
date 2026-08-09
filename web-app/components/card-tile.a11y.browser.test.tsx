import { expect, test } from "vitest";
import { render } from "vitest-browser-react";
import { CardTile } from "@/components/card-tile";
import type { OracleCard } from "@/lib/api";

// Issue #40, tile half.
//
// A tile's accessible name is built from everything inside the anchor, so a
// screen reader announces the image alt, then the name again, then the raw
// mana cost, then the rarity emoji: "Lightning Bolt Lightning Bolt {R} large
// yellow circle, link". The braces are Scryfall's mana notation, not English,
// and the emoji is a decoration whose meaning is already in the `title`.
//
// The name is also the only handle a voice-control user has ("click Lightning
// Bolt"), and it does not match what is on screen.
//
// Browser Mode because an accessible name is computed by the browser from the
// live accessibility tree - aria-hidden subtrees, alt="" images and all. jsdom
// has no accessibility tree to compute it from.

const CARD: OracleCard = {
  id: "b29c8b8a-2c8f-4891-88bc-f35d07a68293",
  name: "Lightning Bolt",
  card_count: 1,
  cards: [],
  mana_cost: "{R}",
  rarity: "rare",
  thumbnail: "https://cards.scryfall.io/normal/front/b/2/lightning-bolt.jpg",
};

test("#40 - the tile's accessible name is the card name and nothing else", async () => {
  const screen = await render(<CardTile card={CARD} />);

  await expect
    .element(screen.getByRole("link", { name: "Lightning Bolt", exact: true }))
    .toBeInTheDocument();
});

test("#40 - the mana cost is marked decorative", async () => {
  const screen = await render(<CardTile card={CARD} />);

  const mana = Array.from(screen.container.querySelectorAll("span")).find(
    (el) => el.textContent === CARD.mana_cost
  );
  expect(mana, "the mana cost should still be on screen").toBeDefined();
  expect(mana?.closest('[aria-hidden="true"]')).not.toBeNull();
});

test("#40 - the rarity emoji is marked decorative", async () => {
  const screen = await render(<CardTile card={CARD} />);

  const emoji = Array.from(screen.container.querySelectorAll("span")).find((el) =>
    /\p{Extended_Pictographic}/u.test(el.textContent ?? "")
  );
  expect(emoji, "the rarity emoji should still be on screen").toBeDefined();
  expect(emoji?.closest('[aria-hidden="true"]')).not.toBeNull();
});

test("#40 - the card name is a level-2 heading, not a level-3 one", async () => {
  // app/page.tsx opens with an <h1> and there is no <h2> anywhere, so every
  // tile heading skips a level. Screen reader users navigate by heading level;
  // a jump from 1 to 3 reads as a missing section.
  const screen = await render(<CardTile card={CARD} />);

  const headings = Array.from(screen.container.querySelectorAll("h1,h2,h3,h4,h5,h6"));
  expect(headings.map((h) => h.tagName)).toEqual(["H2"]);
});
