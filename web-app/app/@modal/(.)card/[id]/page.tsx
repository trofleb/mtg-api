import { notFound } from "next/navigation";
import { CardDetails } from "@/components/card-details";
import { RouteModal } from "@/components/route-modal";
import { getCardByOracleId } from "@/lib/api";

// Intercepts /card/[id] when it is navigated to from within the app, so
// clicking a tile opens a modal over the results instead of a full page.
// The fetch and the markup are still server-side; only the dialog shell is
// client code. A refresh or a direct visit falls through to app/card/[id].

export const revalidate = 3600;

export async function generateStaticParams() {
  return [];
}

interface CardModalProps {
  params: Promise<{ id: string }>;
}

export default async function CardModal({ params }: CardModalProps) {
  const { id } = await params;
  const card = await getCardByOracleId(id);

  if (!card) notFound();

  return (
    <RouteModal title={card.name}>
      <CardDetails card={card} />
    </RouteModal>
  );
}
