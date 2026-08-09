"""Issues #27 and #28 - filter values reach MongoDB unvalidated.

``types`` is interpolated straight into a live ``$regex``. Two consequences,
and neither is theoretical:

* ``types=Cre.ture`` matches every card, because ``.`` is a metacharacter.
  A filter that silently matches everything looks exactly like a filter that
  is working, which is how this survived.
* ``types=(`` is not a regex at all. MongoDB rejects the pattern, pymongo
  raises, and the request 500s.

``/cards/{name}`` interpolates the requested name into a ``^`` anchored
``$regex`` the same way, so it carries the same 500.

CMC is the mirror image: the endpoint declares ``int``, so a fractional
bound is a 422 rather than a crash. That is the correct behaviour and is
pinned here - the fix for #28 belongs in the client, which should not be
emitting a value the API's own type contract forbids.
"""

import pytest
from fastapi.testclient import TestClient

from api.helpers.database import get_cards_collection
from api.main import app
from tests.fixtures.sample_cards import get_all_sample_cards
from tests.mocks.mongodb import MockMongoCollection


@pytest.fixture
def failing_client():
    """Client that reports a handler crash as 500 instead of re-raising.

    The point of these tests is the status code the caller sees, so the
    exception must be turned into a response the way it is in production.
    """
    app.dependency_overrides[get_cards_collection] = lambda: MockMongoCollection(
        get_all_sample_cards()
    )
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _names(response) -> list[str]:
    return [card["name"] for card in response.json()["cards"]]


@pytest.mark.integration
def test_types_filter_treats_its_value_as_text_not_a_pattern(failing_client):
    """``Cre.ture`` is not a card type, so it must match nothing.

    Today the ``.`` matches any character, so this returns every creature -
    which is what proves the value is used as a live regex.
    """
    response = failing_client.get(
        "/cards/search", params={"q": "a", "types": "Cre.ture", "page_count": 20}
    )

    assert response.status_code == 200
    assert _names(response) == []


@pytest.mark.integration
def test_a_wildcard_type_does_not_return_the_unfiltered_set(failing_client):
    """``types=.*`` must not be a way to ask for everything."""
    unfiltered = failing_client.get(
        "/cards/search", params={"q": "a", "page_count": 20}
    )
    wildcard = failing_client.get(
        "/cards/search", params={"q": "a", "types": ".*", "page_count": 20}
    )

    assert unfiltered.status_code == 200
    assert wildcard.status_code == 200
    assert len(_names(unfiltered)) > 0
    assert len(_names(wildcard)) < len(_names(unfiltered))


@pytest.mark.integration
@pytest.mark.parametrize("value", ["(", "[a-", "*", "a{2,", "\\"])
def test_an_unparseable_type_filter_is_answered_not_crashed(failing_client, value):
    """A value that is not a valid pattern must not reach MongoDB as one."""
    response = failing_client.get(
        "/cards/search", params={"q": "a", "types": value, "page_count": 20}
    )

    assert response.status_code == 200


@pytest.mark.integration
def test_the_real_types_the_ui_sends_still_filter(failing_client):
    """The escape must not break the eight values the search form offers."""
    response = failing_client.get(
        "/cards/search", params={"q": "a", "types": "Creature", "page_count": 20}
    )

    assert response.status_code == 200
    cards = response.json()["cards"]
    assert cards
    for card in cards:
        assert "Creature" in card.get("type_line", "")


@pytest.mark.integration
@pytest.mark.parametrize("name", ["(", "[a-", "*", "a{2,", "\\"])
def test_a_card_name_that_is_not_a_valid_pattern_is_answered_not_crashed(
    failing_client, name
):
    """``/cards/{name}`` anchors the name into a regex the same way."""
    response = failing_client.get(f"/cards/{name}")

    assert response.status_code == 404


@pytest.mark.integration
def test_a_card_name_is_matched_as_a_prefix_not_as_a_pattern(failing_client):
    """``.`` in a requested name must not stand for any character."""
    matched = failing_client.get("/cards/Black Lotus")
    patterned = failing_client.get("/cards/Bl.ck Lotus")

    assert matched.status_code == 200
    assert patterned.status_code == 404


@pytest.mark.integration
@pytest.mark.parametrize("bound", ["cmc_min", "cmc_max"])
def test_a_fractional_cmc_bound_is_rejected_rather_than_crashing(failing_client, bound):
    """The endpoint declares int, so 1.5 is bad input, not a server error.

    Pinned because issue #28's 500 is what the *web app* renders when this
    422 comes back: the client must stop emitting fractional bounds.
    """
    response = failing_client.get(
        "/cards/search", params={"q": "a", bound: "1.5", "page_count": 20}
    )

    assert response.status_code == 422
