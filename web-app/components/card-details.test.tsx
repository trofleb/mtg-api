import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { CardDetails } from "@/components/card-details";
import type { OracleCard } from "@/lib/api";
import { render } from "@/test/test-utils";

// Issue #35 - the back face of a double-faced card has never been rendered.
//
// The two-face branch was guarded by `!thumbnail`, and `thumbnail` was derived
// as `card.thumbnail || card.faces_thumbnails?.[0]`. A non-empty
// faces_thumbnails therefore *guarantees* the guard is false, so the branch it
// guards is unreachable by construction and the front face is drawn alone.
//
// jsdom is enough: this counts nodes, not pixels. `next/image` is mocked to a
// plain <img> in vitest.setup.ts, which is fine here for the same reason -
// the claim is about how many images the component decides to render, not
// about how any of them is loaded.

const FRONT = "https://cards.scryfall.io/normal/delver-front.jpg";
const BACK = "https://cards.scryfall.io/normal/delver-back.jpg";

const BASE_CARD: OracleCard = {
  id: "e2f3a4b5-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
  name: "Delver of Secrets // Insectile Aberration",
  card_count: 1,
  cards: [],
  type_line: "Creature — Human Wizard // Creature — Human Insect",
};

function cardImages(): HTMLImageElement[] {
  // Scoped to the image column: the printings list further down also renders
  // images, and counting those would make the assertion mean nothing.
  return screen.queryAllByRole("img").filter((img) => {
    const src = img.getAttribute("src") ?? "";
    return src === FRONT || src === BACK;
  }) as HTMLImageElement[];
}

describe("CardDetails images", () => {
  test("a card with two faces_thumbnails renders two images", () => {
    render(<CardDetails card={{ ...BASE_CARD, faces_thumbnails: [FRONT, BACK] }} />);

    const images = cardImages();
    expect(images).toHaveLength(2);
    expect(images.map((img) => img.getAttribute("src"))).toEqual([FRONT, BACK]);
  });

  test("both faces are given distinguishable accessible names", () => {
    render(<CardDetails card={{ ...BASE_CARD, faces_thumbnails: [FRONT, BACK] }} />);

    const names = cardImages().map((img) => img.getAttribute("alt"));
    expect(new Set(names).size).toBe(2);
    for (const name of names) {
      expect(name).toContain(BASE_CARD.name);
    }
  });

  test("a thumbnail alongside two faces does not hide the back face", () => {
    // Which of the two wins is not the question - a card whose back face
    // exists must show it either way. The aggregated pipeline can produce
    // both fields at once, since `thumbnail` and `faces_thumbnails` come from
    // different source paths.
    render(
      <CardDetails card={{ ...BASE_CARD, thumbnail: FRONT, faces_thumbnails: [FRONT, BACK] }} />
    );

    expect(cardImages().map((img) => img.getAttribute("src"))).toContain(BACK);
  });

  test("a single-faced card still renders exactly one image", () => {
    render(<CardDetails card={{ ...BASE_CARD, thumbnail: FRONT }} />);

    expect(cardImages()).toHaveLength(1);
  });

  test("a lone faces_thumbnails entry renders one image, not a two-up grid", () => {
    // A split or adventure card projects `faces_thumbnails` from face images
    // that mostly do not exist, so a one-entry array is a real shape and must
    // not be laid out as if a second face were missing.
    render(<CardDetails card={{ ...BASE_CARD, faces_thumbnails: [FRONT] }} />);

    expect(cardImages()).toHaveLength(1);
  });

  test("a card with no images at all says so", () => {
    render(<CardDetails card={BASE_CARD} />);

    expect(cardImages()).toHaveLength(0);
    expect(screen.getByText("No image available")).toBeInTheDocument();
  });

  test("an empty faces_thumbnails array is treated as no image", () => {
    render(<CardDetails card={{ ...BASE_CARD, faces_thumbnails: [] }} />);

    expect(screen.getByText("No image available")).toBeInTheDocument();
  });
});
