import Link from "next/link";
import { Button } from "@/components/ui/button";

/**
 * The 404 boundary for the whole app (#29).
 *
 * Until this file existed there was no not-found boundary anywhere in `app/`,
 * so every `notFound()` and every unmatched URL fell through to Next's
 * built-in page: "404 | This page could not be found", with no links in it at
 * all. A visitor who followed a stale shared card link had nothing to click.
 *
 * Placed at the root rather than in `app/card/[id]/` on purpose. The card page
 * is the only `notFound()` call site today, but a root boundary also serves
 * every URL that matches no route - and that case is the one where this file
 * genuinely fixes the no-JavaScript experience, because Next serves it from
 * the prerendered `/_not-found` route as an ordinary successful render, so
 * this markup is in the HTML.
 *
 * It does *not* fix the no-JS case for `notFound()` thrown from a page. That
 * is a Next 16.0.3 behaviour with no lever in `app/`, measured and written up
 * in `e2e/stubbed/error-pages.spec.ts`, where the assertion is kept red.
 *
 * That spec also asserts exactly one `a[href="/"]` here, so keep it to a
 * single way home.
 */

export default function NotFound() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-xl mx-auto space-y-4 text-center pt-24">
        <p className="text-sm font-mono text-muted-foreground">404</p>
        <h1 className="text-3xl font-bold">We couldn&apos;t find that card</h1>
        <p className="text-muted-foreground">
          The link may be out of date, or the card may not be in the database yet. Searching for it
          by name is the quickest way to check.
        </p>
        <div className="pt-2">
          <Button asChild>
            <Link href="/">Back to search</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
