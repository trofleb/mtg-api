import { expect, test, vi } from "vitest";
import { page } from "vitest/browser";
import { render } from "vitest-browser-react";
import { SearchForm } from "@/components/search-form";
import type { SearchState } from "@/lib/search-params";

// Issue #40, tap target. The "x" that removes a selected set is a bare
// <button> wrapping a 12x12 icon with no padding of its own, so its hit area
// is roughly 12x12 CSS px. WCAG 2.2 SC 2.5.8 (Target Size, Minimum) asks for
// 24x24. On a phone it is a coin-flip whether a tap lands.
//
// Browser Mode is not optional here: this is a layout measurement, and jsdom's
// getBoundingClientRect() returns zeros whatever the CSS says.
//
// NOTE ON OWNERSHIP: the button itself lives in search-form.tsx, which Branch 6
// also rewrites. The size comes from a shared primitive in components/ui so the
// two branches do not fight over the same lines - but this spec deliberately
// measures the button as SearchForm actually renders it, so a rewrite that drops
// the primitive fails loudly instead of silently regressing the fix.

const MIN_TAP_TARGET_PX = 24; // WCAG 2.2 SC 2.5.8

const STATE: SearchState = {
  query: "goblin",
  cursor: null,
  filters: { sets: ["Alpha"] },
};

async function removeButtonForSelectedSet() {
  await page.viewport(1024, 768);
  const screen = await render(<SearchForm sets={["Alpha", "Beta"]} state={STATE} />);

  // The selected-set badges only exist once the filter panel is open.
  await screen.getByRole("button", { name: "Filters" }).click();

  const button = await vi.waitFor(() => {
    const found = Array.from(screen.container.querySelectorAll("button")).find((candidate) =>
      candidate.parentElement?.textContent?.startsWith("Alpha")
    );
    if (!found) throw new Error("no remove button inside the 'Alpha' badge");
    return found;
  });

  return button;
}

test("the harness renders with real Tailwind", async () => {
  const button = await removeButtonForSelectedSet();

  // Tailwind's preflight resets every border to 0. Chromium's default <button>
  // border is 2px outset - and an unstyled button's default padding is enough
  // to clear 24px of width on its own, so without this guard the measurement
  // below could pass off the browser defaults and prove nothing.
  expect(getComputedStyle(button).borderTopWidth).toBe("0px");
});

test("#40 - the set badge's remove button meets the minimum tap target", async () => {
  const rect = (await removeButtonForSelectedSet()).getBoundingClientRect();

  expect(rect.width).toBeGreaterThanOrEqual(MIN_TAP_TARGET_PX);
  expect(rect.height).toBeGreaterThanOrEqual(MIN_TAP_TARGET_PX);
});
