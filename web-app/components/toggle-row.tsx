"use client";

import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";

export interface ToggleOption {
  value: string;
  content: ReactNode;
  /** Overrides the accessible name when the visible text is not one. */
  name?: string;
  className?: string;
}

/** Add a value to a list, or remove it if it is already there. */
export function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

/**
 * A labelled row of toggle buttons - colours, card types, rarities.
 *
 * `type="button"` is load-bearing rather than tidiness: these live inside a
 * real <form> now, where a button defaults to type="submit", and picking a
 * colour must not fire off a search. `aria-pressed` is what carries the
 * on/off state to anyone who cannot see the variant swap (#40).
 */
export function ToggleRow({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: ToggleOption[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  return (
    <div>
      <span className="text-sm font-medium mb-2 block">{label}</span>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const active = selected.includes(option.value);
          return (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={active ? "default" : "outline"}
              aria-pressed={active}
              aria-label={option.name}
              title={option.name}
              className={option.className}
              onClick={() => onToggle(option.value)}
            >
              {option.content}
            </Button>
          );
        })}
      </div>
    </div>
  );
}
