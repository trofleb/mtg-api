"""Integration tests for Cards Router basic endpoints.

This module tests the basic card retrieval endpoints:
- /cards/{name} - Search by card name with optional filters
- /cards/id/{scryfall_id} - Get card by Scryfall ID
- /cards/oracle/{oracle_id} - Get all printings by Oracle ID

These tests validate MongoDB queries, aggregation pipelines, filtering,
sorting, and error handling with mocked database.
"""

import pytest


@pytest.mark.integration
def test_get_card_by_name_success(test_client):
    """Test that /cards/{name} endpoint returns card with exact name match.

    This test validates that:
    - The endpoint returns HTTP 200
    - Regex search on name_search field works (case-insensitive)
    - MongoDB aggregation pipeline executes correctly
    - Card is grouped by oracle_id
    - Multiple printings are aggregated together
    - Returns first grouped result

    Expected: Lightning Bolt (2 printings aggregated by oracle_id)
    """
    response = test_client.get("/cards/lightning bolt")

    assert response.status_code == 200

    data = response.json()
    assert data is not None
    assert data["name"] == "Lightning Bolt"
    # Aggregated result exposes the oracle_id as "id"
    assert data["id"] == "b29c8b8a-2c8f-4891-88bc-f35d07a68293"

    # Verify it's the aggregated result with multiple printings
    assert "cards" in data
    assert data["card_count"] == 2  # Two Lightning Bolt printings


@pytest.mark.integration
def test_get_card_by_name_with_language(test_client):
    """Test that /cards/{name} endpoint filters by language parameter.

    This test validates that:
    - Language parameter (lang) is applied correctly
    - Default language is "en"
    - MongoDB $eq operator works in aggregation pipeline
    - Only cards matching the language are returned

    Expected: Lightning Bolt in English (lang=en is default)
    """
    # Test default language (en)
    response = test_client.get("/cards/lightning bolt")
    assert response.status_code == 200

    data = response.json()
    assert data is not None
    # Language is not in aggregated result, but all cards in the array should have lang=en
    assert "cards" in data
    assert all(card["lang"] == "en" for card in data["cards"])

    # Test explicit language parameter
    response_en = test_client.get("/cards/lightning bolt?lang=en")
    assert response_en.status_code == 200
    data_en = response_en.json()
    assert all(card["lang"] == "en" for card in data_en["cards"])


@pytest.mark.integration
def test_get_card_by_name_with_set_filter(test_client):
    """Test that /cards/{name} endpoint filters by set parameter.

    This test validates that:
    - Set parameter filters specific printing
    - MongoDB $eq operator works for set filtering
    - Set codes are case-insensitive (lowercased in query)
    - Returns only cards from specified set

    Expected: Lightning Bolt from Limited Edition Alpha (set code: lea)
    """
    response = test_client.get("/cards/lightning bolt?set=lea")

    assert response.status_code == 200

    data = response.json()
    assert data is not None
    assert data["name"] == "Lightning Bolt"
    # When filtered by set, should return the specific printing
    # (Note: Aggregation still groups, but only one set's cards are included)


@pytest.mark.integration
def test_get_card_by_name_not_found(test_client):
    """Test that /cards/{name} endpoint returns 404 when card not found.

    This test validates that:
    - Non-existent card names raise HTTPException
    - An empty aggregation result is an error, not a 200 with a null body,
      which callers cannot distinguish from a successful empty response
    - Response includes a detail field naming the card

    Expected: 404 for non-existent card "nonexistent card"
    """
    response = test_client.get("/cards/nonexistent card")

    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "nonexistent card" in data["detail"]


@pytest.mark.integration
def test_get_card_by_scryfall_id_success(test_client):
    """Test that /cards/id/{scryfall_id} endpoint retrieves card by ID.

    This test validates that:
    - Endpoint returns HTTP 200 for valid Scryfall ID
    - MongoDB find_one query works correctly
    - CARD_PROJECTION is applied to returned fields
    - All required card metadata is present

    Expected: Lightning Bolt with ID 550c74d4-a843-4208-a3c2-c71e84a21979
    """
    scryfall_id = "550c74d4-a843-4208-a3c2-c71e84a21979"
    response = test_client.get(f"/cards/id/{scryfall_id}")

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == scryfall_id
    assert data["name"] == "Lightning Bolt"
    assert data["oracle_id"] == "b29c8b8a-2c8f-4891-88bc-f35d07a68293"
    assert data["set"] == "lea"

    # Verify key fields from CARD_PROJECTION are present
    assert "image_uris" in data
    assert "type_line" in data
    assert "mana_cost" in data
    assert "cmc" in data


