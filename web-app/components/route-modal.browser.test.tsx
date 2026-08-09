import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { beforeEach, expect, test, vi } from "vitest";
import { userEvent } from "vitest/browser";
import { render } from "vitest-browser-react";
import { CardTile } from "@/components/card-tile";
import { RouteModal } from "@/components/route-modal";
import type { OracleCard } from "@/lib/api";

// Issue #40, modal half.
//
// Two defects, one component. Both are real in production and both are
// invisible to jsdom:
//
//   1. Escape closes the dialog and focus lands on <body>. A keyboard user is
//      returned to the top of the document and has to tab back through the
//      whole grid to reach the card they were just on. Radix normally restores
//      focus to the node that was focused when the dialog mounted - but this
//      modal closes with router.back(), the results grid re-mounts, and the
//      node Radix stored is detached. Calling focus() on a detached element is
//      a silent no-op.
//   2. DialogContent always sets aria-describedby to an id Radix generates for
//      DialogDescription. No DialogDescription is rendered here, so the
//      reference dangles. A screen reader is told a description exists and
//      then finds nothing.
//
// The harness below reproduces the *re-mount*, which is the whole mechanism:
// `generation` is a key on the grid, so router.back() hands React fresh DOM
// exactly as a real back-navigation does. Without that, Radix's own
// restoration would work and the test would pass with the bug present.
//
// What is deliberately NOT tested here, because it already works and the plan
// says so: the focus trap itself, and <main> being aria-hidden while open.

const CARD: OracleCard = {
  id: "b29c8b8a-2c8f-4891-88bc-f35d07a68293",
  name: "Lightning Bolt",
  card_count: 1,
  cards: [],
  mana_cost: "{R}",
  rarity: "common",
};

const CARD_PATH = `/card/${CARD.id}`;

let openModal = () => {};
let goBack = () => {};

function Harness() {
  const [state, setState] = useState({ open: false, generation: 0 });

  openModal = () => setState((s) => ({ ...s, open: true }));
  // What router.back() does from the user's point of view: the modal goes away
  // and the page underneath is rendered again from scratch.
  goBack = () => setState((s) => ({ open: false, generation: s.generation + 1 }));

  return (
    <>
      <main>
        <h1>Magic the Gathering Card Search</h1>
        <div key={state.generation}>
          <CardTile card={CARD} />
        </div>
      </main>
      {state.open && (
        <RouteModal title={CARD.name}>
          <p>Card details</p>
        </RouteModal>
      )}
    </>
  );
}

/** The tile's anchor, re-queried because a re-mount replaces the node. */
function tile(): HTMLAnchorElement {
  const anchor = document.querySelector<HTMLAnchorElement>(`a[href^="${CARD_PATH}"]`);
  if (!anchor) throw new Error("card tile link not found");
  return anchor;
}

function dialog(): HTMLElement {
  const el = document.querySelector<HTMLElement>('[role="dialog"]');
  if (!el) throw new Error("dialog is not open");
  return el;
}

beforeEach(() => {
  vi.mocked(usePathname).mockReturnValue(CARD_PATH);
  vi.mocked(useRouter).mockReturnValue({
    back: () => goBack(),
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  } as unknown as ReturnType<typeof useRouter>);
});

async function openFromTile() {
  await render(<Harness />);
  tile().focus();
  expect(document.activeElement, "the tile has to hold focus before opening").toBe(tile());

  openModal();
  await vi.waitFor(() => dialog());
}

test("#40 - focus returns to the originating tile after Escape", async () => {
  await openFromTile();

  await userEvent.keyboard("{Escape}");

  await vi.waitFor(() => {
    expect(document.querySelector('[role="dialog"]'), "the dialog should have closed").toBeNull();
    expect(
      document.activeElement,
      "focus was dropped on the floor - a keyboard user is back at the top of the document"
    ).toBe(tile());
  });
});

test("#40 - the restored tile is the live one, not the node Radix stored", async () => {
  await openFromTile();
  const stale = tile();

  await userEvent.keyboard("{Escape}");

  await vi.waitFor(() => {
    expect(document.activeElement).toBe(tile());
  });
  // The grid re-mounted, so the element Radix would have restored to is gone
  // from the document. If this is ever the same node the harness has stopped
  // reproducing the bug and the test above proves nothing.
  expect(stale.isConnected, "the harness must re-mount the grid").toBe(false);
});

test("#40 - the dialog does not point at a description that was never rendered", async () => {
  await openFromTile();

  const describedBy = dialog().getAttribute("aria-describedby");
  if (describedBy !== null) {
    expect(
      document.getElementById(describedBy),
      `aria-describedby="${describedBy}" resolves to nothing`
    ).not.toBeNull();
  }
  expect(describedBy).toBeNull();
});

test("#40 - the focus trap still moves focus into the dialog on open", async () => {
  // Regression net for the fix above: overriding onCloseAutoFocus must not
  // disturb the open-side behaviour, which the plan records as already correct.
  await openFromTile();

  await vi.waitFor(() => {
    expect(dialog().contains(document.activeElement)).toBe(true);
  });
});
