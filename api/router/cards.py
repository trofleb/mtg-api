import logging
from typing import Annotated, Optional

from fastapi import HTTPException, Query
from fastapi.routing import APIRouter
from unidecode import unidecode

from api.helpers.cards_mongo import AGGREGATE_CARD, CARD_PROJECTION
from api.helpers.database import CardsCollection
from api.models.cards import CardPrinting, OracleCard, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _expose_id(card: dict) -> dict:
    """Rename an aggregated card's "_id" to "id".

    Grouping by oracle_id forces the key onto "_id", which is a MongoDB
    detail rather than part of this API. The OracleCard response model
    declares "id" and requires it, so this is now how the pipeline meets
    that contract rather than being the contract itself.
    """
    if "_id" in card:
        card["id"] = card.pop("_id")
    return card


@router.get("/cards/{name}", response_model=OracleCard)
def search_card_by_name(
    name: str,
    collection: CardsCollection,
    lang: str = "en",
    set: Optional[str] = None,
):
    search_name = unidecode(name).lower()
    results = [
        card
        for card in collection.aggregate(
            [
                {
                    "$match": {
                        "name_search": {
                            "$regex": f"^{search_name}",
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
                        "set": ({"$eq": set.lower()} if set else {"$exists": True}),
                    }
                },
                {"$group": AGGREGATE_CARD},
            ]
        )
    ]

    if len(results) == 0:
        raise HTTPException(status_code=404, detail=f"Card {name} not found")

    return _expose_id(results[0])


@router.get("/cards/search/{text}", response_model=SearchResponse)
def search_card_by_text(
    text: str,
    collection: CardsCollection,
    lang: str = "en",
    cursor: Optional[str] = None,
    page_count: int = 10,
    sets: Annotated[list[str], Query()] = [],
    colors: Annotated[list[str], Query()] = [],
    color_operator: Annotated[str, Query()] = "or",
    cmc_min: Annotated[Optional[int], Query()] = None,
    cmc_max: Annotated[Optional[int], Query()] = None,
    types: Annotated[list[str], Query()] = [],
    rarities: Annotated[list[str], Query()] = [],
):
    # Build match conditions
    match_conditions = {
        "$text": {
            "$search": text,
            "$caseSensitive": False,
            "$diacriticSensitive": False,
        },
        "lang": {"$eq": lang},
    }

    # Add set filter
    if sets:
        match_conditions["set_name"] = {"$in": sets}

    # Add color filter
    if colors:
        if color_operator == "exactly":
            # Exactly these colors (no more, no less)
            match_conditions["colors"] = {
                "$all": colors,
                "$size": len(colors),
            }
        elif color_operator == "and":
            # Contains all these colors (may have more)
            match_conditions["colors"] = {"$all": colors}
        else:  # "or" - default
            # Contains any of these colors
            match_conditions["colors"] = {"$in": colors}

    # Add CMC filter
    if cmc_min is not None or cmc_max is not None:
        cmc_filter = {}
        if cmc_min is not None:
            cmc_filter["$gte"] = cmc_min
        if cmc_max is not None:
            cmc_filter["$lte"] = cmc_max
        match_conditions["cmc"] = cmc_filter

    # Add type filter (checks if type_line contains any of the specified types)
    if types:
        # Case-insensitive regex for type matching
        type_patterns = [{"type_line": {"$regex": t, "$options": "i"}} for t in types]
        match_conditions["$or"] = type_patterns

    # Add rarity filter
    if rarities:
        match_conditions["rarity"] = {"$in": rarities}

    # Build aggregation pipeline
    pipeline = [
        {"$match": match_conditions},
        # "score": 1 would project each document's own "score" field, which
        # card documents do not have. Only {"$meta": "textScore"} asks for the
        # $text relevance score, without which every document ties at null and
        # the $sort below degenerates to _id ascending.
        {"$project": {"score": {"$meta": "textScore"}, **CARD_PROJECTION}},
        {"$group": {"score": {"$max": "$score"}, **AGGREGATE_CARD}},
        {
            "$sort": {"score": -1, "_id": 1}
        },  # Sort by score DESC, then _id ASC for consistency
    ]

    # Add cursor filter if provided
    if cursor:
        # Cursor format: "score:oracle_id"
        try:
            cursor_score, cursor_id = cursor.split(":", 1)
            cursor_score = float(cursor_score)
            # Match documents with score < cursor_score OR (score == cursor_score AND _id > cursor_id)
            pipeline.append(
                {
                    "$match": {
                        "$or": [
                            {"score": {"$lt": cursor_score}},
                            {
                                "$and": [
                                    {"score": cursor_score},
                                    {"_id": {"$gt": cursor_id}},
                                ]
                            },
                        ]
                    }
                }
            )
        except (ValueError, IndexError):
            # An unusable cursor is served as if it were the first page. That
            # is a pagination loop from the client's side, so say so rather
            # than returning 200 with nothing in the logs.
            logger.warning(
                'Ignoring malformed pagination cursor %r for search "%s"; '
                'expected "<score>:<oracle_id>". Serving the first page.',
                cursor,
                text,
            )

    # Add limit
    pipeline.append({"$limit": page_count + 1})

    # Execute aggregation
    results = list(collection.aggregate(pipeline))

    # Build pagination result
    # One extra document was fetched purely to detect a further page.
    page = [_expose_id(card) for card in results[:page_count]]
    has_more = len(results) > page_count

    # The cursor points at the last card of this page. Its "id" is the
    # grouping key, which the pipeline's cursor filter matches as "_id".
    result = {
        "cards": page,
        "cursor": (
            f"{page[-1]['score']}:{page[-1]['id']}" if has_more and page else None
        ),
        "has_more": has_more,
    }

    return result


@router.get("/cards/id/{scryfall_id}", response_model=CardPrinting)
def get_card_by_scryfall_id(scryfall_id: str, collection: CardsCollection):
    """Get a specific MTG card printing by Scryfall ID.

    Args:
        scryfall_id: Unique Scryfall UUID for a specific card printing
        collection: MongoDB cards collection (injected dependency)

    Returns:
        Card data including image_uris and all metadata

    Raises:
        HTTPException: 404 if card not found
    """

    # Query MongoDB for card by Scryfall ID
    card = collection.find_one({"id": scryfall_id}, CARD_PROJECTION)

    if card is None:
        raise HTTPException(
            status_code=404, detail=f"Card with ID {scryfall_id} not found"
        )

    return card


@router.get("/cards/oracle/{oracle_id}", response_model=list[CardPrinting])
def get_cards_by_oracle_id(oracle_id: str, collection: CardsCollection):
    """Get all printings of a card by Oracle ID.

    Args:
        oracle_id: Oracle UUID representing the card concept (non-unique)
        collection: MongoDB cards collection (injected dependency)

    Returns:
        List of all card printings sharing this oracle_id

    Raises:
        HTTPException: 404 if no cards found with this oracle_id
    """

    # Query MongoDB for all cards with this Oracle ID
    cards = list(
        collection.find({"oracle_id": oracle_id}, CARD_PROJECTION).sort(
            "released_at", -1
        )
    )

    if not cards:
        raise HTTPException(
            status_code=404, detail=f"No cards found with Oracle ID {oracle_id}"
        )

    return cards


@router.get("/cards/oracle/{oracle_id}/aggregated", response_model=OracleCard)
def get_aggregated_card_by_oracle_id(oracle_id: str, collection: CardsCollection):
    """Get a single card aggregated across all its printings, by Oracle ID.

    /cards/oracle/{oracle_id} returns the raw printings. This returns the same
    grouped shape that /cards/search/{text} produces for each result, so a
    card can be rendered on its own from an Oracle ID alone rather than only
    from a search result.

    Args:
        oracle_id: Oracle UUID representing the card concept
        collection: MongoDB cards collection (injected dependency)

    Returns:
        Aggregated card data, including every printing under "cards"

    Raises:
        HTTPException: 404 if no cards found with this oracle_id
    """

    results = [
        card
        for card in collection.aggregate(
            [
                {"$match": {"oracle_id": oracle_id}},
                {"$project": CARD_PROJECTION},
                {"$sort": {"released_at": -1}},
                {"$group": AGGREGATE_CARD},
            ]
        )
    ]

    if not results:
        raise HTTPException(
            status_code=404, detail=f"No cards found with Oracle ID {oracle_id}"
        )

    return _expose_id(results[0])
