"use client";

import { ChevronDown, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { SearchFilters } from "@/components/search-filters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CardFilter } from "@/lib/api";
import { buildSearchParams, CMC_MAX, CMC_MIN, type SearchState } from "@/lib/search-params";

// The only client component in the search path. It holds no results - it
// edits the URL, and the server re-renders the page from it. Submitting
// always drops the cursor, since a cursor only means anything for the exact
// query and filters it was issued against.
//
// It is a real <form method="GET" action="/">, so a browser with no
// JavaScript can still search: the fields below are the query string, and the
// browser assembles it natively (#38). With JavaScript, onSubmit preempts
// that and routes client-side instead. The one part that stays
// JavaScript-only is the Filters *disclosure*; the filters themselves survive
// a native submit through the hidden fields.

const SEARCH_INPUT_ID = "card-search-query";

interface SearchFormProps {
  /** Available set names, fetched on the server. */
  sets: string[];
  /** Current state, parsed from the URL on the server. */
  state: SearchState;
}

function cmcRangeOf(filters: CardFilter): [number, number] {
  return [filters.cmc_min ?? CMC_MIN, filters.cmc_max ?? CMC_MAX];
}

/** Fold the slider back into the filter shape the URL and API expect. */
function withCmc(filters: CardFilter, [min, max]: [number, number]): CardFilter {
  return {
    ...filters,
    cmc_min: min > CMC_MIN ? min : undefined,
    cmc_max: max < CMC_MAX ? max : undefined,
    color_operator: (filters.colors ?? []).length > 0 ? filters.color_operator : undefined,
  };
}

/**
 * The filters, as form fields.
 *
 * None of the filter controls is a native input, so without these a
 * no-JavaScript submit would silently drop every active filter and return the
 * unfiltered set. They are hidden rather than absent because the visible
 * controls are the ones a user reads.
 */
function FilterFields({ filters }: { filters: CardFilter }) {
  const lists: [string, string[]][] = [
    ["sets", filters.sets ?? []],
    ["colors", filters.colors ?? []],
    ["types", filters.types ?? []],
    ["rarities", filters.rarities ?? []],
  ];
  const singles: [string, string | undefined][] = [
    ["color_operator", filters.color_operator],
    ["cmc_min", filters.cmc_min?.toString()],
    ["cmc_max", filters.cmc_max?.toString()],
  ];

  return (
    <div hidden>
      {lists.flatMap(([name, values]) =>
        values.map((value) => (
          <input key={`${name}:${value}`} type="hidden" name={name} value={value} readOnly />
        ))
      )}
      {singles.map(([name, value]) =>
        value === undefined ? null : (
          <input key={name} type="hidden" name={name} value={value} readOnly />
        )
      )}
    </div>
  );
}

export function SearchForm({ sets, state }: SearchFormProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [showFilters, setShowFilters] = useState(false);

  const [query, setQuery] = useState(state.query);
  const [filters, setFilters] = useState<CardFilter>(state.filters);
  const [cmcRange, setCmcRange] = useState<[number, number]>(cmcRangeOf(state.filters));

  // Issue #23. These fields are seeded from the URL, and useState only reads
  // its initial value once - so after Back the component kept showing the
  // query the user had navigated *away* from, above results for the query the
  // URL actually asks for.
  //
  // Synced against a serialised signal rather than the props object, which is
  // rebuilt on every server render: comparing identity would re-seed on every
  // re-render and delete whatever the user was midway through typing. The
  // cursor is excluded so paging leaves an in-progress edit alone.
  const urlSignal = buildSearchParams({ ...state, cursor: null });
  const [syncedSignal, setSyncedSignal] = useState(urlSignal);
  if (urlSignal !== syncedSignal) {
    setSyncedSignal(urlSignal);
    setQuery(state.query);
    setFilters(state.filters);
    setCmcRange(cmcRangeOf(state.filters));
  }

  const update = (patch: Partial<CardFilter>) => setFilters((prev) => ({ ...prev, ...patch }));

  const navigate = (nextFilters: CardFilter, nextCmc: [number, number]) => {
    const text = query.trim();
    if (!text) return;
    const qs = buildSearchParams({
      query: text,
      cursor: null,
      filters: withCmc(nextFilters, nextCmc),
    });
    startTransition(() => router.push(`/?${qs}`));
  };

  const submit = () => navigate(filters, cmcRange);

  // Issue #33. Clearing only the local controls left the badges and toggles
  // reading "nothing selected" above a still-filtered grid, with nothing on
  // screen admitting the two disagreed. Deferring to Apply Filters was the
  // alternative - Clear All does sit next to it - but that would need new
  // copy for a pending state, and someone who presses "Clear All" wants
  // unfiltered results, not a form that agrees to want them later. Navigating
  // costs one round-trip and leaves nothing ambiguous.
  //
  // The cleared values are passed explicitly: setState is queued, so reading
  // `filters` back here would still see the old ones.
  const clearFilters = () => {
    setFilters({});
    setCmcRange([CMC_MIN, CMC_MAX]);
    navigate({}, [CMC_MIN, CMC_MAX]);
  };

  return (
    <form
      method="GET"
      action="/"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className="space-y-6"
    >
      {/* flex-wrap plus a full-width basis below sm: at 320px the buttons will
          not shrink past their text, so on one line the input was left 26px
          wide, ~24px of which was padding (#36). min-w-0 is what lets it
          shrink at all once it does share a line. */}
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor={SEARCH_INPUT_ID} className="sr-only">
          Search cards
        </label>
        <Input
          id={SEARCH_INPUT_ID}
          name="q"
          type="text"
          placeholder="Search for cards by name, text, or ability..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full min-w-0 sm:w-auto sm:flex-1"
        />
        <Button type="submit" disabled={isPending || !query.trim()}>
          <Search className="h-4 w-4" />
          <span className="ml-2">Search</span>
        </Button>
        <Button type="button" variant="outline" onClick={() => setShowFilters(!showFilters)}>
          Filters
          <ChevronDown
            className={`ml-2 h-4 w-4 transition-transform ${showFilters ? "rotate-180" : ""}`}
          />
        </Button>
      </div>

      <FilterFields filters={withCmc(filters, cmcRange)} />

      {showFilters && (
        <SearchFilters
          sets={sets}
          filters={filters}
          cmcRange={cmcRange}
          isPending={isPending}
          onChange={update}
          onCmcChange={setCmcRange}
          onClear={clearFilters}
        />
      )}
    </form>
  );
}
