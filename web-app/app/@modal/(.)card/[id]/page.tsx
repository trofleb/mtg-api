import { notFound } from "next/navigation";
import { CardDetails } from "@/components/card-details";
import { RouteModal } from "@/components/route-modal";
import { getCardByOracleId } from "@/lib/api";

// Intercepts /card/[id] when it is navigated to from within the app, so
// clicking a tile opens a modal over the results instead of a full page.
// The fetch and the markup are still server-side; only the dialog shell is
// client code. A refresh or a direct visit falls through to app/card/[id].
//
// Deliberately NOT prerendered - no `revalidate`, no `generateStaticParams`
// (#34). An intercepting route's response depends on the client's router state
// tree: the payload has to carry the page underneath the modal, which the
// server only knows from the Next-Url header the router sends. Prerender it
// and that header is ignored, `children` collapses to __DEFAULT__, and every
// card click 404s. The hour-long revalidate belongs on app/card/[id], where
// the response is self-contained. Nothing is lost here: the upstream fetch in
// getCardByOracleId is cached either way.

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
