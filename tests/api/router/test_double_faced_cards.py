"""Backend half of issue #35 - two faces have to survive the aggregation.

#35 is a rendering bug: ``CardDetails`` guarded its two-face branch on
``!thumbnail`` while deriving ``thumbnail`` from ``faces_thumbnails[0]``, so
the branch was unreachable and no back face was ever drawn. The fix is in the
component.

These tests pin the data the component depends on. The fix plan listed this
as untestable at the backend layer, because ``_apply_projection`` in the
MongoDB mock dropped ``CARD_PROJECTION``'s computed fields - ``thumbnail``
and ``faces_thumbnails`` came back absent whatever the pipeline did. Branch 3
replaced that with a real expression evaluator, so the projection is now
observable and the claim can be made:

* ``faces_thumbnails`` carries **one entry per face**, not one entry.
* ``thumbnail`` is null on exactly the cards that have faces, which is why a
  client must not decide "does this card have a back face?" by looking at it.

Both double-faced layouts are covered, because they differ in where the
oracle id lives: ``transform`` keeps a top-level one, ``reversible_card``
puts one on each face (issue #22).
"""

import pytest
from fastapi.testclient import TestClient

from api.helpers.database import get_cards_collection
from api.main import app
from tests.fixtures.reversible_cards import get_all_reversible_cards
from tests.fixtures.sample_cards import get_all_sample_cards
from tests.mocks.mongodb import MockMongoCollection

# Delver of Secrets // Insectile Aberration - layout "transform". Two faces,
# each with its own image_uris, and no top-level image_uris at all.
DELVER_ORACLE_ID = "e2f3a4b5-6c7d-8e9f-0a1b-2c3d4e5f6a7b"
DELVER_FACES = [
    "https://cards.scryfall.io/normal/delver-front.jpg",
    "https://cards.scryfall.io/normal/delver-back.jpg",
]

# Command Tower // Command Tower - layout "reversible_card", whose oracle id
# lives on the faces rather than on the card.
REVERSIBLE_ORACLE_ID = "c1f1d1e1-2222-4333-8444-555566667777"
REVERSIBLE_FACES = [
    "https://cards.scryfall.io/normal/tower-front.jpg",
    "https://cards.scryfall.io/normal/tower-back.jpg",
]

# Lightning Bolt - one face, one image, and the control for every assertion
# below: whatever the two-face cards do, a single-faced card must not.
BOLT_ORACLE_ID = "b29c8b8a-2c8f-4891-88bc-f35d07a68293"


@pytest.fixture
def double_faced_client():
    """TestClient over the sample cards plus the reversible-layout ones.

    Yields:
        TestClient whose collection holds both double-faced layouts.
    """
    collection = MockMongoCollection(
        get_all_sample_cards() + get_all_reversible_cards()
    )
    app.dependency_overrides[get_cards_collection] = lambda: collection
    yield TestClient(app)
    app.dependency_overrides.clear()


def aggregated(client: TestClient, oracle_id: str) -> dict:
    """Fetch one aggregated card and assert the request succeeded.

    Args:
        client: TestClient to request through.
        oracle_id: Oracle id to look the card up by.

    Returns:
        The decoded aggregated card.
    """
    response = client.get(f"/cards/oracle/{oracle_id}/aggregated")
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.integration
def test_transform_card_aggregates_two_faces_thumbnails(double_faced_client):
    """A transform card comes back with both face images, in face order."""
    card = aggregated(double_faced_client, DELVER_ORACLE_ID)

    assert card["faces_thumbnails"] == DELVER_FACES


@pytest.mark.integration
def test_reversible_card_aggregates_two_faces_thumbnails(double_faced_client):
    """A reversible card does too, despite having no top-level oracle id."""
    card = aggregated(double_faced_client, REVERSIBLE_ORACLE_ID)

    assert card["faces_thumbnails"] == REVERSIBLE_FACES


@pytest.mark.integration
def test_double_faced_cards_have_no_top_level_thumbnail(double_faced_client):
    """``thumbnail`` is null on the cards that have faces.

    This is the shape that made the component bug invisible in review: the
    old code fell back to ``faces_thumbnails[0]`` precisely because the field
    it wanted was empty here, and that fallback then suppressed the two-face
    branch. Neither layout carries top-level ``image_uris``, so there is
    nothing for ``"$image_uris.normal"`` to project.
    """
    for oracle_id in (DELVER_ORACLE_ID, REVERSIBLE_ORACLE_ID):
        card = aggregated(double_faced_client, oracle_id)

        assert card["thumbnail"] is None, (
            f"{card['name']} projected a top-level thumbnail; the fixture no "
            "longer models a card whose only images are on its faces"
        )


@pytest.mark.integration
def test_single_faced_card_has_a_thumbnail_and_no_faces(double_faced_client):
    """The control: one face means an image and nothing to lay out two-up."""
    card = aggregated(double_faced_client, BOLT_ORACLE_ID)

    assert card["thumbnail"]
    assert not card["faces_thumbnails"]


@pytest.mark.integration
def test_search_results_carry_faces_thumbnails_too(double_faced_client):
    """Search returns the same aggregated shape, so it needs both faces too.

    The card grid renders from the search response, and clicking through to
    the modal renders ``CardDetails`` from it as well - so a face dropped
    here would be a face missing from the modal regardless of the component.
    """
    response = double_faced_client.get("/cards/search", params={"q": "delver"})
    assert response.status_code == 200, response.text

    delver = [
        card for card in response.json()["cards"] if card["id"] == DELVER_ORACLE_ID
    ]
    assert len(delver) == 1, "expected exactly one aggregated Delver of Secrets"
    assert delver[0]["faces_thumbnails"] == DELVER_FACES
