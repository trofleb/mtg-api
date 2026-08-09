import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BackToSearch } from "@/components/back-to-search";
import { CardDetails } from "@/components/card-details";
import { getCardByOracleId } from "@/lib/api";

// Standalone, server-rendered card page. This is what a direct visit, a
// refresh, or a shared link resolves to - the modal in @modal is only an
// interception of this route when navigating from the grid.

export const revalidate = 3600;

// Enables the full route cache for on-demand params.
export async function generateStaticParams() {
  return [];
}

// How long a "no such card" answer may be kept (#30).
//
// A card id that 404s today is one the next ingest run can make real, so the
// answer has to be cheap to be wrong about. An hour was not: the first request
// for an unknown id wrote a 404 into the ISR cache and every request after it
// - including through any shared cache, given the s-maxage - was served that
// same 404 until the hour was up.
const NOT_FOUND_REVALIDATE_SECONDS = 60;

/**
 * Lower *this render's* cache lifetime to the not-found one.
 *
 * The shape here is forced, so it is worth writing down why rather than
 * leaving it to look arbitrary.
 *
 * `export const revalidate` is a static, segment-level module export: one
 * value for every branch of the page. The only runtime input to it is
 * `next.revalidate` on a fetch, and Next takes the *minimum* of the two - a
 * fetch can lower the segment's value but never raise it. So the segment has
 * to carry the maximum (the hour a real card gets) and the branch that wants
 * less has to ask for less. That is what this does.
 *
 * The fetch has to be a real fetch for Next's instrumentation to see it, but
 * it does not have to go anywhere: a `data:` URL is resolved in-process, costs
 * no I/O and cannot fail. It is doing nothing but carrying the number.
 *
 * The obvious alternative - `connection()`, to opt the miss out of caching
 * altogether - is not available here, and that was measured rather than
 * assumed: `generateStaticParams` above puts on-demand renders in prerender
 * mode, where any dynamic API is a hard `DYNAMIC_SERVER_USAGE` 500. Every
 * unknown card id returned HTTP 500 with it.
 *
 * If a future Next stops routing `data:` through its fetch patch this quietly
 * reverts to the hour, which is exactly the kind of silent regression this
 * repo has been bitten by - so `e2e/stubbed/error-pages.spec.ts` asserts the
 * resulting `s-maxage` rather than trusting the mechanism.
 */
async function declareNotFoundCacheLifetime(): Promise<void> {
  await fetch("data:text/plain,card-not-found", {
    next: { revalidate: NOT_FOUND_REVALIDATE_SECONDS },
  });
}

interface CardPageProps {
  params: Promise<{ id: string }>;
}

// Every link-unfurling client - Slack, Discord, WhatsApp, iMessage, X - reads
// og: and twitter: tags and nothing else, so a shared card used to arrive as a
// bare line of text next to a blank box (#41). The card art is the single most
// useful thing a preview could show, and the API already hands it over.
//
// The same fetch as the page body below: getCardByOracleId is a tagged, cached
// fetch, so metadata and content share one upstream request.
export async function generateMetadata({ params }: CardPageProps): Promise<Metadata> {
  const { id } = await params;
  const card = await getCardByOracleId(id);

  // No image on a 404: unfurling with somebody else's artwork would be worse
  // than unfurling with none.
  if (!card) return { title: "Card not found" };

  const title = `${card.name} - MTG Card Search`;
  const description = card.card_text || card.type_line || `${card.name} on MTG Card Search`;
  // faces_thumbnails is the double-faced case, where there is no single front
  // image - preview the front face.
  const image = card.thumbnail || card.faces_thumbnails?.[0];

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      siteName: "MTG Card Search",
      images: image ? [{ url: image, alt: card.name }] : undefined,
    },
    twitter: {
      // A card is a 5:7 portrait; the large-image style is the only one that
      // shows enough of it to be worth having.
      card: image ? "summary_large_image" : "summary",
      title,
      description,
      images: image ? [image] : undefined,
    },
  };
}

export default async function CardPage({ params }: CardPageProps) {
  const { id } = await params;
  const card = await getCardByOracleId(id);

  if (!card) {
    // Only on the miss: doing this unconditionally would drop the whole
    // route to a minute and throw away PR #17's caching win - which
    // error-pages.spec.ts guards with a control assertion, and which #34's
    // spec reads as its "does this server prerender at all" tripwire.
    await declareNotFoundCacheLifetime();
    notFound();
  }

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-3xl font-bold">{card.name}</h1>
          <BackToSearch />
        </div>
        <CardDetails card={card} />
      </div>
    </main>
  );
}
