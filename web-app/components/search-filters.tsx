"use client";

import { SetPicker } from "@/components/set-picker";
import { ToggleRow, toggle } from "@/components/toggle-row";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import type { CardFilter } from "@/lib/api";
import { CMC_MAX, CMC_MIN } from "@/lib/search-params";

// The filter panel, split out of search-form.tsx so neither file has to carry
// both the form plumbing and five kinds of control. It owns no state: every
// change is handed back up, because the form is what turns state into a URL.

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

const COLORS = [
  { value: "W", name: "White", emoji: "⚪" },
  { value: "U", name: "Blue", emoji: "🔵" },
  { value: "B", name: "Black", emoji: "⚫" },
  { value: "R", name: "Red", emoji: "🔴" },
  { value: "G", name: "Green", emoji: "🟢" },
];

// The emoji is decoration on top of the letter code, and read aloud it comes
// out as "large red circle R". Naming the button "Red" instead is both
// shorter and the thing the user actually chose (#40).
const COLOR_OPTIONS = COLORS.map(({ value, name, emoji }) => ({
  value,
  name,
  content: (
    <>
      <span aria-hidden="true">{emoji}</span> {value}
    </>
  ),
}));

interface SearchFiltersProps {
  sets: string[];
  filters: CardFilter;
  cmcRange: [number, number];
  isPending: boolean;
  onChange: (patch: Partial<CardFilter>) => void;
  onCmcChange: (range: [number, number]) => void;
  onClear: () => void;
}

export function SearchFilters({
  sets,
  filters,
  cmcRange,
  isPending,
  onChange,
  onCmcChange,
  onClear,
}: SearchFiltersProps) {
  const selectedColors = filters.colors ?? [];

  return (
    <Card>
      <CardContent className="pt-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <SetPicker
              sets={sets}
              selected={filters.sets ?? []}
              onChange={(next) => onChange({ sets: next })}
            />

            <div>
              <ToggleRow
                label="Colors"
                options={COLOR_OPTIONS}
                selected={selectedColors}
                onToggle={(value) => onChange({ colors: toggle(selectedColors, value) })}
              />
              {selectedColors.length > 0 && (
                <Select
                  value={filters.color_operator ?? "or"}
                  onValueChange={(value) =>
                    onChange({ color_operator: value as CardFilter["color_operator"] })
                  }
                >
                  <SelectTrigger type="button" className="mt-2" aria-label="How to match colors">
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
                onValueChange={(value) => onCmcChange(value as [number, number])}
              />
            </div>

            <ToggleRow
              label="Card Types"
              options={CARD_TYPES.map((value) => ({ value, content: value }))}
              selected={filters.types ?? []}
              onToggle={(value) => onChange({ types: toggle(filters.types ?? [], value) })}
            />

            <ToggleRow
              label="Rarity"
              options={RARITIES.map((value) => ({
                value,
                content: value,
                className: "capitalize",
              }))}
              selected={filters.rarities ?? []}
              onToggle={(value) => onChange({ rarities: toggle(filters.rarities ?? [], value) })}
            />
          </div>
        </div>

        <div className="flex gap-2 pt-4 border-t">
          <Button type="submit" disabled={isPending}>
            Apply Filters
          </Button>
          {/* Clear All navigates rather than only emptying the controls - see
              the note on clearFilters in search-form.tsx (#33). */}
          <Button type="button" variant="outline" onClick={onClear}>
            Clear All
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
