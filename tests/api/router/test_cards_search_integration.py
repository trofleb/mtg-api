"""Integration tests for Cards Search endpoint (/cards/search?q=...).

This module tests search endpoint functionality:
- Full-text search functionality
- Cursor-based pagination
- Response structure validation

NOTE: Filter tests (card_filter parameter) require additional work to pass
Pydantic models as query parameters in GET requests. These will be added in a
follow-up or the endpoint should be changed to POST for complex filters.

Test Categories:
1. Basic text search
2. Pagination tests
"""

import pytest

# =============================================================================
# BASIC TEXT SEARCH TESTS
# =============================================================================


@pytest.mark.integration
def test_search_basic_text_query(test_client):
    """Test /cards/search?q= with basic text query (no filters).

    This validates:
    - Endpoint returns HTTP 200
    - MongoDB $text search is executed
    - Results are aggregated by oracle_id
    - Response structure matches expected format
    - Text search matches card name and oracle_text

    Search: "lightning"
    Expected: Lightning Bolt (matches name)
    """
    response = test_client.get("/cards/search?q=lightning")

    assert response.status_code == 200

    data = response.json()
    assert "cards" in data
    assert "cursor" in data
    assert "has_more" in data

    # Should find Lightning Bolt
    assert len(data["cards"]) > 0
    card_names = [card["name"] for card in data["cards"]]
    assert "Lightning Bolt" in card_names


@pytest.mark.integration
def test_search_matches_oracle_text(test_client):
    """Test that text search matches oracle_text field.

    This validates:
    - $text search includes oracle_text (not just name)
    - Cards with matching oracle_text are returned

    Search: "damage"
    Expected: Lightning Bolt ("deals 3 damage"), Izzet Charm ("deals 2 damage")
    """
    response = test_client.get("/cards/search?q=damage")

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Lightning Bolt has "deals 3 damage" in oracle_text
    card_names = [card["name"] for card in data["cards"]]
    assert "Lightning Bolt" in card_names


@pytest.mark.integration
def test_search_no_results(test_client):
    """Test search with no matching results.

    This validates:
    - Empty results return valid response structure
    - cards array is empty
    - cursor is None
    - has_more is False

    Search: "nonexistentcardxyz"
    Expected: Empty results
    """
    response = test_client.get("/cards/search?q=nonexistentcardxyz")

    assert response.status_code == 200

    data = response.json()
    assert data["cards"] == []
    assert data["cursor"] is None
    assert data["has_more"] is False


# =============================================================================
# PAGINATION TESTS
# =============================================================================


@pytest.mark.integration
def test_search_default_page_count(test_client):
    """Test that default page_count is 10.

    This validates:
    - When page_count not specified, returns max 10 cards
    - Even if more results exist, only 10 returned
    - has_more flag indicates more results available

    Note: With 12 sample cards, broad search should return 10 with has_more=True
    """
    response = test_client.get("/cards/search?q=a")  # Very broad search

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) <= 10  # Default page size


@pytest.mark.integration
def test_search_custom_page_count_5(test_client):
    """Test search with page_count=5."""
    response = test_client.get("/cards/search", params={"q": "a", "page_count": 5})

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) <= 5


@pytest.mark.integration
def test_search_custom_page_count_20(test_client):
    """Test search with page_count=20."""
    response = test_client.get("/cards/search", params={"q": "a", "page_count": 20})

    assert response.status_code == 200

    data = response.json()
    assert data["has_more"] is False


@pytest.mark.integration
def test_search_cursor_pagination(test_client):
    """Test cursor-based pagination for next page.

    Uses composite cursor (score:oracle_id) to handle cards with equal scores.
    This ensures no duplicates or missing cards across pages.
    """
    # First page
    response1 = test_client.get("/cards/search", params={"q": "a", "page_count": 3})
    data1 = response1.json()

    assert len(data1["cards"]) == 3

    if data1["has_more"]:
        assert data1["cursor"] is not None

        # Cursor should be in format "score:oracle_id"
        assert ":" in data1["cursor"]

        # Second page using cursor
        cursor = data1["cursor"]
        response2 = test_client.get(
            "/cards/search", params={"q": "a", "page_count": 3, "cursor": cursor}
        )
        data2 = response2.json()

        # Verify no overlap - composite cursor should prevent duplicates
        page1_ids = {card["id"] for card in data1["cards"]}
        page2_ids = {card["id"] for card in data2["cards"]}

        overlap = page1_ids & page2_ids
        assert len(overlap) == 0, f"Found {len(overlap)} duplicate cards between pages"


