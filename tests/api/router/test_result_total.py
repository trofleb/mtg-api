"""Issue #25 - the result count only ever described the current page.

``app/page.tsx`` derived it from ``results.cards.length`` plus a ``+`` when
``has_more`` was set, so every page of every search read "20+ results
found" - including the last one, and including page 5 of a search with 21
matches. The page array cannot answer "how many results are there"; only
the database can, so the endpoint returns the count alongside the page.

The count is of *oracle cards*, matching what the page contains: the
pipeline groups printings by oracle id, so counting matched printings
would overcount every reprinted card.
"""

import pytest

BROAD_QUERY = "a"


@pytest.mark.integration
def test_the_search_response_carries_a_total(test_client):
    response = test_client.get("/cards/search", params={"q": "lightning"})

    assert response.status_code == 200
    assert "total" in response.json()


@pytest.mark.integration
def test_the_total_counts_the_whole_result_set_not_the_page(test_client):
    """A page of 2 out of a larger set must not report a total of 2."""
    page = test_client.get(
        "/cards/search", params={"q": BROAD_QUERY, "page_count": 2}
    ).json()
    everything = test_client.get(
        "/cards/search", params={"q": BROAD_QUERY, "page_count": 100}
    ).json()

    assert len(page["cards"]) == 2
    assert page["has_more"] is True
    assert page["total"] == len(everything["cards"])
    assert page["total"] > len(page["cards"])


@pytest.mark.integration
def test_the_total_does_not_change_as_pages_advance(test_client):
    """It describes the search, so paging through it must not move it."""
    first = test_client.get(
        "/cards/search", params={"q": BROAD_QUERY, "page_count": 2}
    ).json()
    assert first["cursor"]

    second = test_client.get(
        "/cards/search",
        params={"q": BROAD_QUERY, "page_count": 2, "cursor": first["cursor"]},
    ).json()

    assert second["total"] == first["total"]


@pytest.mark.integration
def test_the_total_counts_oracle_cards_rather_than_printings(test_client):
    """Lightning Bolt is in the fixtures twice; it is one result, not two."""
    data = test_client.get(
        "/cards/search", params={"q": "lightning bolt", "page_count": 100}
    ).json()

    bolt = next(card for card in data["cards"] if card["name"] == "Lightning Bolt")
    assert bolt["card_count"] == 2
    assert data["total"] == len(data["cards"])


@pytest.mark.integration
def test_a_search_with_no_results_reports_a_total_of_zero(test_client):
    data = test_client.get("/cards/search", params={"q": "nonexistentcardxyz"}).json()

    assert data["cards"] == []
    assert data["total"] == 0


@pytest.mark.integration
def test_the_total_respects_the_filters(test_client):
    """It counts what the search actually matched, filters included."""
    unfiltered = test_client.get(
        "/cards/search", params={"q": BROAD_QUERY, "page_count": 100}
    ).json()
    filtered = test_client.get(
        "/cards/search",
        params={"q": BROAD_QUERY, "types": "Creature", "page_count": 100},
    ).json()

    assert filtered["total"] == len(filtered["cards"])
    assert 0 < filtered["total"] < unfiltered["total"]
