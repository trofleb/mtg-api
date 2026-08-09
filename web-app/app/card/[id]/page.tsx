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

  if (!card) notFound();

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