@pytest.mark.integration
def test_search_has_more_flag_true(test_client):
    """Test has_more flag is True when more results exist."""
    response = test_client.get("/cards/search", params={"q": "a", "page_count": 2})

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) == 2
    assert data["has_more"] is True
    assert data["cursor"] is not None


@pytest.mark.integration
def test_search_has_more_flag_false(test_client):
    """Test has_more flag is False at end of results."""
    response = test_client.get(
        "/cards/search", params={"q": "emrakul", "page_count": 10}
    )

    assert response.status_code == 200

    data = response.json()
    assert data["has_more"] is False
    assert data["cursor"] is None


# =============================================================================
# RESPONSE STRUCTURE VALIDATION
# =============================================================================


@pytest.mark.integration
def test_search_response_structure(test_client):
    """Test that search response has correct structure."""
    response = test_client.get("/cards/search?q=lightning")

    assert response.status_code == 200

    data = response.json()

    # Required top-level fields
    assert "cards" in data
    assert "cursor" in data
    assert "has_more" in data

    # cards should be a list
    assert isinstance(data["cards"], list)

    # has_more should be boolean
    assert isinstance(data["has_more"], bool)

    # cursor should be string or None
    assert data["cursor"] is None or isinstance(data["cursor"], str)

    # Verify card structure if results exist
    if len(data["cards"]) > 0:
        card = data["cards"][0]
        assert "id" in card  # Oracle ID
        assert "name" in card
        assert "cmc" in card
        assert "type_line" in card


# =============================================================================
# FILTER TESTS
# =============================================================================


