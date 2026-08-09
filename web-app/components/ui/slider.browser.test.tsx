import { useState } from "react";
import { expect, test } from "vitest";
import { userEvent } from "vitest/browser";
import { render } from "vitest-browser-react";
import { Slider } from "@/components/ui/slider";

// Issue #37. `search-form.tsx` drives this Slider with a two-value range
// (`value={cmcRange}`, a `[number, number]`), but slider.tsx hard-coded a
// single <Thumb>. Radix derives thumb count from what it is given to render,
// not from the value array, so only the minimum handle ever appeared and
// `cmc_max` could not be moved by mouse, touch or keyboard.
//
// Why this file is a *browser* spec and not jsdom: counting `role="slider"`
// elements would pass in jsdom, but that asserts DOM shape rather than the
// defect. Radix computes a slider's value from the track's
// getBoundingClientRect() during a pointer drag, and jsdom returns zeros for
// that no matter what. Only a real drag in a real layout engine proves the
// max value is reachable, which is what the issue actually claims.

const CMC_MIN = 0;
const CMC_MAX = 16;

// A fixed pixel width rather than a viewport-relative one: the drag below
// converts pixels back into slider values, so the geometry has to be
// deterministic and independent of whatever viewport a sibling spec left set.
const TRACK_WIDTH = 320;

/**
 * Mirrors how `search-form.tsx` uses the component: fully controlled, with a
 * two-entry value array. Every emitted value is recorded so the test can
 * assert on the range itself rather than on a thumb's aria-valuenow, which in
 * the buggy build describes the wrong thumb.
 */
function ControlledRange({ onChange }: { onChange: (value: number[]) => void }) {
  const [value, setValue] = useState<number[]>([CMC_MIN, CMC_MAX]);
  return (
    <div style={{ width: `${TRACK_WIDTH}px` }}>
      <Slider
        min={CMC_MIN}
        max={CMC_MAX}
        step={1}
        value={value}
        onValueChange={(next) => {
          setValue(next);
          onChange(next);
        }}
      />
    </div>
  );
}

async function renderRange() {
  const emitted: number[][] = [];
  const screen = await render(<ControlledRange onChange={(v) => emitted.push(v)} />);

  // Radix puts data-orientation on both the root and the track; the root comes
  // first in document order, and the root's rect is what getValueFromPointer
  // scales against.
  const root = screen.container.querySelector<HTMLElement>('[data-orientation="horizontal"]');
  if (!root) throw new Error("slider root did not render");

  const thumbs = screen.getByRole("slider").elements() as HTMLElement[];
  return {
    screen,
    root,
    thumbs,
    emitted,
    /** The range after the last change, or the initial range if nothing moved. */
    current: () => emitted.at(-1) ?? [CMC_MIN, CMC_MAX],
  };
}

test("#37 - a two-value Slider renders one thumb per value, labelled", async () => {
  const { root, thumbs } = await renderRange();

  // Guard: jsdom would report 0 here and every measurement below would be a lie.
  expect(root.getBoundingClientRect().width).toBe(TRACK_WIDTH);

  expect(thumbs).toHaveLength(2);
  expect(thumbs.map((t) => t.getAttribute("aria-label"))).toEqual(["Minimum", "Maximum"]);
  expect(thumbs.map((t) => t.getAttribute("aria-valuenow"))).toEqual(["0", "16"]);
});

// Deriving the thumbs from `value` also changes what a *single*-value slider
// renders, so pin that down too: still one handle, and no "Minimum" label on a
// control that has no maximum to pair it with.
test("a single-value Slider still renders exactly one, unlabelled thumb", async () => {
  const screen = await render(
    <div style={{ width: `${TRACK_WIDTH}px` }}>
      <Slider min={CMC_MIN} max={CMC_MAX} step={1} defaultValue={[5]} />
    </div>
  );

  const thumbs = screen.getByRole("slider").elements();
  expect(thumbs).toHaveLength(1);
  expect(thumbs[0].getAttribute("aria-label")).toBeNull();
  expect(thumbs[0].getAttribute("aria-valuenow")).toBe("5");
});

// The one that matters. A real trusted pointer drag through Playwright's input
// pipeline - not a synthetic PointerEvent, which cannot take pointer capture.
test("#37 - dragging the max thumb lowers the max of the range", async () => {
  const { root, thumbs, current } = await renderRange();

  const rect = root.getBoundingClientRect();
  expect(rect.width).toBe(TRACK_WIDTH);

  // The rightmost thumb: the maximum handle once #37 is fixed, and the *only*
  // (minimum) handle before it is. Dragging it to the middle of the track is
  // therefore either "max 16 -> 8" or "min 0 -> 8" depending on the bug, which
  // is exactly what the assertions below distinguish.
  const maxThumb = thumbs.at(-1);
  if (!maxThumb) throw new Error("slider rendered no thumbs at all");

  // Declared as a variable, not an inline literal: the public
  // UserEventDragAndDropOptions type is `{}`, but the playwright provider
  // forwards it verbatim to frame.dragAndDrop, which honours these.
  const dragOptions = {
    targetPosition: { x: rect.width / 2, y: rect.height / 2 },
    force: true,
  };
  await userEvent.dragAndDrop(maxThumb, root, dragOptions);

  const [min, max] = current();

  // Midpoint of a 0-16 range. Allow a pixel of slop in the pointer landing.
  expect(max).toBeGreaterThanOrEqual(7);
  expect(max).toBeLessThanOrEqual(9);
  // ...and the drag must not have dragged the *minimum* instead, which is the
  // precise failure mode of the single-thumb build.
  expect(min).toBe(CMC_MIN);
});

// #37 reports the max as unreachable by mouse, touch *and* keyboard. The
// keyboard path is a separate Radix code path (onKeyDown resolves which value
// to change from the focused thumb's index in its collection), so it needs its
// own assertion.
test("#37 - the max thumb is reachable and adjustable by keyboard", async () => {
  const { thumbs, current } = await renderRange();

  const maxThumb = thumbs.at(-1);
  if (!maxThumb) throw new Error("slider rendered no thumbs at all");

  maxThumb.focus();
  expect(document.activeElement).toBe(maxThumb);

  await userEvent.keyboard("{ArrowLeft}");

  const [min, max] = current();
  expect(max).toBe(CMC_MAX - 1);
  expect(min).toBe(CMC_MIN);
});
