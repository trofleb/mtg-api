"""HTTP-level contract of the card endpoints, formerly ``e2e/api.spec.ts``.

These assertions used to live in the Playwright suite as 153 lines of direct
FastAPI calls behind a ``test.skip`` that fired whenever the API was not
exposed - which is every environment except a local stack or a VPS tunnel.
That skip is the structural reason Playwright had never run in CI: a browser
test file that talks straight to the backend cannot run where the backend is
deliberately unreachable, and production deliberately keeps it unreachable.

Nothing about them needs a browser. They assert status codes, content types
and response shapes, which is what ``TestClient`` is for - so they run on
every backend change instead of never, and the Playwright suite is left with
only assertions that need a real server.

Deliberately shallow: this is a smoke contract, not a behaviour suite. The
behaviour these endpoints implement is covered by the neighbouring integration
modules.
"""

import pytest

# The Playwright suite used a literal it hoped nothing would match.
MISSING_CARD_NAME = "ThisCardDefinitelyDoesNotExistInMTG123456"


@pytest.mark.integration
def test_ping_responds_pong(test_client):
    """/ping is the readiness probe every deploy check uses."""
    response = test_client.get("/ping")

    assert response.status_code == 200
    assert response.text == "pong"


@pytest.mark.integration
def test_unknown_route_is_404(test_client):
    """An unrouted path is a 404 rather than a 500."""
    response = test_client.get("/invalid-endpoint-12345")

    assert response.status_code == 404


@pytest.mark.integration
def test_search_returns_identified_cards(test_client):
    """Search returns a card list, and every card carries an id and a name."""
    response = test_client.get("/cards/search", params={"q": "lightning bolt"})

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["cards"], list)
    assert data["cards"], "expected at least one match for a sample card name"

    for card in data["cards"]:
        assert card["id"], f"card {card.get('name')!r} has no id"
        assert card["name"]


@pytest.mark.integration
def test_search_response_is_json(test_client):
    """The content type is what the client's `response.json()` assumes."""
    response = test_client.get("/cards/search", params={"q": "test"})

    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.integration
def test_search_accepts_filters(test_client):
    """Filters are query parameters and never change the response shape."""
    response = test_client.get(
        "/cards/search", params={"q": "dragon", "colors": "R", "types": "Creature"}
    )

    assert response.status_code == 200
    assert isinstance(response.json()["cards"], list)


@pytest.mark.integration
def test_search_advertises_a_cursor_and_follows_it(test_client):
    """The pagination contract: cards, cursor, has_more - and the cursor works.

    Asserted unconditionally. The Playwright original wrapped the second
    request in ``if (firstData.has_more)``, so it reported a pass on data that
    never paged; here the query and page size are chosen so it always does.
    """
    first = test_client.get("/cards/search", params={"q": "a", "page_count": 2})

    assert first.status_code == 200
    first_page = first.json()
    assert {"cards", "cursor", "has_more"} <= first_page.keys()
    assert first_page["has_more"] is True
    assert first_page["cursor"]

    second = test_client.get(
        "/cards/search",
        params={"q": "a", "page_count": 2, "cursor": first_page["cursor"]},
    )

    assert second.status_code == 200
    second_page = second.json()
    assert isinstance(second_page["cards"], list)

    first_ids = {card["id"] for card in first_page["cards"]}
    second_ids = {card["id"] for card in second_page["cards"]}
    assert not (first_ids & second_ids), "the cursor handed back a card from page 1"


@pytest.mark.integration
def test_search_of_whitespace_does_not_500(test_client):
    """A blank query is a client mistake, so it must not read as a server one."""
    response = test_client.get("/cards/search", params={"q": " "})

    assert response.status_code in (200, 404, 422)


@pytest.mark.integration
def test_get_card_by_name(test_client):
    """A card is addressable by name."""
    response = test_client.get("/cards/Black Lotus")

    assert response.status_code == 200

    data = response.json()
    assert data["id"]
    assert "Black Lotus" in data["name"]


@pytest.mark.integration
def test_get_card_by_unknown_name_is_404(test_client):
    """An unknown name is a 404, which is what the web app renders not-found from."""
    response = test_client.get(f"/cards/{MISSING_CARD_NAME}")

    assert response.status_code == 404


@pytest.mark.integration
def test_get_printing_by_scryfall_id(test_client):
    """A printing is addressable by its Scryfall id.

    The id has to come from a nested printing, not from the search result:
    search groups printings by oracle id, so a result's own ``id`` is an
    oracle id and would 404 here. The Playwright version of this test guarded
    the lookup with an `if` that was never true, so it asserted nothing.
    """
    search = test_client.get("/cards/search", params={"q": "lightning bolt"})
    assert search.status_code == 200

    printings = search.json()["cards"][0]["cards"]
    assert printings, "an aggregated card always carries at least one printing"

    scryfall_id = printings[0]["id"]
    response = test_client.get(f"/cards/id/{scryfall_id}")

    assert response.status_code == 200
    assert response.json()["id"] == scryfall_id
