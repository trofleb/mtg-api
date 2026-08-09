import Link from "next/link";
import { Button } from "@/components/ui/button";

// The "Back to search" control from the standalone card page, lifted into its
// own component. Behaviour is unchanged by this extraction: it still points at
// "/". Issue #39 is that "/" re-runs the hardcoded DEFAULT_QUERY, throwing away
// whatever the user actually searched for.
//
// Extracted rather than fixed in place because app/card/[id]/page.tsx is an
// async server component, and neither jsdom nor Browser Mode can render one -
// so the link's href was untestable while it lived there.

export function BackToSearch() {
  return (
    <Button variant="outline" asChild>
      <Link href="/">Back to search</Link>
    </Button>
  );
}
