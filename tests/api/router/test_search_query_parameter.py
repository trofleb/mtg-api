"""Issue #26 - the search text belongs in a query parameter, not the path.

``/cards/search/{text}`` cannot carry a card name containing ``//``. The
client percent-encodes the slashes, the ASGI server decodes them back before
routing, and FastAPI's ``{text}`` segment is ``[^/]+`` - so the route stops
matching and the request never reaches the handler. Magic prints those names
(``Fire // Ice``, every split and transforming card), and the app displays
them, so it is searching for a name it just rendered that breaks.

Nothing about the endpoint needed the path form: every filter it takes is
already a query parameter, and ``documentation/fastapi-testing-guide.md``
was written against ``?q=`` throughout.
"""

import pytest

from tests.fixtures.sample_cards import DELVER_OF_SECRETS

SPLIT_NAME = DELVER_OF_SECRETS["name"]


@pytest.mark.integration
def test_search_text_is_read_from_the_q_query_parameter(test_client):
    """The search text arrives as ?q=, not as a path segment."""
    response = test_client.get("/cards/search", params={"q": "lightning"})

    assert response.status_code == 200
    assert "Lightning Bolt" in [card["name"] for card in response.json()["cards"]]


@pytest.mark.integration
def test_search_route_is_matched_before_the_single_card_route(test_client):
    """``/cards/search`` must not be swallowed by ``/cards/{name}``.

    Both are one path segment below ``/cards``, and FastAPI matches in
    declaration order, so ``/cards/{name}`` would answer this request with
    404 "Card search not found" if it were registered first. A missing ``q``
    is a *validation* error, which is only reachable once the search route
    wins the match.
    """
    response = test_client.get("/cards/search")

    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.parametrize("name", ["Fire // Ice", SPLIT_NAME])
def test_search_for_a_name_containing_a_double_slash_returns_200(test_client, name):
    """Issue #26: these names used to be unroutable, whatever the encoding."""
    response = test_client.get("/cards/search", params={"q": name})

    assert response.status_code == 200


@pytest.mark.integration
def test_a_card_whose_name_contains_a_double_slash_is_findable(test_client):
    """The regression is only fixed if the card actually comes back."""
    response = test_client.get(
        "/cards/search", params={"q": SPLIT_NAME, "page_count": 20}
    )

    assert response.status_code == 200
    assert SPLIT_NAME in [card["name"] for card in response.json()["cards"]]


@pytest.mark.integration
def test_percent_encoded_slashes_survive_the_query_string(test_client):
    """``%2F`` in a query parameter is decoded as data, not as a separator.

    This is the difference the fix turns on: the same bytes in the path are
    decoded before routing, and there they end the segment.
    """
    response = test_client.get(f"/cards/search?q={SPLIT_NAME.replace('/', '%2F')}")

    assert response.status_code == 200
    assert SPLIT_NAME in [card["name"] for card in response.json()["cards"]]


@pytest.mark.integration
def test_filters_still_apply_alongside_the_q_parameter(test_client):
    """``q`` is one parameter among the filters, not a special case."""
    response = test_client.get(
        "/cards/search", params={"q": "a", "types": "Creature", "page_count": 20}
    )

    assert response.status_code == 200
    cards = response.json()["cards"]
    assert cards
    for card in cards:
        assert "Creature" in card.get("type_line", "")
