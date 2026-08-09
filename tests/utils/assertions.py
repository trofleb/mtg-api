"""Assertion helpers for MTG API integration tests.

This module provides reusable assertion functions to validate API response
structures and reduce code duplication across test files.
"""

import re


def assert_valid_uuid(value: str, field_name: str = "field") -> None:
    """Validate that a value is a properly formatted UUID.

    Args:
        value: The value to validate as a UUID
        field_name: Name of the field being validated (for error messages)

    Raises:
        AssertionError: If the value is not a valid UUID format
    """
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
    )
    assert isinstance(value, str), f"{field_name} must be a string, got {type(value)}"
    assert uuid_pattern.match(value), (
        f"{field_name} is not a valid UUID format: {value}"
    )


def assert_card_has_fields(card: dict, fields: list[str]) -> None:
    """Validate that a card dictionary contains all specified fields.

    Args:
        card: The card dictionary to validate
        fields: List of field names that must be present

    Raises:
        AssertionError: If any required field is missing
    """
    assert isinstance(card, dict), f"Card must be a dict, got {type(card)}"
    for field in fields:
        assert field in card, f"Card missing required field: {field}"


def assert_valid_image_uris(image_uris: dict) -> None:
    """Validate that image_uris contains all 6 required variants.

    Args:
        image_uris: The image_uris dictionary to validate

    Raises:
        AssertionError: If any required variant is missing or invalid
    """
    assert isinstance(image_uris, dict), (
        f"image_uris must be a dict, got {type(image_uris)}"
    )

    required_variants = ["small", "normal", "large", "png", "art_crop", "border_crop"]
    for variant in required_variants:
        assert variant in image_uris, f"image_uris missing required variant: {variant}"
        uri = image_uris[variant]
        assert isinstance(uri, str), f"image_uris[{variant}] must be string"
        assert uri.startswith(("http://", "https://")), (
            f"image_uris[{variant}] must be a valid URL: {uri}"
        )


def assert_valid_card_response(card: dict) -> None:
    """Validate that a card response includes all required PrintedCard fields.

    This validates the complete structure returned by card endpoints like
    /cards/id/{scryfall_id} or /cards/{name}.

    Args:
        card: The card dictionary to validate

    Raises:
        AssertionError: If any required field is missing or has wrong type
    """
    # Core identification fields (always required)
    core_fields = ["id", "oracle_id", "name", "lang"]
    assert_card_has_fields(card, core_fields)

    # Validate UUID formats
    assert_valid_uuid(card["id"], "id")
    assert_valid_uuid(card["oracle_id"], "oracle_id")

    # Gameplay fields (usually present)
    gameplay_fields = ["type_line", "cmc"]
    assert_card_has_fields(card, gameplay_fields)
    assert isinstance(card["cmc"], (int, float)), "cmc must be numeric"

    # Colors must be a list (can be empty for colorless)
    if "colors" in card:
        assert isinstance(card["colors"], list), "colors must be a list"

    # Set information fields
    set_fields = ["set", "rarity"]
    assert_card_has_fields(card, set_fields)

    # Image URIs (validate structure if present)
    if "image_uris" in card and card["image_uris"] is not None:
        assert_valid_image_uris(card["image_uris"])

    # Layout field
    if "layout" in card:
        assert isinstance(card["layout"], str), "layout must be a string"


def assert_valid_search_response(data: dict, min_cards: int = 0) -> None:
    """Validate the structure of a search endpoint response.

    Validates responses from /cards/search endpoint.

    Args:
        data: The response data dictionary to validate
        min_cards: Minimum number of cards expected in results (default: 0)

    Raises:
        AssertionError: If response structure is invalid
    """
    assert isinstance(data, dict), f"Response must be a dict, got {type(data)}"

    # Required top-level fields
    required_fields = ["cards", "cursor", "has_more"]
    for field in required_fields:
        assert field in data, f"Search response missing required field: {field}"

    # Validate cards array
    assert isinstance(data["cards"], list), "cards must be a list"
    assert len(data["cards"]) >= min_cards, (
        f"Expected at least {min_cards} cards, got {len(data['cards'])}"
    )

    # Validate cursor (can be None or string)
    assert data["cursor"] is None or isinstance(data["cursor"], str), (
        "cursor must be None or string"
    )

    # Validate has_more flag
    assert isinstance(data["has_more"], bool), "has_more must be a boolean"

    # Validate each aggregated card in results
    for i, card in enumerate(data["cards"]):
        assert_valid_aggregated_card(card, f"cards[{i}]")


def assert_valid_aggregated_card(card: dict, context: str = "card") -> None:
    """Validate the structure of an aggregated card in search results.

    Search results group cards by oracle_id with all printings included.

    Args:
        card: The aggregated card dictionary to validate
        context: Context string for error messages (e.g., "cards[0]")

    Raises:
        AssertionError: If aggregated card structure is invalid
    """
    assert isinstance(card, dict), f"{context} must be a dict, got {type(card)}"

    # Required aggregation fields
    required_fields = ["id", "name", "card_count", "cards"]
    for field in required_fields:
        assert field in card, f"{context} missing required field: {field}"

    # Validate id is a UUID (the oracle_id this group was keyed on)
    assert_valid_uuid(card["id"], f"{context}.id")

    # Validate name
    assert isinstance(card["name"], str), f"{context}.name must be a string"

    # Validate card_count
    assert isinstance(card["card_count"], int), (
        f"{context}.card_count must be an integer"
    )
    assert card["card_count"] > 0, f"{context}.card_count must be positive"

    # Validate cards array (all printings)
    assert isinstance(card["cards"], list), f"{context}.cards must be a list"
    assert len(card["cards"]) == card["card_count"], (
        f"{context}.cards length must match card_count"
    )

    # Validate each printing in the cards array
    for i, printing in enumerate(card["cards"]):
        # Each printing should have basic card fields
        printing_context = f"{context}.cards[{i}]"
        assert isinstance(printing, dict), (
            f"{printing_context} must be a dict, got {type(printing)}"
        )
        assert "id" in printing, f"{printing_context} missing id field"
        assert_valid_uuid(printing["id"], f"{printing_context}.id")


def assert_valid_sets_response(sets: list) -> None:
    """Validate the structure of the /sets endpoint response.

    Args:
        sets: The sets array to validate

    Raises:
        AssertionError: If sets response structure is invalid
    """
    assert isinstance(sets, list), f"Sets response must be a list, got {type(sets)}"

    # Each set should be a string (set name)
    for i, set_name in enumerate(sets):
        assert isinstance(set_name, str), (
            f"sets[{i}] must be a string, got {type(set_name)}"
        )
        assert len(set_name) > 0, f"sets[{i}] must not be empty"

    # Verify alphabetical sorting if there are multiple sets
    if len(sets) > 1:
        sorted_sets = sorted(sets)
        assert sets == sorted_sets, "Sets must be alphabetically sorted"
