import logging
from typing import Annotated, Optional

from fastapi import HTTPException, Query
from fastapi.routing import APIRouter

from api.helpers.cards_cursor import CURSOR_FORMAT, cursor_match, decode_cursor
from api.helpers.cards_lookup import (
    find_aggregated_cards_by_oracle_id,
    find_cards_by_name,
    find_printing_by_scryfall_id,
    find_printings_by_oracle_id,
)
from api.helpers.cards_mongo import count_matching_oracle_cards
from api.helpers.cards_response import build_search_page, expose_id
from api.helpers.cards_search import build_search_match, build_search_pipeline
from api.helpers.database import CardsCollection
from api.models.cards import CardPrinting, OracleCard, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _resume_filter(cursor: Optional[str], q: str) -> Optional[dict]:
    """Turn a client's cursor into a resume condition, or say why it can't.

    An unusable cursor serves the first page, which is a pagination loop from
    the client's side - so it is worth a line in the logs rather than an HTTP
    200 and silence (issue #24). Kept in the route because that is where the
    request context worth naming lives.

    Args:
        cursor: Cursor the client sent back, or None for the first page.
        q: The search it was sent for, so the warning names it.

    Returns:
        The ``$match`` resuming after the cursor, or None for the first page.
    """
    if not cursor:
        return None

    decoded = decode_cursor(cursor)
    if decoded is None:
        logger.warning(
            'Ignoring malformed pagination cursor %r for search "%s"; '
            'expected "%s". Serving the first page.',
            cursor,
            q,
            CURSOR_FORMAT,
        )
        return None

    return cursor_match(*decoded)


# Registered before /cards/{name}: both are a single segment below /cards/
# and FastAPI matches in declaration order, so the other way round this route
# would be unreachable and every search would 404 as "Card search not found".
@router.get("/cards/search", response_model=SearchResponse)
def search_card_by_text(
    q: Annotated[
        str,
        Query(
            description=(
                "Full-text search query. A query parameter rather than a path "
                "segment because card names contain '//' - Fire // Ice, and "
                "every split or transforming card - and a path segment cannot "
                "carry one whatever the encoding (issue #26)."
            )
        ),
    ],
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
    # Positional, in the same order as this route's own signature.
    match_conditions = build_search_match(
        q, lang, sets, colors, color_operator, cmc_min, cmc_max, types, rarities
    )
    pipeline = build_search_pipeline(
        match_conditions, page_count, cursor_filter=_resume_filter(cursor, q)
    )

    results = list(collection.aggregate(pipeline))
    total = count_matching_oracle_cards(collection, match_conditions)

    return build_search_page(results, page_count, total)


@router.get("/cards/{name}", response_model=OracleCard)
def search_card_by_name(
    name: str,
    collection: CardsCollection,
    lang: str = "en",
    set: Optional[str] = None,
):
    results = find_cards_by_name(collection, name, lang, set)

    if len(results) == 0:
        raise HTTPException(status_code=404, detail=f"Card {name} not found")

    return expose_id(results[0])


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

    card = find_printing_by_scryfall_id(collection, scryfall_id)

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

    cards = find_printings_by_oracle_id(collection, oracle_id)

    if not cards:
        raise HTTPException(
            status_code=404, detail=f"No cards found with Oracle ID {oracle_id}"
        )

    return cards


@router.get("/cards/oracle/{oracle_id}/aggregated", response_model=OracleCard)
def get_aggregated_card_by_oracle_id(oracle_id: str, collection: CardsCollection):
    """Get a single card aggregated across all its printings, by Oracle ID.

    /cards/oracle/{oracle_id} returns the raw printings. This returns the same
    grouped shape that /cards/search produces for each result, so a
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

    results = find_aggregated_cards_by_oracle_id(collection, oracle_id)

    if not results:
        raise HTTPException(
            status_code=404, detail=f"No cards found with Oracle ID {oracle_id}"
        )

    return expose_id(results[0])
