"""Shape aggregation output into what the card endpoints return."""

from api.helpers.cards_cursor import encode_cursor


def expose_id(card: dict) -> dict:
    """Rename an aggregated card's "_id" to "id".

    Grouping by oracle_id forces the key onto "_id", which is a MongoDB
    detail rather than part of this API. The OracleCard response model
    declares "id" and requires it, so this is now how the pipeline meets
    that contract rather than being the contract itself.

    Args:
        card: Aggregated card as MongoDB returned it. Modified in place.

    Returns:
        The same card, keyed on ``id``.
    """
    if "_id" in card:
        card["id"] = card.pop("_id")
    return card


def build_search_page(results: list[dict], page_count: int, total: int) -> dict:
    """Split a search's aggregation output into a page and its pagination.

    Args:
        results: Up to ``page_count + 1`` cards, the last of which exists
            only to answer whether there is a further page.
        page_count: Cards the caller asked for.
        total: Oracle cards the search matched overall. Describes the
            search, not the page, so it is the same on page 5 as on page 1.
            Without it the client could only count what it had been handed
            and say "20+" forever (issue #25).

    Returns:
        The SearchResponse body.
    """
    page = [expose_id(card) for card in results[:page_count]]
    has_more = len(results) > page_count

    return {
        "cards": page,
        # The cursor points at the last card of this page. Its "id" is the
        # grouping key, which the pipeline's cursor filter matches as "_id".
        "cursor": encode_cursor(page[-1]) if has_more and page else None,
        "has_more": has_more,
        "total": total,
    }
