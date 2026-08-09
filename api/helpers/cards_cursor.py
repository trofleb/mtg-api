"""Encode and decode the search endpoint's pagination cursor.

A cursor is the last card of a page written as ``"<score>:<oracle_id>"``.
Both halves are load-bearing: the search sorts by relevance score descending
and breaks ties on the grouping key ascending, so resuming needs the score to
know how far the ordering had got and the id to break the same tie the same
way. See :func:`api.helpers.cards_search.build_search_pipeline`.
"""

from typing import Optional

# What a well-formed cursor looks like, quoted back at clients that send one
# this module could not parse.
CURSOR_FORMAT = "<score>:<oracle_id>"


def encode_cursor(card: dict) -> str:
    """Point a cursor at the card a page ended on.

    Args:
        card: Last card of the page, after its grouping key has been exposed
            as ``id`` - which is the field the pipeline's cursor filter
            matches back as ``_id``.

    Returns:
        Cursor string in :data:`CURSOR_FORMAT`.
    """
    return f"{card['score']}:{card['id']}"


def decode_cursor(cursor: str) -> Optional[tuple[float, str]]:
    """Parse a cursor, or report that it cannot be parsed.

    Returns ``None`` rather than raising so the caller decides what an
    unusable cursor means. That decision belongs to the route: issue #24 is
    precisely that the old inline ``except`` made it silently, and it is the
    route that holds the request context worth logging.

    Args:
        cursor: Cursor string as handed back by :func:`encode_cursor`.

    Returns:
        ``(score, oracle_id)``, or ``None`` if the cursor is malformed.
    """
    try:
        score, oracle_id = cursor.split(":", 1)
        return float(score), oracle_id
    except (ValueError, IndexError):
        return None


def cursor_match(score: float, oracle_id: str) -> dict:
    """Build the ``$match`` that resumes the search after a cursor.

    Args:
        score: Relevance score of the card the previous page ended on.
        oracle_id: Grouping key of that same card.

    Returns:
        Query dictionary keeping documents that sort strictly after it -
        a lower score, or the same score and a greater grouping key.
    """
    return {
        "$or": [
            {"score": {"$lt": score}},
            {
                "$and": [
                    {"score": score},
                    {"_id": {"$gt": oracle_id}},
                ]
            },
        ]
    }
