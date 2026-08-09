"""A response model must not be able to take the API down.

The rule these tests encode, learned the hard way in foundation 0b:

    Strictness on a *response* model is an availability risk, not a
    test-coverage question. A request model rejects bad input; a response
    model returns HTTP 500.

``api/models/cards.py`` typed ``colors``/``color_identity`` as
``list[Color]``, where ``common.scyfall_models.Color`` is the closed
``Literal["W","U","B","R","G"]``. A stored card carrying ``["C"]`` - the
colorless code that MTGJSON and several Scryfall-adjacent dumps use where
Scryfall itself writes ``[]`` - therefore raised ``ResponseValidationError``
and the caller got a 500 instead of a card. Whether the production
collection holds such a document was never verified; that it *could*, and
that nobody could say, is the defect.

These are the runtime probes: odd-but-serviceable documents, served through
every endpoint that can return them. The structural guards that keep the
class of defect out live in ``test_response_model_strictness.py``.
"""

import pytest
from fastapi.testclient import TestClient

from api.helpers.database import get_cards_collection
from api.main import app
from tests.mocks.mongodb import MockMongoCollection
from tests.utils import CardBuilder


@pytest.fixture
def serve():
    """Serve one card through every card endpoint that can return it.

    ``raise_server_exceptions=False`` so a ``ResponseValidationError``
    surfaces as the 500 a real caller receives, rather than as an exception
    the test client re-raises. The status code is the symptom under test.
    """

    def make(card: dict) -> dict[str, int]:
        card["name_search"] = card["name"].lower()
        app.dependency_overrides[get_cards_collection] = lambda: MockMongoCollection(
            [card]
        )
        client = TestClient(app, raise_server_exceptions=False)
        return {
            "printing": client.get(f"/cards/id/{card['id']}"),
            "printings": client.get(f"/cards/oracle/{card['oracle_id']}"),
            "aggregated": client.get(f"/cards/{card['name_search']}"),
            "search": client.get("/cards/search", params={"q": card["name_search"]}),
        }

    yield make
    app.dependency_overrides.clear()


def test_a_colorless_card_is_served_rather_than_500(serve):
    """``colors=["C"]`` reaches the client instead of failing the response.

    All four endpoints, because the printing model is nested inside the
    aggregated one: a single unrecognised code failed the card at top level
    *and* again inside ``cards``, so it emptied a whole search page rather
    than spoiling one field.
    """
    card = (
        CardBuilder()
        .with_name("Ornithopter")
        .with_colors(["C"])
        .with_mana_cost("{0}")
        .with_cmc(0)
        .build()
    )

    responses = serve(card)

    assert {k: r.status_code for k, r in responses.items()} == {
        "printing": 200,
        "printings": 200,
        "aggregated": 200,
        "search": 200,
    }
    assert responses["printing"].json()["colors"] == ["C"]
    assert responses["printing"].json()["color_identity"] == ["C"]
    assert responses["aggregated"].json()["colors"] == ["C"]
    assert [c["colors"] for c in responses["search"].json()["cards"]] == [["C"]]


def test_a_null_image_uri_is_served_rather_than_500(serve):
    """A null inside ``image_uris`` must not fail the card either.

    Same defect class as the colour literal, one level down: ``dict[str,
    str]`` is a claim that every value of somebody else's object is a
    string. Scryfall's own ``prices`` object already uses nulls for absent
    values, so the convention exists in the same documents; whether it ever
    reaches ``image_uris`` or ``related_uris`` is - like ``["C"]`` -
    unverified, which is the reason not to bet an endpoint on it.
    """
    card = CardBuilder().with_name("Nullshot").build()
    card["image_uris"] = {**card["image_uris"], "png": None}
    card["related_uris"] = {"gatherer": None}

    responses = serve(card)

    assert {k: r.status_code for k, r in responses.items()} == {
        "printing": 200,
        "printings": 200,
        "aggregated": 200,
        "search": 200,
    }
    assert responses["printing"].json()["image_uris"]["png"] is None
