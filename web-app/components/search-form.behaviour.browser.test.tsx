import { useRouter } from "next/navigation";
import { beforeEach, expect, test, vi } from "vitest";
import { userEvent } from "vitest/browser";
import { render } from "vitest-browser-react";
import { SearchForm } from "@/components/search-form";
import type { CardFilter } from "@/lib/api";
import type { SearchState } from "@/lib/search-params";

// Branch 6 behaviour: #23 (stale state after Back), #33 (Clear All), #38
// (works without JavaScript) and the search-form half of #40 (accessible
// names). Layout lives in search-form.browser.test.tsx.
//
// Browser Mode rather than jsdom because every claim here is about what the
// browser itself does with the markup: FormData off a real <form>, the
// accessibility tree behind getByRole, and real clicks on real buttons.

let push: ReturnType<typeof vi.fn>;

beforeEach(() => {
  push = vi.fn();
  vi.mocked(useRouter).mockReturnValue({
    push,
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  } as unknown as ReturnType<typeof useRouter>);
});

function stateOf(query: string, filters: CardFilter = {}): SearchState {
  return { query, cursor: null, filters };
}

type Screen = Awaited<ReturnType<typeof render>>;

// Deliberately selected on type rather than on name="q": the name is itself
// under test in #38, and a selector that assumed it would make #23 and #40
// fail for the wrong reason before the fix lands.
function searchInput(screen: Screen): HTMLInputElement {
  const input = screen.container.querySelector<HTMLInputElement>('input[type="text"]');
  if (!input) throw new Error("search input not found");
  return input;
}

function searchForm(screen: Screen): HTMLFormElement {
  const form = screen.container.querySelector("form");
  if (!form) throw new Error("no <form> around the search input");
  return form;
}

// --- #23 ------------------------------------------------------------------

test("#23 - the input follows the URL when the page re-renders after Back", async () => {
  const screen = await render(<SearchForm sets={[]} state={stateOf("dragon")} />);
  expect(searchInput(screen).value).toBe("dragon");

  // What Back does: the URL changes, the server re-renders the page, and this
  // client component keeps its place in the tree and is handed new props.
  await screen.rerender(<SearchForm sets={[]} state={stateOf("goblin")} />);

  expect(searchInput(screen).value).toBe("goblin");
});

test("#23 - filters follow the URL too, not just the query", async () => {
  const screen = await render(
    <SearchForm sets={["Alpha"]} state={stateOf("dragon", { types: ["Creature"] })} />
  );
  await screen.getByRole("button", { name: "Filters" }).click();
  // aria-pressed is how a toggle button says which way it is set; the variant
  // swap it relied on is invisible to anything but a sighted user (#40).
  await expect
    .element(screen.getByRole("button", { name: "Creature" }))
    .toHaveAttribute("aria-pressed", "true");

  await screen.rerender(<SearchForm sets={["Alpha"]} state={stateOf("dragon")} />);

  await expect
    .element(screen.getByRole("button", { name: "Creature" }))
    .toHaveAttribute("aria-pressed", "false");
});

// A guard, not a reproduction: this one already passes on the unfixed
// component, which never syncs at all. It is here so the fix cannot be a
// blanket copy-props-into-state on every render, which would delete what the
// user is typing whenever anything re-renders the page.
test("#23 - a re-render at the same URL does not discard what the user is typing", async () => {
  const screen = await render(<SearchForm sets={[]} state={stateOf("dragon")} />);
  await userEvent.fill(searchInput(screen), "goblin");

  // Same URL, fresh object - exactly what a server re-render hands down.
  await screen.rerender(<SearchForm sets={[]} state={stateOf("dragon")} />);

  expect(searchInput(screen).value).toBe("goblin");
});

// --- #33 ------------------------------------------------------------------

test("#33 - Clear All applies the cleared filters instead of leaving results filtered", async () => {
  const screen = await render(
    <SearchForm sets={["Alpha"]} state={stateOf("dragon", { types: ["Creature"], cmc_max: 3 })} />
  );
  await screen.getByRole("button", { name: "Filters" }).click();
  await screen.getByRole("button", { name: "Clear All" }).click();

  // Without this the badges and toggles go quiet while the grid below stays
  // filtered, and nothing on screen says the two disagree.
  expect(push).toHaveBeenCalledTimes(1);
  expect(push).toHaveBeenCalledWith("/?q=dragon");
});

// --- #38 ------------------------------------------------------------------

test("#38 - the search input sits in a GET form, so it works without JavaScript", async () => {
  const screen = await render(<SearchForm sets={[]} state={stateOf("dragon")} />);
  const form = searchForm(screen);

  expect(form.getAttribute("method")?.toLowerCase()).toBe("get");
  expect(form.getAttribute("action")).toBe("/");
  expect(searchInput(screen).getAttribute("name")).toBe("q");
});

test("#38 - a no-JavaScript submit carries the applied filters and drops the cursor", async () => {
  const state: SearchState = {
    query: "dragon",
    cursor: "0.5:abc",
    filters: { types: ["Creature"], colors: ["R"], color_operator: "or", cmc_max: 3 },
  };
  const screen = await render(<SearchForm sets={[]} state={state} />);

  // FormData off a real form is exactly what the browser would send.
  const data = new FormData(searchForm(screen));
  expect(data.get("q")).toBe("dragon");
  expect(data.getAll("types")).toEqual(["Creature"]);
  expect(data.getAll("colors")).toEqual(["R"]);
  expect(data.get("color_operator")).toBe("or");
  expect(data.get("cmc_max")).toBe("3");
  // A cursor only means anything for the query it was issued against.
  expect(data.get("cursor")).toBeNull();
});

test("#38 - filter toggles do not submit the form", async () => {
  const screen = await render(<SearchForm sets={["Alpha"]} state={stateOf("dragon")} />);
  await screen.getByRole("button", { name: "Filters" }).click();

  // Inside a <form> a <button> defaults to type="submit". Every control that
  // only edits pending state has to opt out, or picking a colour would fire
  // off a search - and without JavaScript, reload the page.
  const submitters = [...searchForm(screen).querySelectorAll("button")].filter(
    (button) => (button.getAttribute("type") ?? "submit") === "submit"
  );
  expect(submitters.map((button) => button.textContent?.trim())).toEqual([
    "Search",
    "Apply Filters",
  ]);
});

// --- #40 (search-form half) ----------------------------------------------

test("#40 - the search input is labelled, not merely placeholder-ed", async () => {
  const screen = await render(<SearchForm sets={[]} state={stateOf("dragon")} />);
  const input = searchInput(screen);

  // getByRole(..., { name }) on its own passes against the unfixed component:
  // the accessible-name algorithm falls back to the placeholder as a last
  // resort. A placeholder is not a label - it is exposed as a hint, and it
  // disappears the moment anything is typed. Require a real association.
  const labelled = (input.labels?.length ?? 0) > 0 || input.hasAttribute("aria-label");
  expect(labelled).toBe(true);
  await expect.element(screen.getByRole("textbox", { name: /search/i })).toBeInTheDocument();
});

test("#40 - each set badge's remove button has an accessible name", async () => {
  const screen = await render(
    <SearchForm sets={["Alpha", "Beta"]} state={stateOf("dragon", { sets: ["Alpha"] })} />
  );
  await screen.getByRole("button", { name: "Filters" }).click();

  // The button holds only an <X> icon, so unnamed it reads as just "button".
  await expect.element(screen.getByRole("button", { name: "Remove set Alpha" })).toBeVisible();
});
