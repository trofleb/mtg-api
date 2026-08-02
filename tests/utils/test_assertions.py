"""Tests for assertion helper functions.

This module tests that assertion helpers correctly validate data
and raise appropriate errors for invalid inputs.
"""

import pytest

from tests.utils.assertions import (
    assert_card_has_fields,
    assert_valid_aggregated_card,
    assert_valid_card_response,
    assert_valid_image_uris,
    assert_valid_search_response,
    assert_valid_sets_response,
    assert_valid_uuid,
)
from tests.utils.builders import CardBuilder


class TestAssertValidUuid:
    """Test UUID validation helper."""

    def test_valid_uuid_passes(self):
        """Valid UUID should not raise."""
        valid_uuid = "550c74d4-a843-4208-a3c2-c71e84a21979"
        assert_valid_uuid(valid_uuid)  # Should not raise

    def test_invalid_uuid_raises(self):
        """Invalid UUID format should raise AssertionError."""
        with pytest.raises(AssertionError, match="not a valid UUID format"):
            assert_valid_uuid("not-a-uuid")

    def test_non_string_raises(self):
        """Non-string value should raise AssertionError."""
        with pytest.raises(AssertionError, match="must be a string"):
            assert_valid_uuid(12345)  # type: ignore


class TestAssertCardHasFields:
    """Test field existence validator."""

    def test_all_fields_present_passes(self):
        """Card with all required fields should not raise."""
        card = {"name": "Test", "id": "123", "type": "Instant"}
        assert_card_has_fields(card, ["name", "id", "type"])  # Should not raise

    def test_missing_field_raises(self):
        """Card missing required field should raise AssertionError."""
        card = {"name": "Test", "id": "123"}
        with pytest.raises(AssertionError, match="missing required field: type"):
            assert_card_has_fields(card, ["name", "id", "type"])

    def test_non_dict_raises(self):
        """Non-dict value should raise AssertionError."""
        with pytest.raises(AssertionError, match="must be a dict"):
            assert_card_has_fields("not a dict", ["name"])  # type: ignore


class TestAssertValidImageUris:
    """Test image URIs structure validator."""

    def test_complete_image_uris_passes(self):
        """Valid image_uris with all 6 variants should not raise."""
        image_uris = {
            "small": "https://example.com/small.jpg",
            "normal": "https://example.com/normal.jpg",
            "large": "https://example.com/large.jpg",
            "png": "https://example.com/card.png",
            "art_crop": "https://example.com/art.jpg",
            "border_crop": "https://example.com/border.jpg",
        }
        assert_valid_image_uris(image_uris)  # Should not raise

    def test_missing_variant_raises(self):
        """Missing image variant should raise AssertionError."""
        image_uris = {
            "small": "https://example.com/small.jpg",
            "normal": "https://example.com/normal.jpg",
            # Missing other variants
        }
        with pytest.raises(AssertionError, match="missing required variant"):
            assert_valid_image_uris(image_uris)

    def test_invalid_url_raises(self):
        """Non-URL value should raise AssertionError."""
        image_uris = {
            "small": "not-a-url",
            "normal": "https://example.com/normal.jpg",
            "large": "https://example.com/large.jpg",
            "png": "https://example.com/card.png",
            "art_crop": "https://example.com/art.jpg",
            "border_crop": "https://example.com/border.jpg",
        }
        with pytest.raises(AssertionError, match="must be a valid URL"):
            assert_valid_image_uris(image_uris)

    def test_non_dict_raises(self):
        """Non-dict value should raise AssertionError."""
        with pytest.raises(AssertionError, match="must be a dict"):
            assert_valid_image_uris("not a dict")  # type: ignore


class TestAssertValidCardResponse:
    """Test card response validator."""

    def test_valid_card_passes(self):
        """Valid card with all required fields should not raise."""
        card = CardBuilder().build()
        assert_valid_card_response(card)  # Should not raise

    def test_missing_core_field_raises(self):
        """Card missing core field should raise AssertionError."""
        card = CardBuilder().build()
        del card["name"]
        with pytest.raises(AssertionError, match="missing required field: name"):
            assert_valid_card_response(card)

    def test_invalid_uuid_raises(self):
        """Card with invalid UUID should raise AssertionError."""
        card = CardBuilder().with_id("not-a-uuid").build()
        with pytest.raises(AssertionError, match="not a valid UUID format"):
            assert_valid_card_response(card)

    def test_invalid_cmc_type_raises(self):
        """Card with non-numeric CMC should raise AssertionError."""
        card = CardBuilder().build()
        card["cmc"] = "not a number"
        with pytest.raises(AssertionError, match="cmc must be numeric"):
            assert_valid_card_response(card)

    def test_invalid_colors_type_raises(self):
        """Card with non-list colors should raise AssertionError."""
        card = CardBuilder().build()
        card["colors"] = "R"  # Should be ["R"]
        with pytest.raises(AssertionError, match="colors must be a list"):
            assert_valid_card_response(card)

    def test_colorless_card_passes(self):
        """Colorless card with empty colors array should not raise."""
        card = CardBuilder().colorless().build()
        assert_valid_card_response(card)  # Should not raise

    def test_invalid_image_uris_raises(self):
        """Card with invalid image_uris should raise AssertionError."""
        card = (
            CardBuilder()
            .with_image_uris(
                {
                    "small": "https://example.com/small.jpg",
                    "normal": "https://example.com/normal.jpg",
                    # Missing other required variants
                }
            )
            .build()
        )
        with pytest.raises(AssertionError, match="missing required variant"):
            assert_valid_card_response(card)


