"""Integration tests for API response schema validation.

This module validates that all API endpoints return responses that match
documented schemas with all required fields present and correctly typed.
"""

import pytest

from tests.utils import (
    assert_valid_card_response,
    assert_valid_image_uris,
    assert_valid_search_response,
    assert_valid_sets_response,
)


@pytest.mark.integration
def test_card_response_has_all_required_fields(test_client):
    """Validate that card responses include all required PrintedCard fields.

    Tests the /cards/id/{scryfall_id} endpoint to ensure the response
    contains all fields defined in the PrintedCard model.
    """
    # Get Lightning Bolt by Scryfall ID
    response = test_client.get("/cards/id/550c74d4-a843-4208-a3c2-c71e84a21979")
    assert response.status_code == 200

    card = response.json()

    # Use assertion helper to validate complete card structure
    assert_valid_card_response(card)

    # Additional specific validation beyond the helper
    assert card["name"] == "Lightning Bolt"
    assert card["id"] == "550c74d4-a843-4208-a3c2-c71e84a21979"
    assert "oracle_text" in card
    assert "mana_cost" in card
    assert "set_name" in card


@pytest.mark.integration
def test_image_uris_structure_complete(test_client):
    """Validate that image_uris contains all 6 required variants.

    Tests that the image_uris field includes small, normal, large, png,
    art_crop, and border_crop variants, all with valid HTTPS URLs.
    """
    # Get card with image URIs using /cards/id endpoint (returns single card)
    response = test_client.get("/cards/id/550c74d4-a843-4208-a3c2-c71e84a21979")
    assert response.status_code == 200

    card = response.json()

    # Validate image URIs structure
    assert "image_uris" in card
    assert card["image_uris"] is not None
    assert_valid_image_uris(card["image_uris"])

    # Verify all 6 variants are HTTPS URLs
    required_variants = ["small", "normal", "large", "png", "art_crop", "border_crop"]
    for variant in required_variants:
        assert variant in card["image_uris"]
        assert card["image_uris"][variant].startswith("https://")


@pytest.mark.integration
def test_search_response_structure(test_client):
    """Validate search response structure with cards, cursor, and has_more.

    Tests that the /cards/search/{text} endpoint returns a properly
    structured response with aggregated cards by oracle_id.
    """
    # Search for "lightning"
    response = test_client.get("/cards/search/lightning")
    assert response.status_code == 200

    data = response.json()

    # Use assertion helper to validate search response
    assert_valid_search_response(data, min_cards=1)

    # Validate response structure details
    assert isinstance(data["cards"], list)
    assert len(data["cards"]) > 0

    # Validate first aggregated card structure
    first_card = data["cards"][0]
    assert "id" in first_card  # Oracle ID
    assert "name" in first_card
    assert "card_count" in first_card
    assert "cards" in first_card  # Array of all printings

    # Validate card_count matches number of printings
    assert len(first_card["cards"]) == first_card["card_count"]

    # Validate cursor structure (should be "score:oracle_id" or None)
    if data["cursor"] is not None:
        assert isinstance(data["cursor"], str)
        # Cursor format is "score:oracle_id"
        assert ":" in data["cursor"] or data["cursor"] == ""

    # Validate has_more is boolean
    assert isinstance(data["has_more"], bool)


@pytest.mark.integration
def test_sets_response_structure(test_client):
    """Validate sets endpoint returns alphabetically sorted array of strings.

    Tests that the /sets endpoint returns a list of set names as strings,
    sorted alphabetically.
    """
    # Get all sets
    response = test_client.get("/sets")
    assert response.status_code == 200

    data = response.json()

    # Response is a dict with "sets" key containing the array
    assert isinstance(data, dict)
    assert "sets" in data

    sets = data["sets"]

    # Use assertion helper to validate sets structure
    assert_valid_sets_response(sets)

    # Validate we have some sets (test data has at least 2 unique sets)
    assert len(sets) >= 2

    # All elements should be non-empty strings
    for set_name in sets:
        assert isinstance(set_name, str)
        assert len(set_name) > 0

    # Verify alphabetical sorting
    assert sets == sorted(sets)