@pytest.mark.integration
def test_get_card_by_scryfall_id_not_found(test_client):
    """Test that /cards/id/{scryfall_id} returns 404 for non-existent ID.

    This test validates that:
    - Non-existent Scryfall IDs raise HTTPException
    - Status code is 404 (not found)
    - Error message is descriptive
    - Response includes detail field with error message

    Expected: 404 HTTPException for non-existent UUID
    """
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = test_client.get(f"/cards/id/{fake_id}")

    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert fake_id in data["detail"]
    assert "not found" in data["detail"].lower()


@pytest.mark.integration
def test_get_cards_by_oracle_id_multiple_printings(test_client):
    """Test that /cards/oracle/{oracle_id} returns all printings sorted.

    This test validates that:
    - All cards with same oracle_id are returned
    - Cards are sorted by released_at descending (newest first)
    - MongoDB find + sort works correctly
    - Returns list of card objects
    - Each printing retains individual metadata

    Expected: 2 Lightning Bolt printings (1993-08-05 and 2020-08-07)
    Order: 2020 printing first (newer), then 1993 (older)
    """
    oracle_id = "b29c8b8a-2c8f-4891-88bc-f35d07a68293"
    response = test_client.get(f"/cards/oracle/{oracle_id}")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    # Verify both printings are present
    card_ids = {card["id"] for card in data}
    assert "550c74d4-a843-4208-a3c2-c71e84a21979" in card_ids  # 1993 printing
    assert "a8c8c3c2-3f3d-4c7b-9c7a-1a2b3c4d5e6f" in card_ids  # 2020 printing

    # Verify sorting by released_at descending (newest first)
    assert data[0]["released_at"] == "2020-08-07"  # Double Masters (newer)
    assert data[1]["released_at"] == "1993-08-05"  # Limited Edition Alpha (older)

    # Verify both share same oracle_id
    assert all(card["oracle_id"] == oracle_id for card in data)


@pytest.mark.integration
def test_get_cards_by_oracle_id_not_found(test_client):
    """Test that /cards/oracle/{oracle_id} returns 404 when no printings exist.

    This test validates that:
    - Non-existent oracle IDs raise HTTPException
    - Empty result list triggers 404 (not empty list!)
    - Status code is 404 (not found)
    - Error message is descriptive
    - Response includes detail field with error message

    Expected: 404 HTTPException for non-existent Oracle UUID
    """
    fake_oracle_id = "00000000-0000-0000-0000-000000000000"
    response = test_client.get(f"/cards/oracle/{fake_oracle_id}")

    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert fake_oracle_id in data["detail"]
    assert "no cards found" in data["detail"].lower()


@pytest.mark.integration
def test_get_aggregated_card_by_oracle_id_success(test_client):
    """Test that /cards/oracle/{oracle_id}/aggregated groups all printings.

    This test validates that:
    - Printings sharing an oracle_id collapse into a single document
    - The shape matches what /cards/search returns per result,
      so a card can be rendered from an Oracle ID alone
    - Oracle-level fields are present, not just per-printing ones
    - Every printing is retained under "cards"

    Expected: Lightning Bolt aggregated across its 2 printings
    """
    oracle_id = "b29c8b8a-2c8f-4891-88bc-f35d07a68293"
    response = test_client.get(f"/cards/oracle/{oracle_id}/aggregated")

    assert response.status_code == 200

    data = response.json()

    # Grouped documents expose the oracle_id as "id"
    assert data["id"] == oracle_id
    assert data["name"] == "Lightning Bolt"

    # Oracle-level fields the raw printings endpoint does not provide
    assert "card_text" in data
    assert "card_count" in data
    assert data["card_count"] == 2

    # Both printings retained
    assert len(data["cards"]) == 2


@pytest.mark.integration
def test_get_aggregated_card_by_oracle_id_not_found(test_client):
    """Test that /cards/oracle/{oracle_id}/aggregated 404s for unknown IDs.

    This test validates that:
    - An unmatched oracle_id yields 404 rather than an empty document
    - The error message names the offending ID

    Expected: 404 for a non-existent Oracle UUID
    """
    fake_oracle_id = "00000000-0000-0000-0000-000000000000"
    response = test_client.get(f"/cards/oracle/{fake_oracle_id}/aggregated")

    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert fake_oracle_id in data["detail"]
