import { useSearchParams } from "next/navigation";
import { expect, test, vi } from "vitest";
import { render } from "vitest-browser-react";
import { BackToSearch } from "@/components/back-to-search";

// Issue #39. Search for "goblin", open a card, press "Back to search" and you
// land on a fresh page of "Black Lotus" - lib/search-params.ts's DEFAULT_QUERY.
// The link is a fixed <Link href="/">, so every filter, the query and the page
// the user had reached are all discarded.
//
// Browser Mode rather than jsdom because the claim is about a real navigable
// anchor: what a user actually lands on when they activate the control.

function withSearch(search: string) {
  vi.mocked(useSearchParams).mockReturnValue(
    new URLSearchParams(search) as unknown as ReturnType<typeof useSearchParams>
  );
}

async function hrefOf(search: string): Promise<string | null | undefined> {
  withSearch(search);
  const screen = await render(<BackToSearch />);
  return screen.container.querySelector("a")?.getAttribute("href");
}

test("#39 - the back link carries the originating query", async () => {
  expect(await hrefOf("q=goblin")).toBe("/?q=goblin");
});

test("#39 - the back link carries the filters as well as the query", async () => {
  expect(await hrefOf("q=goblin&types=Creature&colors=R&cmc_max=3")).toBe(
    "/?q=goblin&types=Creature&colors=R&cmc_max=3"
  );
});

test("#39 - the back link returns to the page of results the card came from", async () => {
  // A cursor is only meaningful for the query it was issued against, and it is
  // in the URL alongside it, so it comes back too.
  expect(await hrefOf("q=goblin&cursor=1.5%3Aabc")).toBe("/?q=goblin&cursor=1.5%3Aabc");
});

test("#39 - a card reached without a query still links to the results", async () => {
  expect(await hrefOf("")).toBe("/");
});
