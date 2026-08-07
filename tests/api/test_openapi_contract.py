"""The OpenAPI document is the API's contract, so it is tested like one.

Everything downstream of the schema - the generated TypeScript types, the
MSW stub, any response validator - is only as good as what ``app.openapi()``
actually says. Before this module existed the document described request
parameters and nothing at all about responses, so codegen produced
``unknown`` and a stub could return anything without contradicting it.
"""

import pytest
from fastapi.exceptions import ResponseValidationError
from fastapi.testclient import TestClient

from api.helpers.cards_mongo import AGGREGATE_CARD, CARD_PROJECTION
from api.helpers.database import get_cards_collection
from api.main import app
from api.models.cards import CardPrinting, OracleCard
from common.scyfall_models import PrintedCard
from scripts.generate_openapi import OPENAPI_PATH, render
from tests.mocks.mongodb import MockMongoCollection
from tests.utils import CardBuilder

AGGREGATED_PATH = "/cards/oracle/{oracle_id}/aggregated"

CARD_PATHS = [
    "/cards/{name}",
    "/cards/search/{text}",
    "/cards/id/{scryfall_id}",
    "/cards/oracle/{oracle_id}",
    AGGREGATED_PATH,
]

# Projected under names of their own rather than lifted from Scryfall: the
# image sizes clients render, pulled out of image_uris and card_faces.
DERIVED_PROJECTION_FIELDS = {"thumbnail", "faces_thumbnails", "image", "imageXL"}


@pytest.fixture(scope="module")
def openapi_spec() -> dict:
    """The document FastAPI serves at /openapi.json, built offline.

    ``api.main`` opens no database connection at import time, so the schema
    can be produced without Mongo, Meilisearch or any container.
    """
    app.openapi_schema = None
    spec = app.openapi()
    app.openapi_schema = None
    return spec


@pytest.fixture
def client_factory():
    """Build a TestClient over an arbitrary set of card documents.

    The shared ``test_client`` fixture is fixed to the sample cards, and the
    contract's edge cases are about documents the samples deliberately do
    not contain.
    """

    def make(documents: list[dict]) -> TestClient:
        app.dependency_overrides[get_cards_collection] = lambda: MockMongoCollection(
            documents
        )
        return TestClient(app)

    yield make
    app.dependency_overrides.clear()


def resolve(spec: dict, schema: dict) -> dict:
    """Follow a ``$ref`` into ``components/schemas`` if there is one."""
    ref = schema.get("$ref")
    if ref is None:
        return schema
    name = ref.rsplit("/", 1)[-1]
    return spec["components"]["schemas"][name]


def response_schema(spec: dict, path: str, status: str = "200") -> dict:
    """The resolved JSON schema of a path's response body."""
    response = spec["paths"][path]["get"]["responses"][status]
    content = response.get("content", {})
    assert "application/json" in content, (
        f"{path} declares no JSON response body: {response}"
    )
    return resolve(spec, content["application/json"]["schema"])


def test_aggregated_card_response_declares_a_required_id(openapi_spec):
    """The aggregated endpoint documents its response, and ``id`` is required.

    ``id`` is the whole point. It is the oracle_id the group was keyed on and
    the value every client builds a card URL from. While it lived only in
    ``_expose_id`` it was a convention; declaring it required makes it the
    contract, and makes a card without one a validation error at the boundary
    instead of an empty href in the browser.
    """
    schema = response_schema(openapi_spec, AGGREGATED_PATH)

    assert schema.get("type") == "object", (
        f"aggregated response is not an object schema: {schema}"
    )
    assert "id" in schema.get("properties", {}), (
        f"aggregated response declares no 'id' property: {sorted(schema.get('properties', {}))}"
    )
    assert "id" in schema.get("required", []), (
        f"'id' is not required on the aggregated response: {schema.get('required')}"
    )


@pytest.mark.parametrize("path", CARD_PATHS)
def test_every_card_endpoint_documents_its_response(openapi_spec, path):
    """No card endpoint may return an undocumented shape.

    An endpoint with no response model produces ``"schema": {}``, which
    generates as ``unknown`` and validates nothing - the state all ten
    endpoints were in.
    """
    schema = response_schema(openapi_spec, path)
    assert schema != {}, f"{path} documents an empty response schema"


def test_search_results_require_an_id_too(openapi_spec):
    """The id requirement holds for every card in a search page.

    Search is where a card with no oracle id actually surfaces - it lands
    in a single null-keyed group that sorts first, which is the dead first
    tile in issue #22.
    """
    schema = response_schema(openapi_spec, "/cards/search/{text}")
    card = resolve(openapi_spec, schema["properties"]["cards"]["items"])

    assert "id" in card.get("required", []), (
        f"search results do not require an id: {card.get('required')}"
    )
    for field in ("cursor", "has_more"):
        assert field in schema["properties"], f"search response omits {field}"


def test_oracle_card_matches_the_aggregation_that_produces_it():
    """OracleCard declares exactly what ``AGGREGATE_CARD`` groups.

    The model is only a contract while it describes the pipeline. Add a
    field to the ``$group`` and it would otherwise be silently filtered out
    of every response by the response model.
    """
    grouped = {"id" if key == "_id" else key for key in AGGREGATE_CARD}

    assert set(OracleCard.model_fields) == grouped


def test_card_printing_matches_the_projection_that_produces_it():
    """CardPrinting declares exactly what ``CARD_PROJECTION`` projects."""
    projected = {key for key in CARD_PROJECTION if key != "_id"}

    assert set(CardPrinting.model_fields) == projected


def test_card_printing_borrows_its_field_names_from_scryfall():
    """Every printing field is a Scryfall field, not one we invented.

    ``common.scyfall_models`` is the source of truth for what a card has.
    The four exceptions are the projection's own derived image fields.
    """
    borrowed = set(CardPrinting.model_fields) - DERIVED_PROJECTION_FIELDS

    assert borrowed <= set(PrintedCard.model_fields), (
        f"not Scryfall fields: {sorted(borrowed - set(PrintedCard.model_fields))}"
    )


def test_a_card_with_no_oracle_id_never_reaches_a_client_with_an_empty_id(
    client_factory,
):
    """The required ``id`` is enforced at runtime, not merely documented.

    Scryfall omits the top-level oracle id on ``reversible_card`` layouts -
    each face carries its own - so grouping on it produces a card keyed on
    nothing. What must never happen is that card arriving at a client with
    an id it can build a URL from, which is what ``id ?? _id ?? ""`` turned
    it into: ``href="/card"``.

    Refusing to serve it is one acceptable outcome and serving it with a
    real id is the other; issue #22 chooses between them. This asserts only
    the part that both must satisfy.
    """
    card = CardBuilder().with_name("Faceless").build()
    del card["oracle_id"]
    card["name_search"] = "faceless"

    client = client_factory([card])
    try:
        response = client.get("/cards/faceless")
    except ResponseValidationError:
        return  # The contract refused it at the boundary. Loud is fine.

    assert response.status_code == 200
    assert response.json()["id"], "a card was served with an empty id"


def test_committed_openapi_document_is_current():
    """openapi.json on disk matches the API as it is coded right now.

    The frontend generates its types and its stub from the committed file,
    so a stale one is a contract that quietly describes the wrong API. CI
    runs the same check.
    """
    assert OPENAPI_PATH.exists(), f"{OPENAPI_PATH} is missing. Run: just openapi"
    assert OPENAPI_PATH.read_text() == render(), (
        f"{OPENAPI_PATH.name} is out of date with the API. Run: just openapi"
    )