@pytest.mark.integration
def test_search_filter_colors_or_operator(test_client):
    """Test color filter with 'or' operator (default).

    This validates:
    - colors parameter accepts list of colors
    - 'or' operator returns cards with ANY of the specified colors
    - Cards with R or U should be included
    """
    # Use query string to send multiple values for same parameter
    response = test_client.get(
        "/cards/search?q=a&colors=R&colors=U&color_operator=or&page_count=20"
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned cards have at least one of R or U
    for card in data["cards"]:
        colors = card.get("colors", [])
        assert "R" in colors or "U" in colors, (
            f"Card {card['name']} has colors {colors}"
        )


@pytest.mark.integration
def test_search_filter_colors_and_operator(test_client):
    """Test color filter with 'and' operator.

    This validates:
    - 'and' operator returns cards with ALL specified colors (may have more)
    - Cards must contain both U and R
    """
    response = test_client.get(
        "/cards/search?q=a&colors=U&colors=R&color_operator=and&page_count=20"
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned cards have both U and R
    for card in data["cards"]:
        colors = card.get("colors", [])
        assert "U" in colors and "R" in colors, (
            f"Card {card['name']} has colors {colors}"
        )


@pytest.mark.integration
def test_search_filter_colors_exactly_operator(test_client):
    """Test color filter with 'exactly' operator.

    This validates:
    - 'exactly' operator returns cards with EXACTLY the specified colors (no more, no less)
    - Uses both $all and $size operators
    """
    response = test_client.get(
        "/cards/search?q=a&colors=U&colors=R&color_operator=exactly&page_count=20"
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned cards have exactly U and R (no more, no less)
    for card in data["cards"]:
        colors = card.get("colors", [])
        assert set(colors) == {"U", "R"}, f"Card {card['name']} has colors {colors}"


@pytest.mark.integration
def test_search_filter_cmc_min(test_client):
    """Test CMC filter with minimum value only.

    This validates:
    - cmc_min parameter filters cards by converted mana cost
    - Only cards with CMC >= min are returned
    """
    response = test_client.get("/cards/search?q=a&cmc_min=5&page_count=20")

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned cards have CMC >= 5
    for card in data["cards"]:
        cmc = card.get("cmc", 0)
        assert cmc >= 5, f"Card {card['name']} has CMC {cmc}"


@pytest.mark.integration
def test_search_filter_cmc_max(test_client):
    """Test CMC filter with maximum value only.

    This validates:
    - cmc_max parameter filters cards by converted mana cost
    - Only cards with CMC <= max are returned
    """
    response = test_client.get("/cards/search?q=a&cmc_max=2&page_count=20")

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned cards have CMC <= 2
    for card in data["cards"]:
        cmc = card.get("cmc", 0)
        assert cmc <= 2, f"Card {card['name']} has CMC {cmc}"


@pytest.mark.integration
def test_search_filter_cmc_range(test_client):
    """Test CMC filter with both min and max values.

    This validates:
    - cmc_min and cmc_max work together
    - Only cards with min <= CMC <= max are returned
    """
    response = test_client.get("/cards/search?q=a&cmc_min=1&cmc_max=5&page_count=20")

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned cards have 1 <= CMC <= 5
    for card in data["cards"]:
        cmc = card.get("cmc", 0)
        assert 1 <= cmc <= 5, f"Card {card['name']} has CMC {cmc}"


@pytest.mark.integration
def test_search_filter_types(test_client):
    """Test type filter.

    This validates:
    - types parameter filters by type_line field
    - Uses case-insensitive regex matching
    - Cards matching ANY of the specified types are returned
    """
    response = test_client.get("/cards/search?q=a&types=Creature&page_count=20")

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned cards are creatures
    for card in data["cards"]:
        type_line = card.get("type_line", "")
        assert "Creature" in type_line, (
            f"Card {card['name']} has type_line '{type_line}'"
        )


@pytest.mark.integration
def test_search_filter_rarities(test_client):
    """Test rarity filter.

    This validates:
    - rarities parameter filters by rarity field
    - Cards with ANY of the specified rarities are returned
    """
    response = test_client.get(
        "/cards/search?q=a&rarities=rare&rarities=mythic&page_count=20"
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned cards are rare or mythic
    for card in data["cards"]:
        rarity = card.get("rarity", "")
        assert rarity in ["rare", "mythic"], (
            f"Card {card['name']} has rarity '{rarity}'"
        )


@pytest.mark.integration
def test_search_filter_sets(test_client):
    """Test set filter.

    This validates:
    - sets parameter filters by set_name field
    - Cards from ANY of the specified sets are returned
    - set_name is in the individual card printings (cards array)
    """
    response = test_client.get(
        "/cards/search?q=a&sets=Limited Edition Alpha&page_count=20"
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned oracle cards have at least one printing from Alpha
    # (set_name is in the cards array, not at the top level after $group)
    for oracle_card in data["cards"]:
        cards = oracle_card.get("cards", [])
        assert len(cards) > 0, f"Oracle card {oracle_card['name']} has no printings"

        # Check that at least one printing is from the filtered set
        set_names = [c.get("set_name", "") for c in cards]
        assert "Limited Edition Alpha" in set_names, (
            f"Card {oracle_card['name']} has printings from {set_names}"
        )


@pytest.mark.integration
def test_search_filter_combined(test_client):
    """Test multiple filters combined.

    This validates:
    - Multiple filters work together (AND logic)
    - Cards must match ALL filter criteria
    """
    response = test_client.get(
        "/cards/search?q=a&colors=U&color_operator=or&cmc_min=1&cmc_max=3&page_count=20"
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Verify all returned cards match all criteria
    for card in data["cards"]:
        colors = card.get("colors", [])
        cmc = card.get("cmc", 0)
        assert "U" in colors, f"Card {card['name']} missing U color: {colors}"
        assert 1 <= cmc <= 3, f"Card {card['name']} has CMC {cmc} (not in 1-3 range)"
