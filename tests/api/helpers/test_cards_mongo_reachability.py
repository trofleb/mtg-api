"""Every aggregated field must read something the projection produces.

``AGGREGATE_CARD`` runs *after* ``{"$project": CARD_PROJECTION}``, so an
accumulator reading a field the projection drops sees nothing and emits
null - for every card, forever. The response model still declares the
field and the client still renders it, so both sides go on pretending it
works. Found this way: ``edhrec_rank`` and ``penny_rank`` were structurally
null in every aggregated response ever served.

This is a pure structural check rather than an HTTP one on purpose. The
defect is that a field is *unreachable*, which no fixture can demonstrate
by being absent - only by the pipeline being unable to carry it.
"""

import pytest
from fastapi.testclient import TestClient

from api.helpers.cards_mongo import AGGREGATE_CARD, CARD_PROJECTION
from api.helpers.database import get_cards_collection
from api.main import app
from tests.mocks.mongodb import MockMongoCollection
from tests.utils import CardBuilder


@pytest.fixture
def ranked_card_client():
    """Client over one card that carries a penny_rank."""
    card = CardBuilder().with_name("Ranked Card").build()
    card["name_search"] = "ranked card"
    card["penny_rank"] = 137

    app.dependency_overrides[get_cards_collection] = lambda: MockMongoCollection([card])
    yield TestClient(app), card
    app.dependency_overrides.clear()


def aggregated_sources() -> dict[str, str]:
    """Map each grouped field to the document field its accumulator reads.

    Skips ``_id`` (the grouping key), literal accumulators like
    ``{"$sum": 1}``, and ``$$ROOT``, none of which name a projected field.

    Returns:
        Grouped field name -> source field name.
    """
    sources = {}
    for field, accumulator in AGGREGATE_CARD.items():
        if field == "_id" or not isinstance(accumulator, dict):
            continue
        expression = next(iter(accumulator.values()))
        if not isinstance(expression, str) or not expression.startswith("$"):
            continue
        if expression.startswith("$$"):
            continue
        sources[field] = expression[1:]
    return sources


@pytest.mark.unit
def test_every_aggregated_field_reads_a_projected_field():
    """A grouped field whose source is dropped is null in every response."""
    projected = {key for key in CARD_PROJECTION if key != "_id"}

    unreachable = {
        field: source
        for field, source in aggregated_sources().items()
        if source not in projected
    }

    assert unreachable == {}, (
        "these aggregated fields are structurally always null, because "
        f"CARD_PROJECTION drops what they read: {unreachable}"
    )


@pytest.mark.integration
def test_a_stored_penny_rank_reaches_the_aggregated_response(ranked_card_client):
    """The structural fix, proven end to end through the real pipeline."""
    client, card = ranked_card_client

    response = client.get(f"/cards/oracle/{card['oracle_id']}/aggregated")

    assert response.status_code == 200
    assert response.json()["penny_rank"] == 137
