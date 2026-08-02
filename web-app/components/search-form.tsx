"use client";

import { ChevronDown, Search, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import type { CardFilter } from "@/lib/api";
import { buildSearchParams, CMC_MAX, CMC_MIN, type SearchState } from "@/lib/search-params";

// The only client component in the search path. It holds no results - it
// edits the URL, and the server re-renders the page from it. Submitting
// always drops the cursor, since a cursor only means anything for the exact
// query and filters it was issued against.

const CARD_TYPES = [
  "Creature",
  "Instant",
  "Sorcery",
  "Enchantment",
  "Artifact",
  "Planeswalker",
  "Land",
  "Battle",
];

const RARITIES = ["common", "uncommon", "rare", "mythic"];

const COLOR_MAP = {
  W: { name: "White", emoji: "⚪" },
  U: { name: "Blue", emoji: "🔵" },
  B: { name: "Black", emoji: "⚫" },
  R: { name: "Red", emoji: "🔴" },
  G: { name: "Green", emoji: "🟢" },
} as const;

interface SearchFormProps {
  /** Available set names, fetched on the server. */
  sets: string[];
  /** Current state, parsed from the URL on the server. */
  state: SearchState;
}

function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function SearchForm({ sets, state }: SearchFormProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [showFilters, setShowFilters] = useState(false);

  const [query, setQuery] = useState(state.query);
  const [filters, setFilters] = useState<CardFilter>(state.filters);
  const [cmcRange, setCmcRange] = useState<[number, number]>([
    state.filters.cmc_min ?? CMC_MIN,
    state.filters.cmc_max ?? CMC_MAX,
  ]);

  const update = (patch: Partial<CardFilter>) => setFilters((prev) => ({ ...prev, ...patch }));

  const submit = () => {
    if (!query.trim()) return;
    const qs = buildSearchParams({
      query: query.trim(),
      cursor: null,
      filters: {
        ...filters,
        cmc_min: cmcRange[0] > CMC_MIN ? cmcRange[0] : undefined,
        cmc_max: cmcRange[1] < CMC_MAX ? cmcRange[1] : undefined,
        color_operator: (filters.colors ?? []).length > 0 ? filters.color_operator : undefined,
      },
    });
    startTransition(() => router.push(`/?${qs}`));
  };

  const clearFilters = () => {
    setFilters({});
    setCmcRange([CMC_MIN, CMC_MAX]);
  };

  const selectedSets = filters.sets ?? [];
  const selectedColors = filters.colors ?? [];
  const selectedTypes = filters.types ?? [];
  const selectedRarities = filters.rarities ?? [];

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        <Input
          type="text"
          placeholder="Search for cards by name, text, or ability..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
          className="flex-1"
        />
        <Button onClick={submit} disabled={isPending || !query.trim()}>
          <Search className="h-4 w-4" />
          <span className="ml-2">Search</span>
        </Button>
        <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
          Filters
          <ChevronDown
            className={`ml-2 h-4 w-4 transition-transform ${showFilters ? "rotate-180" : ""}`}
          />
        </Button>
      </div>

      {showFilters && (
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <span className="text-sm font-medium mb-2 block">Sets</span>
                  <Select
                    value=""
                    onValueChange={(value) => {
                      if (value && !selectedSets.includes(value)) {
                        update({ sets: [...selectedSets, value] });
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select sets..." />
                    </SelectTrigger>
                    <SelectContent>
                      {sets.map((set) => (
                        <SelectItem key={set} value={set}>
                          {set}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {selectedSets.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {selectedSets.map((set) => (
                        <Badge key={set} variant="secondary">
                          {set}
                          <button
                            type="button"
                            onClick={() => update({ sets: selectedSets.filter((s) => s !== set) })}
                            className="ml-1 hover:text-destructive"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <span className="text-sm font-medium mb-2 block">Colors</span>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(COLOR_MAP).map(([code, { name, emoji }]) => (
                      <Button
                        key={code}
                        type="button"
                        size="sm"
                        variant={selectedColors.includes(code) ? "default" : "outline"}
                        onClick={() => update({ colors: toggle(selectedColors, code) })}
                        title={name}
                      >
                        {emoji} {code}
                      </Button>
                    ))}
                  </div>
                  {selectedColors.length > 0 && (
                    <Select
                      value={filters.color_operator ?? "or"}
                      onValueChange={(value) =>
                        update({ color_operator: value as CardFilter["color_operator"] })
                      }
                    >
                      <SelectTrigger className="mt-2">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="or">Any of these colors</SelectItem>
                        <SelectItem value="and">All of these colors</SelectItem>
                        <SelectItem value="exactly">Exactly these colors</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <span className="text-sm font-medium mb-2 block">
                    Mana Cost (CMC): {cmcRange[0]} - {cmcRange[1] === CMC_MAX ? "16+" : cmcRange[1]}
                  </span>
                  <Slider
                    min={CMC_MIN}
                    max={CMC_MAX}
                    step={1}
                    value={cmcRange}
                    onValueChange={(value) => setCmcRange(value as [number, number])}
                  />
                </div>

                <div>
                  <span className="text-sm font-medium mb-2 block">Card Types</span>
                  <div className="flex flex-wrap gap-2">
                    {CARD_TYPES.map((type) => (
                      <Button
                        key={type}
                        type="button"
                        size="sm"
                        variant={selectedTypes.includes(type) ? "default" : "outline"}
                        onClick={() => update({ types: toggle(selectedTypes, type) })}
                      >
                        {type}
                      </Button>
                    ))}
                  </div>
                </div>

                <div>
                  <span className="text-sm font-medium mb-2 block">Rarity</span>
                  <div className="flex flex-wrap gap-2">
                    {RARITIES.map((rarity) => (
                      <Button
                        key={rarity}
                        type="button"
                        size="sm"
                        variant={selectedRarities.includes(rarity) ? "default" : "outline"}
                        onClick={() => update({ rarities: toggle(selectedRarities, rarity) })}
                        className="capitalize"
                      >
                        {rarity}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Filter Actions */}
            <div className="flex gap-2 pt-4 border-t">
              <Button onClick={submit} disabled={isPending}>
                Apply Filters
              </Button>
              <Button variant="outline" onClick={clearFilters}>
                Clear All
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
