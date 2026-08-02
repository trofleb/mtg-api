import { CardTile } from "@/components/card-tile";
import type { OracleCard } from "@/lib/api";

// Server component: the whole grid is HTML by the time it reaches the
// browser. No "use client", no click handlers, no state.

interface CardGridProps {
  cards: OracleCard[];
}

export function CardGrid({ cards }: CardGridProps) {
  if (cards.length === 0) {
    return <p className="text-muted-foreground py-12 text-center">No cards found.</p>;
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {cards.map((card) => (
        <CardTile key={card.id} card={card} />
      ))}
    </div>
  );
}
