import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

// The "x" that removes a selected filter (#40). Written here rather than
// inline at each call site so the hit area is decided once.
//
// h-6 w-6 is 24x24 CSS px, WCAG 2.2 SC 2.5.8 (Target Size, Minimum). The icon
// inside stays 12x12: this grows the *target*, not the drawing. -my-1 pulls the
// extra height back out of the flow so the badge itself does not get taller.
const badgeRemoveButtonClasses =
  "-my-1 ml-1 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-sm " +
  "transition-colors hover:text-destructive focus-visible:outline-none " +
  "focus-visible:ring-2 focus-visible:ring-ring";

function BadgeRemoveButton({ className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={cn(badgeRemoveButtonClasses, className)} {...props} />;
}

export { Badge, BadgeRemoveButton, badgeVariants };
