"""Regression tests for issue #22 - reversible cards collapse to a null id.

Scryfall omits the top-level ``oracle_id`` on a ``reversible_card`` layout,
putting one on each face instead. ``AGGREGATE_CARD`` groups on
``{"_id": "$oracle_id"}``, so every reversible card in a result set lands in
one bucket keyed ``None``.

Two consequences, and the tests below pin both:

1. The grouping key is null, so the aggregated card has no usable id. Since
   Branch 0b made ``id`` required on ``OracleCard`` this is no longer one dead
   tile - it fails response validation and the whole search returns nothing.
2. *Every* reversible card shares that one bucket, so two distinct cards merge
   into a single result and one of them disappears.
"""

import pytest
from fastapi.testclient import TestClient

from api.helpers.database import get_cards_collection
from api.main import app
from tests.fixtures.reversible_cards import (
    REVERSIBLE_SEARCH_TEXT,
    get_all_reversible_cards,
)
from tests.fixtures.sample_cards import get_all_sample_cards
from tests.mocks.mongodb import MockMongoCollection


@pytest.fixture
def reversible_collection():
    """Mock collection holding the ordinary sample cards plus reversible ones.

    Returns:
        MockMongoCollection with both fixture sets loaded.
    """
    return MockMongoCollection(get_all_sample_cards() + get_all_reversible_cards())


@pytest.fixture
def reversible_client(reversible_collection):
    """TestClient whose collection contains reversible-layout cards.

    Args:
        reversible_collection: Fixture providing the mock collection.

    Yields:
        TestClient instance with the dependency overridden.
    """
    app.dependency_overrides[get_cards_collection] = lambda: reversible_collection
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_search_returns_reversible_cards_with_non_null_ids(reversible_client):
    """Every card in a search response carries a usable, non-null id.

    This is the assertion the web app depends on: it builds ``/card/{id}``
    from this field, and ``normaliseCard``'s ``?? ""`` fallback turns a
    missing one into ``href="/card"``.
    """
    response = reversible_client.get(f"/cards/search?q={REVERSIBLE_SEARCH_TEXT}")

    assert response.status_code == 200, response.text

    cards = response.json()["cards"]
    assert len(cards) > 0, "search matched no cards - fixture or query is wrong"

    missing = [card["name"] for card in cards if not card.get("id")]
    assert missing == [], f"cards returned without an id: {missing}"


@pytest.mark.integration
def test_two_reversible_cards_do_not_merge_into_one_result(reversible_client):
    """Two distinct reversible cards stay two results.

    Grouping on a field neither card has puts both in one ``None`` bucket,
    so one of the two silently vanishes from the results.
    """
    response = reversible_client.get(f"/cards/search?q={REVERSIBLE_SEARCH_TEXT}")

    assert response.status_code == 200, response.text

    names = [card["name"] for card in response.json()["cards"]]
    assert "Propaganda // Propaganda" in names
    assert "Command Tower // Command Tower" in names


@pytest.mark.integration
def test_reversible_cards_get_distinct_ids(reversible_client):
    """Each reversible card gets its own id rather than sharing one.

    Distinctness is what the grid's ``key={card.id}`` needs, and it is what
    makes the ``/card/{id}`` link land on the right card.
    """
    response = reversible_client.get(f"/cards/search?q={REVERSIBLE_SEARCH_TEXT}")

    assert response.status_code == 200, response.text

    ids = [card["id"] for card in response.json()["cards"]]
    assert len(ids) == len(set(ids)), f"duplicate ids across results: {ids}"


@pytest.mark.integration
def test_lookup_by_name_returns_a_reversible_card_with_an_id(reversible_client):
    """``/cards/{name}`` groups on the same key, so it broke the same way."""
    response = reversible_client.get("/cards/Propaganda")

    assert response.status_code == 200, response.text

    card = response.json()
    assert card["name"] == "Propaganda // Propaganda"
    assert card["id"] == "b0e0c0d0-1111-4222-8333-444455556666"


@pytest.mark.integration
def test_search_id_resolves_through_the_aggregated_endpoint(reversible_client):
    """The id search hands out is one the card page can look up again.

    ``/card/{id}`` in the web app calls ``/cards/oracle/{id}/aggregated``, so
    an id that exists but resolves to nothing is still a dead tile - just a
    404 rather than a blank href.
    """
    search = reversible_client.get(f"/cards/search?q={REVERSIBLE_SEARCH_TEXT}")
    assert search.status_code == 200, search.text

    for card in search.json()["cards"]:
        aggregated = reversible_client.get(f"/cards/oracle/{card['id']}/aggregated")
        assert aggregated.status_code == 200, (
            f"{card['name']} has id {card['id']!r}, which does not resolve: "
            f"{aggregated.text}"
        )
        assert aggregated.json()["name"] == card["name"]


@pytest.mark.integration
def test_reversible_card_printings_are_listed_by_face_oracle_id(reversible_client):
    """``/cards/oracle/{id}`` lists a reversible card's printings too.

    The face oracle id is now what identifies the card everywhere else, so
    the printings endpoint has to answer to it as well.
    """
    face_oracle_id = "c1f1d1e1-2222-4333-8444-555566667777"

    response = reversible_client.get(f"/cards/oracle/{face_oracle_id}")

    assert response.status_code == 200, response.text
    printings = response.json()
    assert [printing["name"] for printing in printings] == [
        "Command Tower // Command Tower"
    ]
    assert printings[0]["oracle_id"] == face_oracle_id


@pytest.mark.integration
def test_reversible_card_printings_still_group_together(reversible_client):
    """A normal card's printings still collapse into one aggregated card.

    The fix changes the grouping key, so this guards the behaviour that key
    was there for: Lightning Bolt has two printings in the fixtures and must
    still come back as a single result carrying both.
    """
    response = reversible_client.get("/cards/search?q=lightning")

    assert response.status_code == 200, response.text

    bolts = [
        card for card in response.json()["cards"] if card["name"] == "Lightning Bolt"
    ]
    assert len(bolts) == 1, f"expected one aggregated Lightning Bolt, got {len(bolts)}"
    assert bolts[0]["card_count"] == 2
