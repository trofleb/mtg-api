"use client";

import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";

// Client shell for an intercepted route: it owns only the open/close
// behaviour. The contents are server-rendered and passed in as children,
// so no card markup is built in the browser. Dismissing navigates back,
// which returns the user to the search results underneath.

interface RouteModalProps {
  title: string;
  children: ReactNode;
}

/** How long to keep waiting for the grid to come back before giving up. */
const FOCUS_RESTORE_TIMEOUT_MS = 2000;

/**
 * The tile that opened this modal, found by its href rather than by a stored
 * reference - the stored one is exactly what goes stale.
 *
 * Matched against every anchor instead of a CSS attribute selector so that
 * nothing in the path has to be escaped, and `?` so that the query CardTile
 * threads through for #39 still matches.
 */
function findTile(pathname: string): HTMLElement | null {
  for (const link of document.querySelectorAll<HTMLAnchorElement>("a[href]")) {
    const href = link.getAttribute("href") ?? "";
    if (href === pathname || href.startsWith(`${pathname}?`)) return link;
  }
  return null;
}

/**
 * Put focus back on the tile the user came from (#40).
 *
 * Radix already restores focus on close - to the element that was focused when
 * the dialog mounted. That is the right element and the wrong node: this modal
 * closes with router.back(), the results grid re-renders, and React hands out
 * fresh DOM. Calling focus() on the detached original is a silent no-op, so a
 * keyboard user is dropped on <body> and has to tab through the whole grid to
 * get back to where they were.
 *
 * The re-render is also asynchronous, so the tile may not exist yet at the
 * moment the dialog unmounts - hence the observer rather than a single lookup.
 */
function restoreFocusToTile(pathname: string) {
  const tile = findTile(pathname);
  if (tile) {
    tile.focus();
    return;
  }

  let timer = 0;
  const observer = new MutationObserver(() => {
    const restored = findTile(pathname);
    if (!restored) return;
    window.clearTimeout(timer);
    observer.disconnect();
    restored.focus();
  });

  observer.observe(document.body, { childList: true, subtree: true });
  // If the user navigated somewhere else entirely, the tile is never coming
  // back; stop watching rather than leaking an observer for the session.
  timer = window.setTimeout(() => observer.disconnect(), FOCUS_RESTORE_TIMEOUT_MS);
}

export function RouteModal({ title, children }: RouteModalProps) {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) router.back();
      }}
    >
      <DialogContent
        className="max-w-4xl max-h-[90vh]"
        // DialogContent otherwise points aria-describedby at an id Radix mints
        // for a DialogDescription. There is no DialogDescription here, so the
        // reference dangles: assistive tech is promised a description and finds
        // nothing. undefined is Radix's documented way to say "there isn't one".
        aria-describedby={undefined}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          restoreFocusToTile(pathname);
        }}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="max-h-[calc(90vh-8rem)]">{children}</ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