class TestAssertValidSearchResponse:
    """Test search response validator."""

    def test_valid_search_response_passes(self):
        """Valid search response should not raise."""
        response = {
            "cards": [
                {
                    "id": "550c74d4-a843-4208-a3c2-c71e84a21979",
                    "name": "Lightning Bolt",
                    "card_count": 1,
                    "cards": [
                        {
                            "id": "550c74d4-a843-4208-a3c2-c71e84a21979",
                            "name": "Lightning Bolt",
                        }
                    ],
                }
            ],
            "cursor": "score:oracle_id",
            "has_more": False,
        }
        assert_valid_search_response(response)  # Should not raise

    def test_empty_cards_array_passes(self):
        """Empty cards array should not raise."""
        response = {"cards": [], "cursor": None, "has_more": False}
        assert_valid_search_response(response)  # Should not raise

    def test_missing_field_raises(self):
        """Missing required field should raise AssertionError."""
        response = {"cards": [], "cursor": None}  # Missing has_more
        with pytest.raises(AssertionError, match="missing required field"):
            assert_valid_search_response(response)

    def test_invalid_cards_type_raises(self):
        """Non-list cards should raise AssertionError."""
        response = {"cards": "not a list", "cursor": None, "has_more": False}
        with pytest.raises(AssertionError, match="cards must be a list"):
            assert_valid_search_response(response)

    def test_invalid_has_more_type_raises(self):
        """Non-boolean has_more should raise AssertionError."""
        response = {"cards": [], "cursor": None, "has_more": "yes"}
        with pytest.raises(AssertionError, match="has_more must be a boolean"):
            assert_valid_search_response(response)

    def test_min_cards_validation(self):
        """Should validate minimum number of cards."""
        response = {"cards": [], "cursor": None, "has_more": False}
        with pytest.raises(AssertionError, match="Expected at least 1 cards"):
            assert_valid_search_response(response, min_cards=1)


class TestAssertValidAggregatedCard:
    """Test aggregated card validator."""

    def test_valid_aggregated_card_passes(self):
        """Valid aggregated card should not raise."""
        card = {
            "id": "550c74d4-a843-4208-a3c2-c71e84a21979",
            "name": "Lightning Bolt",
            "card_count": 2,
            "cards": [
                {
                    "id": "550c74d4-a843-4208-a3c2-c71e84a21979",
                    "name": "Lightning Bolt",
                },
                {
                    "id": "a1234567-1234-1234-1234-123456789abc",
                    "name": "Lightning Bolt",
                },
            ],
        }
        assert_valid_aggregated_card(card)  # Should not raise

    def test_missing_field_raises(self):
        """Missing required field should raise AssertionError."""
        card = {
            "id": "550c74d4-a843-4208-a3c2-c71e84a21979",
            "name": "Lightning Bolt",
            # Missing card_count and cards
        }
        with pytest.raises(AssertionError, match="missing required field"):
            assert_valid_aggregated_card(card)

    def test_invalid_oracle_id_raises(self):
        """Invalid oracle_id (_id) should raise AssertionError."""
        card = {
            "id": "not-a-uuid",
            "name": "Lightning Bolt",
            "card_count": 1,
            "cards": [{"id": "550c74d4-a843-4208-a3c2-c71e84a21979"}],
        }
        with pytest.raises(AssertionError, match="not a valid UUID format"):
            assert_valid_aggregated_card(card)

    def test_mismatched_count_raises(self):
        """Mismatched card_count and cards length should raise AssertionError."""
        card = {
            "id": "550c74d4-a843-4208-a3c2-c71e84a21979",
            "name": "Lightning Bolt",
            "card_count": 5,  # Says 5 but only has 1
            "cards": [{"id": "550c74d4-a843-4208-a3c2-c71e84a21979"}],
        }
        with pytest.raises(AssertionError, match="length must match card_count"):
            assert_valid_aggregated_card(card)

    def test_invalid_printing_id_raises(self):
        """Invalid printing ID should raise AssertionError."""
        card = {
            "id": "550c74d4-a843-4208-a3c2-c71e84a21979",
            "name": "Lightning Bolt",
            "card_count": 1,
            "cards": [{"id": "not-a-uuid"}],
        }
        with pytest.raises(AssertionError, match="not a valid UUID format"):
            assert_valid_aggregated_card(card)


class TestAssertValidSetsResponse:
    """Test sets response validator."""

    def test_valid_sets_passes(self):
        """Valid sets array should not raise."""
        sets = ["Alpha", "Beta", "Gamma"]
        assert_valid_sets_response(sets)  # Should not raise

    def test_empty_sets_passes(self):
        """Empty sets array should not raise."""
        sets = []
        assert_valid_sets_response(sets)  # Should not raise

    def test_non_list_raises(self):
        """Non-list value should raise AssertionError."""
        with pytest.raises(AssertionError, match="must be a list"):
            assert_valid_sets_response("not a list")  # type: ignore

    def test_non_string_element_raises(self):
        """Non-string element should raise AssertionError."""
        sets = ["Alpha", 123, "Gamma"]
        with pytest.raises(AssertionError, match="must be a string"):
            assert_valid_sets_response(sets)

    def test_empty_string_raises(self):
        """Empty string element should raise AssertionError."""
        sets = ["Alpha", "", "Gamma"]
        with pytest.raises(AssertionError, match="must not be empty"):
            assert_valid_sets_response(sets)

    def test_unsorted_sets_raises(self):
        """Unsorted sets should raise AssertionError."""
        sets = ["Zebra", "Alpha", "Beta"]  # Not alphabetical
        with pytest.raises(AssertionError, match="must be alphabetically sorted"):
            assert_valid_sets_response(sets)

    def test_sorted_sets_passes(self):
        """Alphabetically sorted sets should not raise."""
        sets = ["Alpha", "Beta", "Gamma", "Zebra"]
        assert_valid_sets_response(sets)  # Should not raise
