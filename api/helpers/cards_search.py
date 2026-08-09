"""Query construction for ``/cards/search``.

The route says *what* it is asking MongoDB for; this module holds the
filters and pipeline that ask it. The shapes it is built out of - the
projection, the grouping - live next door in :mod:`api.helpers.cards_mongo`;
the single-card lookups live in :mod:`api.helpers.cards_lookup`.
"""

import re
from typing import Optional

from api.helpers.cards_mongo import AGGREGATE_CARD, CARD_PROJECTION


def _color_filter(colors: list[str], color_operator: str) -> dict:
    """Turn the requested colors and combinator into a ``colors`` condition.

    Args:
        colors: Color codes the caller asked for.
        color_operator: ``"exactly"``, ``"and"``, or anything else for the
            default ``"or"``.

    Returns:
        Query fragment for the ``colors`` field.
    """
    if color_operator == "exactly":
        # Exactly these colors (no more, no less)
        return {"$all": colors, "$size": len(colors)}
    if color_operator == "and":
        # Contains all these colors (may have more)
        return {"$all": colors}
    # "or" - default: contains any of these colors
    return {"$in": colors}


def _cmc_filter(cmc_min: Optional[int], cmc_max: Optional[int]) -> dict:
    """Build the converted-mana-cost range condition.

    Args:
        cmc_min: Inclusive lower bound, or None for unbounded.
        cmc_max: Inclusive upper bound, or None for unbounded.

    Returns:
        Query fragment for the ``cmc`` field.
    """
    cmc_filter = {}
    if cmc_min is not None:
        cmc_filter["$gte"] = cmc_min
    if cmc_max is not None:
        cmc_filter["$lte"] = cmc_max
    return cmc_filter


def _type_filters(types: list[str]) -> list[dict]:
    """Build one ``type_line`` condition per requested type.

    type_line is a compound string - "Legendary Creature - Human Wizard" -
    so this stays a substring match rather than becoming an $in. What it
    must not stay is a *pattern*: interpolated raw, "Cre.ture" matched
    every creature and ".*" matched the entire collection, so a filter
    that quietly did nothing was indistinguishable from one that worked,
    and "(" was not a regex at all and 500ed the request (issue #27).

    Args:
        types: Card types the caller asked for.

    Returns:
        Conditions to be combined with ``$or``.
    """
    return [{"type_line": {"$regex": re.escape(t), "$options": "i"}} for t in types]


def build_search_match(
    q: str,
    lang: str,
    sets: list[str],
    colors: list[str],
    color_operator: str,
    cmc_min: Optional[int],
    cmc_max: Optional[int],
    types: list[str],
    rarities: list[str],
) -> dict:
    """Build the ``$match`` describing a search, filters and all.

    Returned separately from the pipeline because the total count runs the
    same conditions through a pipeline of its own - see
    :func:`api.helpers.cards_mongo.count_matching_oracle_cards` - so the
    count describes exactly the search that produced the page.

    Args:
        q: Full-text query.
        lang: Language code printings must carry.
        sets: Set names to restrict to, empty for all.
        colors: Color codes to restrict to, empty for all.
        color_operator: How to combine ``colors``; see :func:`_color_filter`.
        cmc_min: Inclusive lower bound on converted mana cost, or None.
        cmc_max: Inclusive upper bound on converted mana cost, or None.
        types: Card types to restrict to, empty for all.
        rarities: Rarities to restrict to, empty for all.

    Returns:
        Query dictionary for the pipeline's opening ``$match``.
    """
    match_conditions = {
        "$text": {
            "$search": q,
            "$caseSensitive": False,
            "$diacriticSensitive": False,
        },
        "lang": {"$eq": lang},
    }

    if sets:
        match_conditions["set_name"] = {"$in": sets}

    if colors:
        match_conditions["colors"] = _color_filter(colors, color_operator)

    if cmc_min is not None or cmc_max is not None:
        match_conditions["cmc"] = _cmc_filter(cmc_min, cmc_max)

    if types:
        match_conditions["$or"] = _type_filters(types)

    if rarities:
        match_conditions["rarity"] = {"$in": rarities}

    return match_conditions


def build_search_pipeline(
    match_conditions: dict,
    page_count: int,
    cursor_filter: Optional[dict] = None,
) -> list[dict]:
    """Build the pipeline returning one page of search results.

    Args:
        match_conditions: As built by :func:`build_search_match`.
        page_count: Cards the caller asked for.
        cursor_filter: Resume condition from
            :func:`api.helpers.cards_cursor.cursor_match`, or None for the
            first page.

    Returns:
        Aggregation pipeline yielding at most ``page_count + 1`` cards.
    """
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

    if cursor_filter is not None:
        pipeline.append({"$match": cursor_filter})

    # One extra document, fetched purely to detect a further page.
    pipeline.append({"$limit": page_count + 1})

    return pipeline
