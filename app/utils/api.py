from typing import Optional

import streamlit as st
from requests import get


@st.cache_data
def search_cards(
    text: str,
    cursor: Optional[str] = None,
    selected_sets: Optional[list[str]] = None,
    colors: Optional[list[str]] = None,
    color_operator: str = "or",
    cmc_min: Optional[int] = None,
    cmc_max: Optional[int] = None,
    types: Optional[list[str]] = None,
    rarities: Optional[list[str]] = None,
) -> dict:
    """Search for MTG cards with optional filters.

    Args:
        text: Search text
        cursor: Pagination cursor
        selected_sets: List of set names to filter by
        colors: List of colors (W, U, B, R, G)
        color_operator: How to apply color filter ("or", "and", "exactly")
        cmc_min: Minimum converted mana cost
        cmc_max: Maximum converted mana cost
        types: List of card types to filter by
        rarities: List of rarities to filter by

    Returns:
        Dict with 'cards', 'cursor', and 'has_more' keys
    """
    # Every one of these is a query parameter on the endpoint, including the
    # search text itself: as a path segment it could not carry a name
    # containing "//" - Fire // Ice and every split card - because the ASGI
    # server decodes %2F before routing (issue #26).
    #
    # The filters used to be sent as a JSON body, which the endpoint has never
    # read, so none of them had any effect from this client.
    params: dict = {"q": text, "cursor": cursor}
    if selected_sets:
        params["sets"] = selected_sets
    if colors:
        params["colors"] = colors
        params["color_operator"] = color_operator
    if cmc_min is not None:
        params["cmc_min"] = cmc_min
    if cmc_max is not None:
        params["cmc_max"] = cmc_max
    if types:
        params["types"] = types
    if rarities:
        params["rarities"] = rarities

    try:
        response = get(
            "http://api:8000/cards/search",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        cards = response.json()

        if "cards" not in cards:
            print(f"Unexpected response: {cards}")
            return {"cards": [], "cursor": None, "has_more": False}

        return cards
    except Exception as e:
        print(f"Error searching cards: {e}")
        return {"cards": [], "cursor": None, "has_more": False, "error": str(e)}


@st.cache_data
def all_sets() -> list[str]:
    return get("http://api:8000/sets").json()["sets"]
