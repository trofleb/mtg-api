import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CardDetails } from "@/components/card-details";
import { Button } from "@/components/ui/button";
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

export async function generateMetadata({ params }: CardPageProps): Promise<Metadata> {
  const { id } = await params;
  const card = await getCardByOracleId(id);
  return { title: card ? `${card.name} - MTG Card Search` : "Card not found" };
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
          <Button variant="outline" asChild>
            <Link href="/">Back to search</Link>
          </Button>
        </div>
        <CardDetails card={card} />
      </div>
    </main>
  );
}
