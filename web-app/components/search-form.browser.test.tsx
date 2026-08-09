import type { ReactNode } from "react";
import { expect, test } from "vitest";
import { page } from "vitest/browser";
import { render } from "vitest-browser-react";
import { SearchForm } from "@/components/search-form";
import type { SearchState } from "@/lib/search-params";

// These assertions are about *pixels*, so they need a real layout engine.
// jsdom's getBoundingClientRect() returns zeros no matter what, which would
// make every ratio below NaN or 0 and prove nothing.

const STATE: SearchState = { query: "dragon", cursor: null, filters: {} };

// The collapse in #36 is not a property of search-form.tsx on its own: it
// depends on `min-h-screen p-8` and `max-w-7xl mx-auto` from app/page.tsx.
// This is a reconstruction of that container and reconstructions drift, so
// Branch 6 keeps one thin e2e-B check against the real page as well.
function PageShell({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <div className="space-y-6">{children}</div>
      </div>
    </main>
  );
}

async function renderAtWidth(width: number) {
  await page.viewport(width, 720);
  const screen = await render(
    <PageShell>
      <SearchForm sets={[]} state={STATE} />
    </PageShell>
  );
  const input = screen.container.querySelector<HTMLInputElement>('input[type="text"]');
  if (!input) throw new Error("search input not found");
  const row = input.parentElement;
  if (!row) throw new Error("search input has no parent row");
  return { screen, input, row };
}

test("the harness renders with real Tailwind and a real layout engine", async () => {
  const { screen, input, row } = await renderAtWidth(320);
  const main = screen.container.querySelector("main");
  if (!main) throw new Error("shell did not render");

  // p-8 is 2rem. An unstyled <main> has 0px padding, so this fails loudly if
  // globals.css was not loaded and no measurement below can be trusted.
  expect(getComputedStyle(main).paddingLeft).toBe("32px");
  // px-3 on the Input, versus Chromium's 2px default for a bare <input>.
  expect(getComputedStyle(input).paddingLeft).toBe("12px");
  // flex-1 on the input only means anything inside a flex container.
  expect(getComputedStyle(row).display).toBe("flex");
  // ...and jsdom would report 0 here.
  expect(main.getBoundingClientRect().width).toBeGreaterThan(0);
  expect(input.getBoundingClientRect().height).toBeGreaterThan(0);
});

// Issue #36: at 320px the search input measures ~26px wide, of which ~24px is
// horizontal padding, because the Search and Filters buttons take the whole
// row and the input has no min-w-0 to shrink against.
//
// Asserted as a ratio of the row rather than in absolute px: the shell above
// is a reconstruction, and a px threshold would encode its drift instead of
// the bug.
//
// Measured: 26px of a 256px row, a ratio of 0.1015625. Worth recording that
// with globals.css *not* imported the same ratio measures 0.478 - close
// enough to the threshold that a looser bound would have gone green off the
// unstyled defaults and proved nothing. Hence the harness check above.
//
// FIXED BY BRANCH 6 (`fix/search-form`), NOT HERE. It is marked `.fails` so
// CI stays green while the assertion stays in the tree. When Branch 6 lands,
// this reports "expected to fail, but passed" - drop the `.fails` then.
test("#36 - search input keeps a usable share of its row at 320px", async () => {
  const { input, row } = await renderAtWidth(320);

  const inputWidth = input.getBoundingClientRect().width;
  const rowWidth = row.getBoundingClientRect().width;
  expect(rowWidth).toBeGreaterThan(0);

  // The primary control of the app should own at least half of its row.
  expect(inputWidth / rowWidth).toBeGreaterThan(0.5);
});
