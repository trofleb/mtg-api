"""MongoDB projection and grouping shapes for the card endpoints."""

# Scryfall omits the top-level ``oracle_id`` on a ``reversible_card`` layout,
# because its two faces are separate Oracle cards printed back-to-back and
# each face carries its own. Reading the raw field therefore yields null for
# every such card, and since AGGREGATE_CARD groups on it they all collapse
# into a single null-keyed bucket - issue #22.
#
# Resolving to the first face's oracle id gives every layout a key that
# exists, and keeps the promise the field name makes: the Oracle card this
# printing is a printing of. Printings of one card still share it, so they
# still group together.
ORACLE_ID = {
    "$ifNull": [
        "$oracle_id",
        {"$arrayElemAt": [{"$ifNull": ["$card_faces.oracle_id", []]}, 0]},
    ]
}


def oracle_id_match(oracle_id: str) -> dict:
    """Build a ``$match`` that finds a card by oracle id, whatever its layout.

    The counterpart to :data:`ORACLE_ID`: an id resolved from a card's faces
    has to be looked up there too, or the aggregated endpoint 404s on exactly
    the cards search has just started returning ids for.

    Args:
        oracle_id: Oracle UUID, top-level or belonging to one of the faces.

    Returns:
        Query dictionary matching either location.
    """
    return {
        "$or": [
            {"oracle_id": oracle_id},
            {"card_faces.oracle_id": oracle_id},
        ]
    }


CARD_PROJECTION = {
    "_id": 0,
    "id": 1,
    "name": 1,
    "printed_name": 1,
    "oracle_id": ORACLE_ID,
    "lang": 1,
    "oracle_text": 1,
    "set_name": 1,
    "type_line": 1,
    "mana_cost": 1,
    "cmc": 1,
    "colors": 1,
    "color_identity": 1,
    # "frame": 1,
    # "reserved": 1,
    # "full_art": 1,
    # "textless": 1,
    "artist": 1,
    # "booster": 1,
    # "attraction_lights": 1,
    "layout": 1,
    # "story_spotlight": 1,
    # "artist_ids": 1,
    # "border_color": 1,
    # "card_back_id": 1,
    # "collector_number": 1,
    # "content_warning": 1,
    # "digital": 1,
    # "finishes": 1,
    "flavor_name": 1,
    "flavor_text": 1,
    # "frame_effects": 1,
    "games": 1,
    # "highres_image": 1,
    # "illustration_id": 1,
    # "image_status": 1,
    "image_uris": 1,
    # "oversized": 1,
    # "prices": 1,
    # "printed_name": 1,
    # "printed_text": 1,
    # "printed_type_line": 1,
    "promo": 1,
    # "promo_types": 1,
    # "purchase_uris": 1,
    "rarity": 1,
    "related_uris": 1,
    "released_at": 1,
    "reprint": 1,
    # "scryfall_set_uri": 1,
    # "set_search_uri": 1,
    # "set_type": 1,
    # "set_uri": 1,
    "set": 1,
    # "set_id": 1,
    # "textless": 1,
    "variation": 1,
    "variation_of": 1,
    "security_stamp": 1,
    "watermark": 1,
    # "preview_previewed_at": 1,
    # "preview_source_uri": 1,
    # "preview_source": 1,
    "thumbnail": "$image_uris.normal",
    "faces_thumbnails": "$card_faces.image_uris.normal",
    "image": "$image_uris.large",
    "imageXL": "$image_uris.png",
}

# Grouped on the projected oracle_id, which CARD_PROJECTION has already
# resolved through ORACLE_ID - so the key is present for every layout.
AGGREGATE_CARD = {
    "_id": "$oracle_id",
    "name": {"$first": "$name"},
    "card_text": {"$first": "$oracle_text"},
    "type_line": {"$first": "$type_line"},
    "mana_cost": {"$first": "$mana_cost"},
    "cmc": {"$first": "$cmc"},
    "colors": {"$first": "$colors"},
    "rarity": {"$first": "$rarity"},
    "card_count": {"$sum": 1},
    "cards": {"$addToSet": "$$ROOT"},
    "edhrec_rank": {"$max": "$edhrec_rank"},
    "penny_rank": {"$max": "$penny_rank"},
    "thumbnail": {"$first": "$thumbnail"},
    "faces_thumbnails": {"$first": "$faces_thumbnails"},
}
