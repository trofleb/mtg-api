"use client";

import * as SliderPrimitive from "@radix-ui/react-slider";
import * as React from "react";

import { cn } from "@/lib/utils";

// One <Thumb> per value, as current shadcn/ui does.
//
// Issue #37: this component used to hard-code a single <Thumb>. Radix takes
// the number of handles from what it is given to render, not from the length
// of `value`, so `search-form.tsx`'s two-value CMC range rendered only the
// minimum handle. The maximum was then unreachable by every input method at
// once - there was no handle to grab or focus, and a drag of the one handle
// that existed moved the minimum instead.

/**
 * A two-value slider is a range, so its handles have names. Anything else is
 * left unlabelled for the caller to name, since only the caller knows what a
 * third handle would mean.
 */
const RANGE_THUMB_LABELS = ["Minimum", "Maximum"];

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(({ className, value, defaultValue, min = 0, max = 100, ...props }, ref) => {
  // Mirrors Radix's own resolution order, including its `[min]` fallback for a
  // slider given neither prop, so the rendered handles always match the
  // handles Radix is tracking internally.
  const thumbValues = React.useMemo<number[]>(
    () => value ?? defaultValue ?? [min],
    [value, defaultValue, min]
  );
  const isRange = thumbValues.length === RANGE_THUMB_LABELS.length;

  return (
    <SliderPrimitive.Root
      ref={ref}
      className={cn("relative flex w-full touch-none select-none items-center", className)}
      value={value}
      defaultValue={defaultValue}
      min={min}
      max={max}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-primary/20">
        <SliderPrimitive.Range className="absolute h-full bg-primary" />
      </SliderPrimitive.Track>
      {thumbValues.map((_, index) => (
        <SliderPrimitive.Thumb
          // biome-ignore lint/suspicious/noArrayIndexKey: Radix identifies thumbs positionally through its own collection, so a handle's index in the value array is its only stable identity.
          key={index}
          aria-label={isRange ? RANGE_THUMB_LABELS[index] : undefined}
          className="block h-4 w-4 rounded-full border border-primary/50 bg-background shadow transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
        />
      ))}
    </SliderPrimitive.Root>
  );
});
Slider.displayName = SliderPrimitive.Root.displayName;

export { Slider };
