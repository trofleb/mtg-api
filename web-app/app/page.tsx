import Link from "next/link";
import { CardGrid } from "@/components/card-grid";
import { SearchForm } from "@/components/search-form";
import { Button } from "@/components/ui/button";
import { getAllSets, searchCards } from "@/lib/api";
import { buildSearchParams, parseSearchParams, type RawSearchParams } from "@/lib/search-params";

// Async server component: the search runs here, on the server, inside the
// Docker network. Results are in the initial HTML, so the page is readable
// without JavaScript and every search is a shareable URL.

interface HomeProps {
  searchParams: Promise<RawSearchParams>;
}

export default async function Home({ searchParams }: HomeProps) {
  const state = parseSearchParams(await searchParams);

  // Both calls are server-side; run them together rather than in sequence.
  const [results, sets] = await Promise.all([
    searchCards(state.query, state.cursor, state.filters),
    getAllSets().catch(() => [] as string[]),
  ]);

  const nextHref =
    results.has_more && results.cursor
      ? `/?${buildSearchParams({ ...state, cursor: results.cursor })}`
      : null;

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Magic the Gathering Card Search</h1>
          <p className="text-muted-foreground">
            Card info comes from the{" "}
            <a
              href="https://scryfall.com/docs/api"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              Scryfall API
            </a>
            . Thank you so much for all the data!
          </p>
        </header>

        <div className="space-y-6">
          <SearchForm sets={sets} state={state} />

          {results.cards.length > 0 && (
            <div className="flex items-center justify-between">
              {/* The API counts the whole result set, so this is the real
                  number rather than "however many are on this page, plus".
                  It used to read results.cards.length + "+" when has_more,
                  which said "20+ results found" on every page of every
                  search - and on the last page too (issue #25). */}
              <p className="text-sm text-muted-foreground">
                <strong>{results.total}</strong> {results.total === 1 ? "result" : "results"} found
              </p>
            </div>
          )}

          <CardGrid cards={results.cards} />

          {(state.cursor || nextHref) && (
            <div className="flex justify-center gap-2 pt-4">
              {state.cursor && (
                <Button variant="outline" asChild>
                  <Link href={`/?${buildSearchParams({ ...state, cursor: null })}`}>
                    Back to start
                  </Link>
                </Button>
              )}
              {nextHref && (
                <Button variant="outline" asChild>
                  <Link href={nextHref}>Load More Cards</Link>
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
