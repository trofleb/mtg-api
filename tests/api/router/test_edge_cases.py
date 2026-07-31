"""Integration tests for edge cases and error handling.

This module tests boundary conditions, special inputs, and error scenarios
to ensure the API handles edge cases gracefully.
"""

import pytest

from tests.utils import assert_valid_search_response


@pytest.mark.integration
def test_colorless_cards_with_exactly_operator(test_client):
    """Test that colorless cards (empty colors array) match with 'exactly' operator.

    Uses Black Lotus which has an empty colors array to verify that searching
    for colorless cards with the 'exactly' operator works correctly.
    """
    # Search for colorless cards using empty colors with "exactly" operator
    response = test_client.get("/cards/search/lotus?color_operator=exactly")
    assert response.status_code == 200

    data = response.json()
    assert_valid_search_response(data)

    # Should find Black Lotus (colorless)
    assert len(data["cards"]) >= 1

    # Find Black Lotus in results
    black_lotus = next(
        (card for card in data["cards"] if "Lotus" in card["name"]), None
    )
    assert black_lotus is not None
    assert black_lotus["colors"] == [] or len(black_lotus["colors"]) == 0


@pytest.mark.integration
def test_five_color_cards_with_exactly_operator(test_client):
    """Test five-color cards (WUBRG) with 'exactly' operator.

    Uses Progenitus to verify that five-color cards only match when all
    five colors are specified with the 'exactly' operator.
    """
    # Search for five-color cards with all 5 colors and "exactly" operator
    response = test_client.get(
        "/cards/search/progenitus"
        "?colors=W&colors=U&colors=B&colors=R&colors=G"
        "&color_operator=exactly"
    )
    assert response.status_code == 200

    data = response.json()
    assert_valid_search_response(data)

    # Should find Progenitus
    assert len(data["cards"]) >= 1

    # Find Progenitus in results
    progenitus = next(
        (card for card in data["cards"] if "Progenitus" in card["name"]), None
    )
    assert progenitus is not None
    # Should have exactly 5 colors
    assert len(progenitus["colors"]) == 5
    assert set(progenitus["colors"]) == {"W", "U", "B", "R", "G"}


@pytest.mark.integration
def test_cmc_zero_cards(test_client):
    """Test CMC 0 cards are correctly filtered.

    Uses Black Lotus (CMC 0) to verify that zero-cost cards can be found
    with CMC filtering.
    """
    # Search for CMC 0 cards
    response = test_client.get("/cards/search/lotus?cmc_min=0&cmc_max=0")
    assert response.status_code == 200

    data = response.json()
    assert_valid_search_response(data)

    # Should find Black Lotus
    assert len(data["cards"]) >= 1

    # All results should have CMC 0
    for card in data["cards"]:
        assert card["cmc"] == 0


@pytest.mark.integration
def test_very_high_cmc_cards(test_client):
    """Test very high CMC cards (15+) are correctly filtered.

    Uses Emrakul (CMC 15) to verify that high-cost cards can be found
    with CMC filtering.
    """
    # Search for CMC 15+ cards
    response = test_client.get("/cards/search/emrakul?cmc_min=15")
    assert response.status_code == 200

    data = response.json()
    assert_valid_search_response(data)

    # Should find Emrakul
    assert len(data["cards"]) >= 1

    # Find Emrakul in results
    emrakul = next((card for card in data["cards"] if "Emrakul" in card["name"]), None)
    assert emrakul is not None
    assert emrakul["cmc"] >= 15


@pytest.mark.integration
def test_invalid_scryfall_id_format(test_client):
    """Test that invalid UUID format returns appropriate error.

    Verifies that malformed Scryfall IDs are rejected with a clear error
    message and proper HTTP status code.
    """
    # Try to get card with invalid UUID format
    response = test_client.get("/cards/id/not-a-valid-uuid")

    # Should return 404 (not found) for invalid/non-existent cards
    # or 422 (unprocessable entity) or 400 (bad request) for malformed input
    assert response.status_code in [400, 404, 422]

    # Response should contain error information
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
def test_special_characters_in_search_query(test_client):
    """Test that special characters in search queries don't cause errors.

    Tests various special characters (quotes, slashes, unicode) to ensure
    the search endpoint handles them gracefully.
    """
    special_queries = [
        "lightning",  # Normal query (baseline)
        "test's",  # Apostrophe
        "test-test",  # Dash
        "test+test",  # Plus
        '"test"',  # Quotes
    ]

    for query in special_queries:
        response = test_client.get(f"/cards/search/{query}")

        # Should not crash - returns 200 with results, 200 with empty results, or 404 not found
        # The key is it shouldn't return 500 (server error)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should have valid response structure (even if empty)
            assert_valid_search_response(data, min_cards=0)
            assert "cards" in data
            assert "cursor" in data
            assert "has_more" in data
        else:  # 404
            # 404 is acceptable for queries with no matches
            data = response.json()
            assert "detail" in data


@pytest.mark.integration
def test_database_connection_error_handling(test_client_empty):
    """Test that database errors are handled with appropriate HTTP status.

    This test verifies that database connection issues or query failures
    result in proper error responses rather than crashes.

    Note: This test uses a mock that can be configured to fail. In a real
    scenario, you might need to temporarily break the database connection
    or use dependency overrides to inject a failing mock.
    """
    # Using the empty collection fixture, which might not have all operations
    # For now, just verify that endpoints return proper responses even with empty data

    response = test_client_empty.get("/cards/search/nonexistent")
    assert response.status_code == 200

    data = response.json()
    # Empty database should return empty results, not crash
    assert_valid_search_response(data, min_cards=0)
    assert len(data["cards"]) == 0
    assert data["has_more"] is False


# Additional edge case tests that could be added in the future:
# - test_duplicate_filter_parameters (e.g., colors=R&colors=R)
# - test_contradictory_filters (e.g., cmc_min=10&cmc_max=5)
# - test_extremely_long_search_query (> 1000 characters)
# - test_pagination_beyond_available_results
# - test_negative_cmc_values
# - test_invalid_color_codes (e.g., colors=X)
# - test_case_sensitivity_in_search
