"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";

/**
 * The error boundary for the whole app.
 *
 * Companion to `not-found.tsx`, and there for the same reason: with no
 * `error.tsx` anywhere in `app/`, an uncaught render error - a search that
 * throws because the API answered 500, say - fell through to Next's built-in
 * error page, which offers no way out and no way to retry.
 *
 * Like `notFound()`, a thrown error reaches the browser only in the flight
 * payload in Next 16 (probed on 16.0.3: a page that just throws serves an empty
 * `<html id="__next_error__">`), so this paints after hydration rather than in
 * the HTML. That is a limit of the framework's error path, not of this file.
 *
 * `"use client"` is not decoration: a React error boundary only exists on the
 * client, and Next fails the build without the directive.
 *
 * Deliberately *not* `global-error.tsx`. That one replaces the root layout and
 * only fires for errors thrown inside the layout itself; `app/layout.tsx` here
 * fetches nothing and renders no data, so the useful boundary is this one.
 */

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // The server strips the message out of the payload in production and
    // leaves only `digest`; logging here is what makes the client-side half
    // (a bad render after hydration) visible at all.
    console.error(error);
  }, [error]);

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-xl mx-auto space-y-4 text-center pt-24">
        <h1 className="text-3xl font-bold">Something went wrong</h1>
        <p className="text-muted-foreground">
          The search service did not answer. This is usually temporary.
        </p>
        {/* `error.message` is deliberately not shown: on a server error it can
            carry an internal hostname or a stack fragment, and in production
            Next replaces it with a placeholder anyway. The digest is the
            supported handle for matching this against the server log. */}
        {error.digest ? (
          <p className="text-xs font-mono text-muted-foreground">Reference: {error.digest}</p>
        ) : null}
        <div className="flex items-center justify-center gap-3 pt-2">
          {/* Re-renders the failed segment in place, so a transient failure
              costs a click rather than a full page load. */}
          <Button onClick={reset}>Try again</Button>
          <Button variant="outline" asChild>
            <Link href="/">Back to search</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
