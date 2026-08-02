import Image from "next/image";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import type { OracleCard } from "@/lib/api";

// Server component: this markup is rendered on the server and arrives as
// HTML. There is no click handler and no state - navigation is a plain
// <Link>, so a card is readable and crawlable without any JavaScript.

const RARITY_EMOJI = {
  common: "⚪",
  uncommon: "🔵",
  rare: "🟡",
  mythic: "🔴",
} as const;

interface CardTileProps {
  card: OracleCard;
}

export function CardTile({ card }: CardTileProps) {
  const thumbnail = card.thumbnail || card.faces_thumbnails?.[0];
  const rarityEmoji = card.rarity ? RARITY_EMOJI[card.rarity as keyof typeof RARITY_EMOJI] : "⚪";

  return (
    <Link href={`/card/${card.id}`} scroll={false} data-testid="card-item">
      <Card className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer group h-full">
        <CardContent className="p-0">
          <div className="relative aspect-[5/7] bg-muted">
            {thumbnail ? (
              <Image
                src={thumbnail}
                alt={card.name || "Magic card"}
                fill
                className="object-cover group-hover:scale-105 transition-transform"
                sizes="(max-width: 768px) 50vw, (max-width: 1024px) 33vw, (max-width: 1280px) 25vw, 20vw"
              />
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                No image available
              </div>
            )}
          </div>

          <div className="p-3 space-y-2">
            <h3 className="font-semibold text-sm line-clamp-2 min-h-[2.5rem]">{card.name}</h3>

            <div className="flex items-center justify-between text-xs">
              {card.mana_cost && (
                <span className="text-muted-foreground truncate flex-1">{card.mana_cost}</span>
              )}
              {card.rarity && (
                <span className="ml-2" title={card.rarity}>
                  {rarityEmoji}
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
