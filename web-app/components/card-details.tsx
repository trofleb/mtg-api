import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { OracleCard } from "@/lib/api";

// Server component holding the detail markup itself, with no dialog shell
// around it. Both the standalone /card/[id] page and the intercepted modal
// render this, so the two can never drift apart.

interface CardDetailsProps {
  card: OracleCard;
}

export function CardDetails({ card }: CardDetailsProps) {
  const thumbnail = card.thumbnail || card.faces_thumbnails?.[0];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Left Column - Image(s) */}
      <div className="space-y-4">
        {thumbnail ? (
          <div className="relative aspect-[5/7] w-full">
            <Image
              src={thumbnail}
              alt={card.name || "Magic card"}
              fill
              className="object-contain rounded-lg"
              sizes="(max-width: 768px) 100vw, 50vw"
              priority
            />
          </div>
        ) : card.faces_thumbnails && card.faces_thumbnails.length > 0 ? (
          <div className="grid grid-cols-2 gap-2">
            {card.faces_thumbnails.map((img, i) => (
              <div key={img} className="relative aspect-[5/7]">
                <Image
                  src={img}
                  alt={`${card.name} face ${i + 1}`}
                  fill
                  className="object-contain rounded-lg"
                  sizes="50vw"
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center aspect-[5/7] bg-muted rounded-lg text-muted-foreground text-sm">
            No image available
          </div>
        )}
      </div>

      {/* Right Column - Details */}
      <div className="space-y-4">
        {card.type_line && (
          <div>
            <h3 className="font-semibold text-sm text-muted-foreground mb-1">Type</h3>
            <p>{card.type_line}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          {card.mana_cost && (
            <div>
              <h3 className="font-semibold text-sm text-muted-foreground mb-1">Mana Cost</h3>
              <p className="font-mono">{card.mana_cost}</p>
            </div>
          )}
          {card.cmc !== undefined && (
            <div>
              <h3 className="font-semibold text-sm text-muted-foreground mb-1">CMC</h3>
              <p>{card.cmc}</p>
            </div>
          )}
        </div>

        {card.colors && card.colors.length > 0 && (
          <div>
            <h3 className="font-semibold text-sm text-muted-foreground mb-1">Colors</h3>
            <div className="flex gap-1">
              {card.colors.map((color) => (
                <Badge key={color} variant="secondary">
                  {color}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {card.rarity && (
          <div>
            <h3 className="font-semibold text-sm text-muted-foreground mb-1">Rarity</h3>
            <Badge className="capitalize">{card.rarity}</Badge>
          </div>
        )}

        {card.card_text && (
          <div>
            <h3 className="font-semibold text-sm text-muted-foreground mb-1">Oracle Text</h3>
            <p className="whitespace-pre-wrap text-sm">{card.card_text}</p>
          </div>
        )}

        {card.card_count !== undefined && (
          <div>
            <h3 className="font-semibold text-sm text-muted-foreground mb-1">Printings</h3>
            <p>{card.card_count}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          {card.edhrec_rank !== undefined && (
            <div>
              <h3 className="font-semibold text-sm text-muted-foreground mb-1">EDHREC Rank</h3>
              <p>#{card.edhrec_rank}</p>
            </div>
          )}
          {card.penny_rank !== undefined && (
            <div>
              <h3 className="font-semibold text-sm text-muted-foreground mb-1">Penny Rank</h3>
              <p>#{card.penny_rank}</p>
            </div>
          )}
        </div>

        {card.cards && card.cards.length > 0 && (
          <div>
            <h3 className="font-semibold text-sm text-muted-foreground mb-2">
              All Printings ({card.cards.length})
            </h3>
            <ScrollArea className="h-48 rounded border p-4">
              <div className="space-y-3">
                {card.cards.map((printing, i) => (
                  <div
                    key={`${printing.id}-${i}`}
                    className="flex items-start gap-3 pb-3 border-b last:border-0"
                  >
                    {printing.image_uris?.small && (
                      <div className="relative w-16 h-22 flex-shrink-0">
                        <Image
                          src={printing.image_uris.small}
                          alt={printing.set_name ?? printing.name}
                          fill
                          className="object-contain rounded"
                          sizes="64px"
                        />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm">{printing.set_name}</p>
                      {printing.set && (
                        <p className="text-xs text-muted-foreground">
                          Set: {printing.set.toUpperCase()}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Released: {printing.released_at}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}
      </div>
    </div>
  );
}
