import { expect, test } from "vitest";
import { render } from "vitest-browser-react";
import { CardTile } from "@/components/card-tile";
import type { OracleCard } from "@/lib/api";

// Issue #22, client half. The API is what should never emit a card without an
// id - Branch 3's grouping fix plus the required `id` on OracleCard see to
// that. This is the guard behind it: a tile that cannot be linked must not
// pretend to be a link.
//
// `normaliseCard`'s `id: rest.id ?? _id ?? ""` fallback is why an empty string
// is the shape to test rather than undefined. Fed one, this component built
// `href="/card/"`, which Next normalises to `/card` - a route that does not
// exist. The user saw an ordinary card and got a 404 on click.
//
// Browser Mode rather than jsdom because the claim is about what the user can
// interact with: a real <a href> is focusable and navigable, and only a real
// browser has an opinion about that.

const CARD: OracleCard = {
  id: "b29c8b8a-2c8f-4891-88bc-f35d07a68293",
  name: "Lightning Bolt",
  card_count: 1,
  cards: [],
  mana_cost: "{R}",
  rarity: "common",
};

async function renderTile(card: OracleCard) {
  return await render(<CardTile card={card} />);
}

test("a card with an id renders as a link to that card", async () => {
  const screen = await renderTile(CARD);

  const link = screen.container.querySelector("a");
  expect(link).not.toBeNull();
  expect(link?.getAttribute("href")).toBe(`/card/${CARD.id}`);
});

test("a card with an empty id renders no link", async () => {
  const screen = await renderTile({ ...CARD, id: "" });

  expect(screen.container.querySelector("a")).toBeNull();
  // Nothing anchor-shaped either: a role="link" would be just as misleading.
  expect(screen.container.querySelector('[role="link"]')).toBeNull();
});

test("a card with an empty id is still rendered, just not clickable", async () => {
  const screen = await renderTile({ ...CARD, id: "" });

  // Dropping the tile would hide a real card and silently shorten the page.
  // The card stays visible; only the navigation goes away.
  await expect.element(screen.getByText("Lightning Bolt")).toBeInTheDocument();
});

test("an unlinked tile is not focusable, so it cannot be tabbed into", async () => {
  const screen = await renderTile({ ...CARD, id: "" });

  const focusable = screen.container.querySelectorAll(
    'a[href], button, [tabindex]:not([tabindex="-1"])'
  );
  expect(focusable.length).toBe(0);
});
