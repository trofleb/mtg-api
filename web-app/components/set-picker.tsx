"use client";

import { X } from "lucide-react";
import { Badge, BadgeRemoveButton } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * Pick sets from a dropdown; each pick becomes a removable badge.
 *
 * The dropdown is deliberately valueless - it is an "add one" control, not a
 * single-selection field, and the badges below are where the selection lives.
 */
export function SetPicker({
  sets,
  selected,
  onChange,
}: {
  sets: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  return (
    <div>
      <span className="text-sm font-medium mb-2 block">Sets</span>
      <Select
        value=""
        onValueChange={(value) => {
          if (value && !selected.includes(value)) onChange([...selected, value]);
        }}
      >
        <SelectTrigger type="button">
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
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {selected.map((set) => (
            <Badge key={set} variant="secondary">
              {set}
              {/* Lucide marks its icons aria-hidden, so with no name of its
                  own this button reads as bare "button" to a screen reader
                  and there is no way to tell the five of them apart (#40). */}
              {/* BadgeRemoveButton, not a bare <button>: the icon is 12px, far
                  under a usable tap target, so the primitive pads the hit area
                  out to 24px without growing the badge (#40). */}
              <BadgeRemoveButton
                aria-label={`Remove set ${set}`}
                onClick={() => onChange(selected.filter((s) => s !== set))}
              >
                <X className="h-3 w-3" />
              </BadgeRemoveButton>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
