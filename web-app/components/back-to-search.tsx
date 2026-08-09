"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Button } from "@/components/ui/button";

// "Back to search" on the standalone card page (#39). It used to be a fixed
// <Link href="/">, so returning from a card threw away the query, every filter
// and the page the user had reached, and re-ran the hardcoded DEFAULT_QUERY.
// CardTile now threads the originating query into the card's own URL; this
// reads it back off that URL.
//
// A client component reading useSearchParams, rather than the page reading its
// own searchParams, and that is not a workaround - it is the only correct
// shape here. app/card/[id] carries `export const revalidate = 3600`, so its
// HTML is cached in the full route cache keyed by *pathname*. Rendering a
// query-specific href on the server would mean one visitor's search string
// being served from cache to the next visitor. Awaiting searchParams instead
// would opt the whole route out of static rendering, dropping the s-maxage
// that PR #17 added and that the #34 spec uses as its prerendering tripwire.
//
// So the query is resolved in the browser, behind Suspense: the cached HTML
// carries the fallback, hydration swaps in the real destination. Without
// JavaScript the link still points at "/", which is exactly today's behaviour
// - no worse, and better for everyone else.

const LABEL = "Back to search";

function BackLink({ href }: { href: string }) {
  return (
    <Button variant="outline" asChild>
      <Link href={href}>{LABEL}</Link>
    </Button>
  );
}

function BackLinkFromUrl() {
  const search = useSearchParams().toString();
  return <BackLink href={search ? `/?${search}` : "/"} />;
}

export function BackToSearch() {
  return (
    <Suspense fallback={<BackLink href="/" />}>
      <BackLinkFromUrl />
    </Suspense>
  );
}
