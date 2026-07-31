"""Integration tests for Sets Router endpoints.

This module tests the /sets endpoint which returns a list of unique MTG set names
from the cards collection, validating MongoDB aggregation and sorting.
"""

import pytest


@pytest.mark.integration
def test_get_sets_returns_unique_set_names(test_client):
    """Test that /sets endpoint returns all unique set names.

    This test validates that:
    - The endpoint returns HTTP 200
    - Response has correct structure: {"sets": [...]}
    - All unique set names are returned
    - Duplicate set names are deduplicated (MongoDB $group)
    - Multiple cards from the same set result in single entry

    Expected: 4 unique sets from sample data:
    - Limited Edition Alpha (4 cards)
    - Double Masters (1 card)
    - Conflux (1 card)
    - Innistrad (1 card)
    """
    response = test_client.get("/sets")

    assert response.status_code == 200

    data = response.json()
    assert "sets" in data
    assert isinstance(data["sets"], list)

    # Should have exactly 7 unique sets from sample data (updated with Phase 5 fixtures)
    assert len(data["sets"]) == 7

    # Verify all expected sets are present
    expected_sets = {
        "Limited Edition Alpha",
        "Double Masters",
        "Conflux",
        "Innistrad",
        "Return to Ravnica",
        "Magic 2011",
        "Rise of the Eldrazi",
    }
    assert set(data["sets"]) == expected_sets


@pytest.mark.integration
def test_get_sets_empty_database_returns_empty_list(test_client_empty):
    """Test that /sets endpoint handles empty database gracefully.

    This test validates that:
    - Empty database doesn't cause errors
    - Returns HTTP 200 (not 404 or 500)
    - Returns empty list, not null or error message
    - Response structure is still correct
    """
    response = test_client_empty.get("/sets")

    assert response.status_code == 200

    data = response.json()
    assert "sets" in data
    assert data["sets"] == []


@pytest.mark.integration
def test_get_sets_returns_alphabetically_sorted_ascending(test_client):
    """Test that /sets endpoint returns sets sorted A→Z alphabetically.

    This test validates that:
    - MongoDB $sort stage with _id: 1 works correctly
    - Sets are in ascending alphabetical order
    - Order is consistent across calls

    Expected order (A→Z):
    1. Conflux
    2. Double Masters
    3. Innistrad
    4. Limited Edition Alpha
    5. Magic 2011
    6. Return to Ravnica
    7. Rise of the Eldrazi
    """
    response = test_client.get("/sets")

    assert response.status_code == 200

    data = response.json()
    sets = data["sets"]

    # Verify we have all 7 sets (updated with Phase 5 fixtures)
    assert len(sets) == 7

    # Verify list is sorted in ascending (alphabetical) order
    assert sets == sorted(sets)
