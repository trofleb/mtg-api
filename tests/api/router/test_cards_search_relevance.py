"""Integration tests for search relevance ranking and cursor pagination.

Covers issues #21 (no relevance ranking; pagination loops forever) and #24
(invalid cursors silently swallowed).

The endpoint sorts by ``{"score": -1, "_id": 1}``. When the pipeline fails to
project a real text score, every document ties at ``None`` and the sort
degenerates to ``_id`` ascending -- so results come back in oracle-id order,
the cursor is emitted as the literal string ``"None:<id>"``, and the next
request cannot parse it.

Guarding against the mock's fidelity gaps
-----------------------------------------
``tests/mocks/mongodb.py`` matches ``$text`` by substring against
``str(doc).lower()`` -- the whole document repr, including field names and
image URLs -- while ``$meta`` scoring only weighs six whitelisted fields. Two
consequences shape the queries chosen here:

1. Short queries match everything. ``"a"`` matches all 12 sample cards, so a
   test built on it asserts against an artificially broad result set. Every
   query below is a full word.
2. A document can match and still score 0.0. That is used deliberately: for
   ``"sol ring"`` the decoy matches only through its ``artist``
   ("Sandra Everingham" contains "ring"), an unscored field. Each test that
   depends on a decoy asserts the decoy is present, so a fixture change that
   removes it fails the test loudly instead of letting it pass vacuously.
"""

import logging

import pytest

# =============================================================================
# RELEVANCE RANKING (#21)
# =============================================================================


@pytest.mark.integration
def test_search_ranks_exact_name_match_first(test_client):
    """An exact card-name query returns that card, ranked first.

    "Sol Ring" scores 10.0 on the card name. "Giant Growth" scores 0.0 -- it
    matches only through its artist -- yet its oracle_id (d4e5f6a7...) sorts
    before Sol Ring's (f6a7b8c9...). So relevance order is the exact reverse
    of _id order and an _id fallback cannot rank Sol Ring first by accident.
    """
    response = test_client.get(
        "/cards/search", params={"q": "sol ring", "page_count": 10}
    )

    assert response.status_code == 200
    names = [card["name"] for card in response.json()["cards"]]

    # Guard: without the lower-scoring decoy in the candidate set the ranking
    # assertion below would be trivially true.
    assert "Giant Growth" in names, (
        "Fixture drift: the query no longer pulls in a lower-scoring decoy, "
        f"so it cannot discriminate relevance from _id order. Got {names}."
    )
    assert names[0] == "Sol Ring", (
        f"Expected the exact name match to rank first, got {names}"
    )


@pytest.mark.integration
def test_search_scores_are_populated_and_ordered(test_client):
    """Grouped results carry a real numeric score, ordered descending."""
    response = test_client.get(
        "/cards/search", params={"q": "instant", "page_count": 10}
    )

    assert response.status_code == 200
    cards = response.json()["cards"]
    assert len(cards) > 1, "Need several results for ordering to be observable"

    scores = [card.get("score") for card in cards]
    assert all(isinstance(score, (int, float)) for score in scores), (
        f"Every card needs a numeric relevance score, got {scores}"
    )
    assert scores == sorted(scores, reverse=True), (
        f"Scores must be ordered descending, got {scores}"
    )


# =============================================================================
# CURSOR PAGINATION (#21)
# =============================================================================


@pytest.mark.integration
def test_search_cursor_score_component_parses_as_float(test_client):
    """The emitted cursor's score component is a number, not "None".

    The cursor is built as f"{score}:{id}". A null score stringifies to the
    literal "None", which float() cannot parse on the next request.
    """
    response = test_client.get(
        "/cards/search", params={"q": "instant", "page_count": 2}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["has_more"] is True
    cursor = data["cursor"]
    assert cursor is not None

    score_part, _, id_part = cursor.partition(":")
    assert id_part, f"Cursor is missing its id component: {cursor!r}"
    float(score_part)  # raises ValueError on the literal "None"


@pytest.mark.integration
def test_search_second_page_shares_no_ids_with_first(test_client):
    """Paging with the emitted cursor advances instead of repeating page one.

    "instant" matches six distinct oracle groups, five of them tied on score,
    so this exercises the composite cursor's _id tie-break rather than only
    its score comparison.
    """
    first = test_client.get("/cards/search", params={"q": "instant", "page_count": 2})
    assert first.status_code == 200
    page1 = first.json()
    assert page1["has_more"] is True

    second = test_client.get(
        "/cards/search",
        params={"q": "instant", "page_count": 2, "cursor": page1["cursor"]},
    )
    assert second.status_code == 200
    page2 = second.json()

    page1_ids = {card["id"] for card in page1["cards"]}
    page2_ids = {card["id"] for card in page2["cards"]}

    assert page2_ids, "Second page came back empty"
    overlap = page1_ids & page2_ids
    assert not overlap, (
        f"Cursor did not advance: {len(overlap)} card(s) repeated on page 2 "
        f"({sorted(overlap)})"
    )


# =============================================================================
# INVALID CURSOR HANDLING (#24)
# =============================================================================


@pytest.mark.integration
@pytest.mark.parametrize(
    "bad_cursor",
    [
        "None:b29c8b8a-2c8f-4891-88bc-f35d07a68293",  # what the bug emitted
        "not-a-number:b29c8b8a-2c8f-4891-88bc-f35d07a68293",
        "no-separator-at-all",
    ],
    ids=["none-literal", "non-numeric-score", "missing-separator"],
)
def test_invalid_cursor_logs_a_warning(test_client, caplog, bad_cursor):
    """A cursor the server cannot parse is reported, not silently dropped.

    Issue #24: the bare ``except: pass`` meant a client stuck in a pagination
    loop got HTTP 200 throughout with nothing in the logs.
    """
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="api.router.cards"):
        response = test_client.get(
            "/cards/search", params={"q": "instant", "cursor": bad_cursor}
        )

    assert response.status_code == 200

    warnings = [
        record
        for record in caplog.records
        if record.levelno >= logging.WARNING and record.name == "api.router.cards"
    ]
    assert warnings, (
        f"Cursor {bad_cursor!r} was dropped without a warning; "
        "an unusable cursor must leave a trace in the logs"
    )
    assert "cursor" in warnings[0].getMessage().lower()
