"""Fetch a single card, by name or by id.

Sibling of :mod:`api.helpers.cards_search`, which builds the paginated
search. Everything here picks its cards by identity rather than by
relevance, and shapes them with the projection and grouping in
:mod:`api.helpers.cards_mongo`.
"""

import re
from typing import Optional

from unidecode import unidecode

from api.helpers.cards_mongo import AGGREGATE_CARD, CARD_PROJECTION, oracle_id_match


def find_cards_by_name(
    collection, name: str, lang: str, set_code: Optional[str]
) -> list[dict]:
    """Find a card by name, aggregated across its printings.

    Args:
        collection: Cards collection to aggregate over.
        name: Card name as the caller typed it, accents and case included.
        lang: Language code printings must carry.
        set_code: Set to restrict to, or None for any.

    Returns:
        The matching aggregated cards, empty when the name matches nothing.
    """
    search_name = unidecode(name).lower()
    return list(
        collection.aggregate(
            [
                {
                    "$match": {
                        # Anchored prefix match on the name the caller asked
                        # for, not on a pattern built out of it: escaped, so
                        # "Bl.ck Lotus" finds nothing rather than Black Lotus,
                        # and "/cards/(" is a 404 rather than a 500.
                        "name_search": {
                            "$regex": f"^{re.escape(search_name)}",
                        },
                    }
                },
                {"$project": CARD_PROJECTION},
                {"$sort": {"released_at": -1}},
                {
                    "$match": {
                        "lang": {"$eq": lang},
                        "layout": {
                            "$nin": ["art_series"],
                        },
                        "set": (
                            {"$eq": set_code.lower()} if set_code else {"$exists": True}
                        ),
                    }
                },
                {"$group": AGGREGATE_CARD},
            ]
        )
    )


def find_printing_by_scryfall_id(collection, scryfall_id: str) -> Optional[dict]:
    """Find one specific printing.

    Args:
        collection: Cards collection to query.
        scryfall_id: Unique Scryfall UUID for a specific card printing.

    Returns:
        The printing, or None when no card carries that id.
    """
    return collection.find_one({"id": scryfall_id}, CARD_PROJECTION)


def find_printings_by_oracle_id(collection, oracle_id: str) -> list[dict]:
    """Find every printing sharing an oracle id, newest first.

    A reversible card carries its oracle ids on the faces rather than the
    document, so the lookup has to check both places - see
    :func:`api.helpers.cards_mongo.oracle_id_match`.

    Args:
        collection: Cards collection to query.
        oracle_id: Oracle UUID, top-level or belonging to one of the faces.

    Returns:
        The printings, empty when the id matches nothing.
    """
    return list(
        collection.find(oracle_id_match(oracle_id), CARD_PROJECTION).sort(
            "released_at", -1
        )
    )


def find_aggregated_cards_by_oracle_id(collection, oracle_id: str) -> list[dict]:
    """Find a card by oracle id, aggregated across its printings.

    The same grouped shape a search result has, so a card can be rendered
    from an oracle id alone.

    Args:
        collection: Cards collection to aggregate over.
        oracle_id: Oracle UUID, top-level or belonging to one of the faces.

    Returns:
        The matching aggregated cards, empty when the id matches nothing.
    """
    return list(
        collection.aggregate(
            [
                {"$match": oracle_id_match(oracle_id)},
                {"$project": CARD_PROJECTION},
                {"$sort": {"released_at": -1}},
                {"$group": AGGREGATE_CARD},
            ]
        )
    )
