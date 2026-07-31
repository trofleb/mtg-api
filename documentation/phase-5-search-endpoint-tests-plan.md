# Phase 5: Cards Router Integration Tests - Search Endpoint

**Date**: 2025-11-16
**Phase**: 5 of 9
**Complexity**: High
**Estimated Effort**: 3-4 hours
**Dependencies**: Phase 1 (Test Infrastructure) must be complete

---

## Overview

Phase 5 implements comprehensive integration tests for the `/cards/search/{text}` endpoint, the most complex endpoint in the MTG API. This endpoint combines full-text search with multi-dimensional filtering (colors, CMC, types, rarities, sets), cursor-based pagination, and MongoDB aggregation pipelines.

**Why this phase is critical:**
- The search endpoint is the core feature of the MTG card API
- It has the most complex query logic with multiple filter combinations (2^6 = 64 possible combinations)
- Pagination logic using score-based cursors is non-trivial and error-prone
- The endpoint constructs dynamic MongoDB aggregation pipelines based on user filters
- Edge cases (colorless, five-color, CMC 0) require careful testing

---

## Current Implementation Analysis

### Endpoint Signature
```python
@router.get("/cards/search/{text}")
def search_card_by_text(
    text: str,
    collection: CardsCollection,
    lang: str = "en",
    cursor: Optional[str] = None,
    page_count=10,
    card_filter: Optional[CardFilter] = None,
)
```

### CardFilter Model
```python
class CardFilter(BaseModel):
    sets: Optional[list[str]] = None              # Filter by set names
    colors: Optional[list[str]] = None            # WUBRG filter
    color_operator: Optional[str] = "or"          # "or", "and", "exactly"
    cmc_min: Optional[int] = None                 # Minimum CMC
    cmc_max: Optional[int] = None                 # Maximum CMC
    types: Optional[list[str]] = None             # creature, instant, sorcery
    rarities: Optional[list[str]] = None          # common, uncommon, rare, mythic
```

### Aggregation Pipeline Flow

The endpoint builds a MongoDB aggregation pipeline with these stages:

1. **$match** - Text search + filters (sets, colors, CMC, types, rarities)
2. **$project** - Add text search score + card fields
3. **$group** - Aggregate by oracle_id (same card, different printings)
4. **$sort** - Sort by text search score (descending)
5. **$match** - Apply cursor pagination (score < cursor_value)
6. **$limit** - Return page_count + 1 (to determine has_more)

### Response Structure
```python
{
    "cards": [...],            # Array of card objects (max: page_count)
    "cursor": "0.85",          # Score of second-to-last card (for next page)
    "has_more": true           # True if len(results) > page_count
}
```

### Filter Logic Complexity

**Color Operator Variations:**
- `"or"` → `{"colors": {"$in": ["R", "G"]}}` - Contains ANY of these colors
- `"and"` → `{"colors": {"$all": ["R", "G"]}}` - Contains ALL of these colors
- `"exactly"` → `{"colors": {"$all": ["R", "G"], "$size": 2}}` - EXACTLY these colors

**CMC Range Variations:**
- `cmc_min` only → `{"cmc": {"$gte": 3}}`
- `cmc_max` only → `{"cmc": {"$lte": 5}}`
- Both → `{"cmc": {"$gte": 3, "$lte": 5}}`

**Type Matching:**
- Uses `$or` with regex patterns: `[{"type_line": {"$regex": "creature", "$options": "i"}}]`

---

## Mock MongoDB Enhancement Requirements

### Current MockMongoCollection Support

✅ **Already Supported:**
- `$match` stage
- `$project` stage
- `$group` stage (with $first, $sum, $max, $addToSet)
- `$sort` stage
- `$limit` stage
- `$text` operator (basic text search)
- `$in`, `$all`, `$gte`, `$lte` operators
- `$or`, `$and` logical operators

❌ **NOT Yet Supported:**
- `$size` operator for exact color matching (`color_operator="exactly"`)
- Text search score simulation (`{"$project": {"score": 1}}`)

### Required Enhancements

**1. Add `$size` operator support** (`tests/mocks/mongodb.py`)

Location: `MockMongoCollection._matches_query()` method

```python
elif operator == "$size":
    if not isinstance(field_value, list):
        return False
    if len(field_value) != value:
        return False
```

**2. Add text search score simulation** (`tests/mocks/mongodb.py`)

Location: `MockMongoCollection._execute_aggregation_stage()` method for `$project`

```python
# In $project stage execution
if stage_spec.get("score") == 1:
    # Add mock text search score (higher = better match)
    # Simulate scores: 1.0 for perfect match, 0.5-0.9 for partial matches
    for doc in documents:
        if "score" not in doc:
            doc["score"] = self._calculate_mock_score(doc, search_text)
```

**Why we need score simulation:**
- Pagination relies on score-based cursors (`cursor: "0.85"`)
- Tests must verify cursor pagination works correctly
- We need deterministic scores for reproducible tests

**Score Simulation Strategy:**
```python
def _calculate_mock_score(self, doc: dict, search_text: str) -> float:
    """Calculate mock text search score for testing.

    Returns:
        Score between 0.0 and 1.0 (higher = better match)
    """
    name = doc.get("name", "").lower()
    oracle_text = doc.get("oracle_text", "").lower()
    search = search_text.lower()

    # Perfect name match = 1.0
    if search == name:
        return 1.0

    # Name starts with search = 0.9
    if name.startswith(search):
        return 0.9

    # Search in name = 0.8
    if search in name:
        return 0.8

    # Search in oracle text = 0.6
    if search in oracle_text:
        return 0.6

    # Weak match = 0.3
    return 0.3
```

---

## Test Data Requirements

### Additional Sample Cards Needed

The current `tests/fixtures/sample_cards.py` has 7 cards, but we need more variety for comprehensive filter testing.

**Add these cards:**

```python
# Izzet Charm - Two-color (U/R) instant
IZZET_CHARM = {
    "id": "...",
    "oracle_id": "...",
    "name": "Izzet Charm",
    "name_search": "izzet charm",
    "lang": "en",
    "released_at": "2012-10-05",
    "layout": "normal",
    "cmc": 2.0,
    "type_line": "Instant",
    "oracle_text": "Choose one — • Counter target noncreature spell unless its controller pays {2}. • Izzet Charm deals 2 damage to target creature. • Draw two cards, then discard two cards.",
    "mana_cost": "{U}{R}",
    "colors": ["U", "R"],
    "color_identity": ["U", "R"],
    "rarity": "uncommon",
    "set_name": "Return to Ravnica",
    "set": "rtr",
    "artist": "Zoltan Boros",
    # ... image_uris
}

# Giant Growth - Green instant, CMC 1
GIANT_GROWTH = {
    "id": "...",
    "oracle_id": "...",
    "name": "Giant Growth",
    "name_search": "giant growth",
    "lang": "en",
    "released_at": "1993-08-05",
    "layout": "normal",
    "cmc": 1.0,
    "type_line": "Instant",
    "oracle_text": "Target creature gets +3/+3 until end of turn.",
    "mana_cost": "{G}",
    "colors": ["G"],
    "color_identity": ["G"],
    "rarity": "common",
    "set_name": "Limited Edition Alpha",
    "set": "lea",
    # ... image_uris
}

# Serra Angel - White creature, CMC 5
SERRA_ANGEL = {
    "id": "...",
    "oracle_id": "...",
    "name": "Serra Angel",
    "name_search": "serra angel",
    "lang": "en",
    "released_at": "1993-08-05",
    "layout": "normal",
    "cmc": 5.0,
    "type_line": "Creature — Angel",
    "oracle_text": "Flying, vigilance",
    "mana_cost": "{3}{W}{W}",
    "colors": ["W"],
    "color_identity": ["W"],
    "power": "4",
    "toughness": "4",
    "rarity": "uncommon",
    "set_name": "Limited Edition Alpha",
    "set": "lea",
    # ... image_uris
}

# Doom Blade - Black instant, CMC 2
DOOM_BLADE = {
    "id": "...",
    "oracle_id": "...",
    "name": "Doom Blade",
    "name_search": "doom blade",
    "lang": "en",
    "released_at": "2010-07-16",
    "layout": "normal",
    "cmc": 2.0,
    "type_line": "Instant",
    "oracle_text": "Destroy target nonblack creature.",
    "mana_cost": "{1}{B}",
    "colors": ["B"],
    "color_identity": ["B"],
    "rarity": "common",
    "set_name": "Magic 2011",
    "set": "m11",
    # ... image_uris
}

# Emrakul, the Aeons Torn - Colorless creature, CMC 15
EMRAKUL = {
    "id": "...",
    "oracle_id": "...",
    "name": "Emrakul, the Aeons Torn",
    "name_search": "emrakul, the aeons torn",
    "lang": "en",
    "released_at": "2010-04-23",
    "layout": "normal",
    "cmc": 15.0,
    "type_line": "Legendary Creature — Eldrazi",
    "oracle_text": "Emrakul, the Aeons Torn can't be countered.\nWhen you cast this spell, take an extra turn after this one.\nFlying, protection from colored spells, annihilator 6\nWhen Emrakul is put into a graveyard from anywhere, its owner shuffles their graveyard into their library.",
    "mana_cost": "{15}",
    "colors": [],  # Colorless
    "color_identity": [],
    "power": "15",
    "toughness": "15",
    "rarity": "mythic",
    "set_name": "Rise of the Eldrazi",
    "set": "roe",
    # ... image_uris
}
```

**Why these cards:**
- **Izzet Charm**: Two-color card for "or"/"and" color operator testing
- **Giant Growth**: Green instant for multi-color filter combinations
- **Serra Angel**: White creature for type filtering (creature vs instant)
- **Doom Blade**: Black instant for complete WUBRG color coverage
- **Emrakul**: High CMC (15) colorless creature for edge case testing

**Updated test data coverage:**
- **Colors**: All WUBRG covered individually + multi-color cards
- **CMC Range**: 0, 1, 2, 5, 10, 15 (wide spectrum)
- **Types**: Instant, Creature, Artifact, Legendary
- **Rarities**: Common, Uncommon, Rare, Mythic (all covered)
- **Sets**: Multiple different sets for set filtering

---

## Test File Structure

### File: `tests/api/router/test_cards_search_integration.py`

**Organization:**
```python
"""Integration tests for Cards Search endpoint (/cards/search/{text}).

This module tests the most complex endpoint with:
- Full-text search functionality
- Cursor-based pagination
- Multi-dimensional filtering (colors, CMC, types, rarities, sets)
- MongoDB aggregation pipeline execution
- Edge cases and filter combinations

Test Categories:
1. Basic text search (lines 20-50)
2. Pagination tests (lines 52-150)
3. Filter tests - Individual (lines 152-400)
4. Filter tests - Combinations (lines 402-500)
5. Edge cases (lines 502-600)
"""

import pytest
from tests.fixtures.sample_cards import (
    LIGHTNING_BOLT,
    COUNTERSPELL,
    BLACK_LOTUS,
    PROGENITUS,
    DELVER_OF_SECRETS,
    SOL_RING,
    # New cards
    IZZET_CHARM,
    GIANT_GROWTH,
    SERRA_ANGEL,
    DOOM_BLADE,
    EMRAKUL,
)


# Test organization:
# - Mark all tests with @pytest.mark.integration
# - Group related tests together
# - Use descriptive docstrings with "Why" and "Expected"
# - Follow existing test pattern from test_cards_basic_integration.py
```

---

## Implementation Tasks (Detailed)

### Task 1: Enhance Mock MongoDB with $size Operator

**File**: `tests/mocks/mongodb.py`
**Lines**: 179-197 (in `_matches_query` method)

**What to update:**
Add `$size` operator support after the `$all` operator case:

```python
elif operator == "$all":
    if not isinstance(field_value, list):
        return False
    if not all(item in field_value for item in value):
        return False
elif operator == "$size":  # NEW
    if not isinstance(field_value, list):
        return False
    if len(field_value) != value:
        return False
```

**Why:**
- The `color_operator="exactly"` filter uses `{"colors": {"$all": [...], "$size": n}}`
- Without `$size` support, tests for exact color matching will fail
- This is a MongoDB standard operator that should be supported

**Test this change:**
```python
# In tests/mocks/test_mongodb.py
def test_size_operator():
    """Test that $size operator filters arrays by exact length."""
    collection = MockMongoCollection([
        {"colors": ["R", "G"]},
        {"colors": ["R"]},
        {"colors": []},
    ])

    results = list(collection.find({"colors": {"$size": 2}}))
    assert len(results) == 1
    assert results[0]["colors"] == ["R", "G"]
```

---

### Task 2: Enhance Mock MongoDB with Text Search Score

**File**: `tests/mocks/mongodb.py`
**Location**: Add new method + modify `_execute_aggregation_stage`

**What to update:**

1. **Add score calculation method** (after `_execute_group_stage`):

```python
def _calculate_text_score(self, doc: dict, search_text: str) -> float:
    """Calculate mock text search score for pagination testing.

    Simulates MongoDB $text search score based on text relevance.
    Higher scores indicate better matches.

    Args:
        doc: Document to score
        search_text: Search query text

    Returns:
        Score between 0.0 and 1.0
    """
    if not search_text:
        return 0.5  # Default score

    name = doc.get("name", "").lower()
    oracle_text = doc.get("oracle_text", "").lower()
    search = search_text.lower()

    # Scoring rules (deterministic for testing):
    if search == name:
        return 1.0  # Perfect match
    elif name.startswith(search):
        return 0.9  # Prefix match
    elif search in name:
        return 0.8  # Substring match in name
    elif search in oracle_text:
        return 0.6  # Match in card text
    else:
        return 0.3  # Weak/generic match
```

2. **Store search text in collection** (add to `__init__`):

```python
def __init__(self, documents: list[dict]):
    """Initialize collection with documents."""
    self._documents = deepcopy(documents)
    self._last_search_text = None  # NEW: Track last text search
```

3. **Capture search text during $match** (in `_matches_query`):

```python
elif field == "$text":
    # Text search - simple implementation
    search_text = condition.get("$search", "").lower()
    self._last_search_text = search_text  # NEW: Save for scoring
    doc_text = str(doc).lower()
    if search_text not in doc_text:
        return False
```

4. **Add score to $project stage** (in `_execute_aggregation_stage`):

```python
elif stage_type == "$project":
    # Project fields
    projected = []
    for doc in documents:
        projected_doc = self._apply_projection(doc, stage_spec)

        # NEW: Add text search score if requested
        if stage_spec.get("score") == 1 and self._last_search_text:
            projected_doc["score"] = self._calculate_text_score(
                doc, self._last_search_text
            )

        projected.append(projected_doc)
    return projected
```

5. **Update $group to handle score field**:

```python
# In _execute_group_stage, add after $addToSet case:
elif acc_type == "$max":
    field_name = (
        acc_value[1:] if acc_value.startswith("$") else acc_value
    )
    current_value = doc.get(field_name)
    if current_value is not None:
        if (
            field not in groups[key]
            or current_value > groups[key][field]
        ):
            groups[key][field] = current_value
```

**Why:**
- Cursor-based pagination uses `score < cursor_value` for "next page" queries
- Without score simulation, we cannot test pagination logic
- Deterministic scoring ensures reproducible tests

**Test this change:**
```python
# In tests/mocks/test_mongodb.py
def test_text_search_score_in_aggregation():
    """Test that text search score is added to projection."""
    collection = MockMongoCollection([
        {"name": "Lightning Bolt", "oracle_text": "deals 3 damage"},
        {"name": "Counterspell", "oracle_text": "counter target spell"},
    ])

    pipeline = [
        {"$match": {"$text": {"$search": "lightning"}}},
        {"$project": {"score": 1, "name": 1}},
    ]

    results = list(collection.aggregate(pipeline))
    assert len(results) > 0
    assert "score" in results[0]
    assert results[0]["score"] > 0.0
```

---

### Task 3: Add New Sample Cards to Fixtures

**File**: `tests/fixtures/sample_cards.py`
**Lines**: After SOL_RING definition (line 247)

**What to add:**
Add 5 new card definitions (see "Test Data Requirements" section above):
1. IZZET_CHARM
2. GIANT_GROWTH
3. SERRA_ANGEL
4. DOOM_BLADE
5. EMRAKUL

**Update `get_all_sample_cards()`:**
```python
def get_all_sample_cards() -> list[dict]:
    """Get all sample cards as a list."""
    return [
        LIGHTNING_BOLT,
        LIGHTNING_BOLT_REPRINT,
        COUNTERSPELL,
        BLACK_LOTUS,
        PROGENITUS,
        DELVER_OF_SECRETS,
        SOL_RING,
        IZZET_CHARM,        # NEW
        GIANT_GROWTH,       # NEW
        SERRA_ANGEL,        # NEW
        DOOM_BLADE,         # NEW
        EMRAKUL,            # NEW
    ]
```

**Why:**
- Need complete WUBRG color coverage for filter tests
- Need variety of CMC values (0, 1, 2, 5, 10, 15)
- Need mix of creatures and instants for type filtering
- Need multiple sets for set filter testing

**Test this change:**
Run existing fixture tests to ensure no regressions:
```bash
pytest tests/fixtures/test_sample_cards.py -v
```

---

### Task 4-7: Basic Text Search Tests

**File**: `tests/api/router/test_cards_search_integration.py` (NEW)
**Lines**: 1-150

**Test 4.1: Basic text search without filters**

```python
@pytest.mark.integration
def test_search_basic_text_query(test_client):
    """Test /cards/search/{text} with basic text query (no filters).

    This validates:
    - Endpoint returns HTTP 200
    - MongoDB $text search is executed
    - Results are aggregated by oracle_id
    - Response structure matches expected format
    - Text search matches card name and oracle_text

    Search: "lightning"
    Expected: Lightning Bolt (matches name)
    """
    response = test_client.get("/cards/search/lightning")

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
    Expected: Lightning Bolt ("deals 3 damage")
    """
    response = test_client.get("/cards/search/damage")

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # Lightning Bolt has "deals 3 damage" in oracle_text
    card_names = [card["name"] for card in data["cards"]]
    assert "Lightning Bolt" in card_names
```

**Test 4.2: Empty results**

```python
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
    response = test_client.get("/cards/search/nonexistentcardxyz")

    assert response.status_code == 200

    data = response.json()
    assert data["cards"] == []
    assert data["cursor"] is None
    assert data["has_more"] is False
```

**Why these tests:**
- Validate basic endpoint functionality works
- Ensure response structure is correct
- Test both success and empty result cases

---

### Task 8-11: Pagination Tests

**Lines**: 152-280

**Test 8.1: Default page size (10)**

```python
@pytest.mark.integration
def test_search_default_page_count(test_client):
    """Test that default page_count is 10.

    This validates:
    - When page_count not specified, returns max 10 cards
    - Even if more results exist, only 10 returned
    - has_more flag indicates more results available

    Note: With 12 sample cards, should return 10 with has_more=True
    """
    response = test_client.get("/cards/search/a")  # Very broad search

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) <= 10  # Default page size
```

**Test 8.2: Custom page_count parameter**

```python
@pytest.mark.integration
def test_search_custom_page_count_5(test_client):
    """Test search with page_count=5.

    This validates:
    - page_count parameter controls result count
    - Returns max 5 cards when page_count=5

    Search: "a" (broad search)
    Page count: 5
    Expected: 5 cards max
    """
    response = test_client.get("/cards/search/a?page_count=5")

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) <= 5


@pytest.mark.integration
def test_search_custom_page_count_20(test_client):
    """Test search with page_count=20.

    This validates:
    - Large page_count values work correctly
    - With 12 sample cards, returns all cards (no pagination)

    Search: "a" (broad search)
    Page count: 20
    Expected: All matching cards (< 20)
    """
    response = test_client.get("/cards/search/a?page_count=20")

    assert response.status_code == 200

    data = response.json()
    # Should return all matching cards since page_count > total cards
    assert data["has_more"] is False
```

**Test 8.3: Cursor-based pagination**

```python
@pytest.mark.integration
def test_search_cursor_pagination(test_client):
    """Test cursor-based pagination for next page.

    This validates:
    - First request returns cursor value
    - Second request with cursor returns next page
    - Cursor is based on text search score
    - No duplicate cards between pages

    Flow:
    1. Get first page (page_count=3)
    2. Use cursor from first page to get second page
    3. Verify no overlap between pages
    """
    # First page
    response1 = test_client.get("/cards/search/a?page_count=3")
    data1 = response1.json()

    assert len(data1["cards"]) == 3
    assert data1["cursor"] is not None  # Has next page

    # Second page using cursor
    cursor = data1["cursor"]
    response2 = test_client.get(f"/cards/search/a?page_count=3&cursor={cursor}")
    data2 = response2.json()

    # Verify no overlap
    page1_ids = {card["_id"] for card in data1["cards"]}
    page2_ids = {card["_id"] for card in data2["cards"]}
    assert page1_ids.isdisjoint(page2_ids)  # No duplicates


@pytest.mark.integration
def test_search_has_more_flag_true(test_client):
    """Test has_more flag is True when more results exist.

    This validates:
    - has_more=True when results exceed page_count
    - Fetches page_count+1 results internally
    - Only returns page_count results to client

    Search: "a" (broad search for many results)
    Page count: 2
    Expected: has_more=True (12 sample cards > 2)
    """
    response = test_client.get("/cards/search/a?page_count=2")

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) == 2
    assert data["has_more"] is True
    assert data["cursor"] is not None


@pytest.mark.integration
def test_search_has_more_flag_false(test_client):
    """Test has_more flag is False at end of results.

    This validates:
    - has_more=False when no more results exist
    - cursor=None when on last page

    Search: Very specific search with 1-2 results
    Page count: 10 (larger than result count)
    Expected: has_more=False, cursor=None
    """
    response = test_client.get("/cards/search/emrakul?page_count=10")

    assert response.status_code == 200

    data = response.json()
    # Only 1 Emrakul card exists
    assert data["has_more"] is False
    assert data["cursor"] is None
```

**Why these tests:**
- Pagination is complex and error-prone
- Cursor logic must be verified thoroughly
- has_more flag is critical for UI "load more" buttons
- Edge cases (first page, last page, exact page boundary)

---

### Task 12-18: Filter Tests - Individual Filters

**Lines**: 282-500

**Test 12.1: Sets filter (single set)**

```python
@pytest.mark.integration
def test_search_filter_single_set(test_client):
    """Test search with sets filter (single set).

    This validates:
    - CardFilter.sets parameter filters by set_name
    - MongoDB $in operator works correctly
    - Only cards from specified set are returned

    Search: "bolt"
    Filter: sets=["Limited Edition Alpha"]
    Expected: Lightning Bolt from LEA (not Double Masters reprint)
    """
    response = test_client.get(
        "/cards/search/bolt",
        params={"card_filter": {"sets": ["Limited Edition Alpha"]}}
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["cards"]) > 0

    # All cards should be from Limited Edition Alpha
    for card in data["cards"]:
        # Note: Aggregation groups by oracle_id, so check cards array
        assert all(c["set_name"] == "Limited Edition Alpha"
                   for c in card["cards"])


@pytest.mark.integration
def test_search_filter_multiple_sets(test_client):
    """Test search with sets filter (multiple sets).

    This validates:
    - Multiple set names in sets array work correctly
    - $in operator with multiple values

    Search: "bolt"
    Filter: sets=["Limited Edition Alpha", "Double Masters"]
    Expected: Both Lightning Bolt printings
    """
    response = test_client.get(
        "/cards/search/bolt",
        params={
            "card_filter": {
                "sets": ["Limited Edition Alpha", "Double Masters"]
            }
        }
    )

    assert response.status_code == 200

    data = response.json()
    # Should find Lightning Bolt with printings from both sets
    assert len(data["cards"]) > 0
```

**Test 12.2: Colors filter with "or" operator**

```python
@pytest.mark.integration
def test_search_filter_colors_or_operator(test_client):
    """Test search with colors filter using 'or' operator.

    This validates:
    - CardFilter.colors with color_operator="or" (default)
    - MongoDB $in operator for colors field
    - Returns cards with ANY of the specified colors

    Search: "a" (broad search)
    Filter: colors=["R", "U"], operator="or"
    Expected: Lightning Bolt (R), Counterspell (U), Izzet Charm (U+R)
    """
    response = test_client.get(
        "/cards/search/a",
        params={
            "card_filter": {
                "colors": ["R", "U"],
                "color_operator": "or"
            }
        }
    )

    assert response.status_code == 200

    data = response.json()
    card_names = [card["name"] for card in data["cards"]]

    # Should include red cards
    assert "Lightning Bolt" in card_names
    # Should include blue cards
    assert "Counterspell" in card_names
    # Should NOT include green-only cards
    assert "Giant Growth" not in card_names


@pytest.mark.integration
def test_search_filter_colors_and_operator(test_client):
    """Test search with colors filter using 'and' operator.

    This validates:
    - CardFilter.colors with color_operator="and"
    - MongoDB $all operator for colors field
    - Returns only cards containing ALL specified colors

    Search: "a" (broad search)
    Filter: colors=["U", "R"], operator="and"
    Expected: Only Izzet Charm (has both U and R)
    """
    response = test_client.get(
        "/cards/search/a",
        params={
            "card_filter": {
                "colors": ["U", "R"],
                "color_operator": "and"
            }
        }
    )

    assert response.status_code == 200

    data = response.json()
    card_names = [card["name"] for card in data["cards"]]

    # Should include cards with BOTH U and R
    assert "Izzet Charm" in card_names

    # Should NOT include cards with only R
    assert "Lightning Bolt" not in card_names
    # Should NOT include cards with only U
    assert "Counterspell" not in card_names


@pytest.mark.integration
def test_search_filter_colors_exactly_operator(test_client):
    """Test search with colors filter using 'exactly' operator.

    This validates:
    - CardFilter.colors with color_operator="exactly"
    - MongoDB $all + $size operators for exact color match
    - Returns only cards with EXACTLY these colors (no more, no less)

    Search: "a" (broad search)
    Filter: colors=["U", "R"], operator="exactly"
    Expected: Only Izzet Charm (exactly U+R, not Progenitus with WUBRG)
    """
    response = test_client.get(
        "/cards/search/a",
        params={
            "card_filter": {
                "colors": ["U", "R"],
                "color_operator": "exactly"
            }
        }
    )

    assert response.status_code == 200

    data = response.json()
    card_names = [card["name"] for card in data["cards"]]

    # Should include Izzet Charm (exactly U+R)
    assert "Izzet Charm" in card_names

    # Should NOT include mono-colored cards
    assert "Lightning Bolt" not in card_names
    assert "Counterspell" not in card_names

    # Should NOT include cards with more than 2 colors
    assert "Progenitus" not in card_names  # Has all 5 colors
```

**Test 12.3: CMC filters**

```python
@pytest.mark.integration
def test_search_filter_cmc_min_only(test_client):
    """Test search with cmc_min filter only.

    This validates:
    - CardFilter.cmc_min parameter
    - MongoDB $gte operator
    - Returns cards with CMC >= min value

    Search: "a" (broad search)
    Filter: cmc_min=5
    Expected: Serra Angel (5), Progenitus (10), Emrakul (15)
    NOT: Lightning Bolt (1), Counterspell (2)
    """
    response = test_client.get(
        "/cards/search/a",
        params={"card_filter": {"cmc_min": 5}}
    )

    assert response.status_code == 200

    data = response.json()

    # All cards should have CMC >= 5
    for card in data["cards"]:
        assert card["cmc"] >= 5


@pytest.mark.integration
def test_search_filter_cmc_max_only(test_client):
    """Test search with cmc_max filter only.

    This validates:
    - CardFilter.cmc_max parameter
    - MongoDB $lte operator
    - Returns cards with CMC <= max value

    Search: "a" (broad search)
    Filter: cmc_max=2
    Expected: Black Lotus (0), Lightning Bolt (1), Counterspell (2)
    NOT: Serra Angel (5), Progenitus (10)
    """
    response = test_client.get(
        "/cards/search/a",
        params={"card_filter": {"cmc_max": 2}}
    )

    assert response.status_code == 200

    data = response.json()

    # All cards should have CMC <= 2
    for card in data["cards"]:
        assert card["cmc"] <= 2


@pytest.mark.integration
def test_search_filter_cmc_range(test_client):
    """Test search with both cmc_min and cmc_max (range).

    This validates:
    - Both cmc_min and cmc_max work together
    - MongoDB $gte and $lte operators combined
    - Returns cards within CMC range

    Search: "a" (broad search)
    Filter: cmc_min=1, cmc_max=5
    Expected: Lightning Bolt (1), Counterspell (2), Serra Angel (5)
    NOT: Black Lotus (0), Progenitus (10), Emrakul (15)
    """
    response = test_client.get(
        "/cards/search/a",
        params={"card_filter": {"cmc_min": 1, "cmc_max": 5}}
    )

    assert response.status_code == 200

    data = response.json()

    # All cards should have 1 <= CMC <= 5
    for card in data["cards"]:
        assert 1 <= card["cmc"] <= 5
```

**Test 12.4: Types filter**

```python
@pytest.mark.integration
def test_search_filter_types_single(test_client):
    """Test search with types filter (single type).

    This validates:
    - CardFilter.types parameter
    - MongoDB regex pattern matching on type_line
    - Case-insensitive type matching

    Search: "a" (broad search)
    Filter: types=["Creature"]
    Expected: Serra Angel, Progenitus, Delver, Emrakul
    NOT: Lightning Bolt (Instant), Black Lotus (Artifact)
    """
    response = test_client.get(
        "/cards/search/a",
        params={"card_filter": {"types": ["Creature"]}}
    )

    assert response.status_code == 200

    data = response.json()

    # All cards should have "Creature" in type_line
    for card in data["cards"]:
        assert "creature" in card["type_line"].lower()


@pytest.mark.integration
def test_search_filter_types_multiple(test_client):
    """Test search with types filter (multiple types).

    This validates:
    - Multiple types in array work with $or logic
    - Returns cards matching ANY of the types

    Search: "a" (broad search)
    Filter: types=["Instant", "Artifact"]
    Expected: Lightning Bolt (Instant), Black Lotus (Artifact), Sol Ring (Artifact)
    NOT: Serra Angel (Creature)
    """
    response = test_client.get(
        "/cards/search/a",
        params={"card_filter": {"types": ["Instant", "Artifact"]}}
    )

    assert response.status_code == 200

    data = response.json()
    card_names = [card["name"] for card in data["cards"]]

    # Should include Instants
    assert "Lightning Bolt" in card_names
    # Should include Artifacts
    assert "Black Lotus" in card_names or "Sol Ring" in card_names

    # Should NOT include pure creatures
    # (Note: Some cards might be "Artifact Creature" - that's OK)
```

**Test 12.5: Rarities filter**

```python
@pytest.mark.integration
def test_search_filter_rarities_single(test_client):
    """Test search with rarities filter (single rarity).

    This validates:
    - CardFilter.rarities parameter
    - MongoDB $in operator for rarity field
    - Returns only cards of specified rarity

    Search: "a" (broad search)
    Filter: rarities=["mythic"]
    Expected: Progenitus (mythic), Emrakul (mythic)
    NOT: Lightning Bolt (common), Counterspell (uncommon)
    """
    response = test_client.get(
        "/cards/search/a",
        params={"card_filter": {"rarities": ["mythic"]}}
    )

    assert response.status_code == 200

    data = response.json()

    # All cards should be mythic rarity
    for card in data["cards"]:
        assert card["rarity"] == "mythic"


@pytest.mark.integration
def test_search_filter_rarities_multiple(test_client):
    """Test search with rarities filter (multiple rarities).

    This validates:
    - Multiple rarities in array work correctly
    - $in operator with multiple values

    Search: "a" (broad search)
    Filter: rarities=["common", "uncommon"]
    Expected: Lightning Bolt (common), Counterspell (uncommon)
    NOT: Black Lotus (rare), Progenitus (mythic)
    """
    response = test_client.get(
        "/cards/search/a",
        params={"card_filter": {"rarities": ["common", "uncommon"]}}
    )

    assert response.status_code == 200

    data = response.json()

    # All cards should be common or uncommon
    for card in data["cards"]:
        assert card["rarity"] in ["common", "uncommon"]
```

**Why these tests:**
- Each filter dimension must be tested individually
- Validates MongoDB query operators ($in, $all, $size, $gte, $lte, $regex)
- Ensures filter logic matches endpoint specification

---

### Task 19: Combined Filters Test

**Lines**: 502-600

```python
@pytest.mark.integration
def test_search_all_filters_combined(test_client):
    """Test search with ALL filters applied simultaneously.

    This is the most complex test case, validating that:
    - All filters work together in one query
    - MongoDB aggregation pipeline combines all match conditions
    - No filter interference or conflicts
    - Correct boolean logic (AND between different filter types)

    Search: "a" (broad search)
    Filters:
    - sets: ["Limited Edition Alpha", "Magic 2011"]
    - colors: ["R", "U", "B"], operator="or"
    - cmc_min: 1, cmc_max: 3
    - types: ["Instant"]
    - rarities: ["common", "uncommon"]

    Expected: Only cards matching ALL criteria
    """
    response = test_client.get(
        "/cards/search/a",
        params={
            "card_filter": {
                "sets": ["Limited Edition Alpha", "Magic 2011"],
                "colors": ["R", "U", "B"],
                "color_operator": "or",
                "cmc_min": 1,
                "cmc_max": 3,
                "types": ["Instant"],
                "rarities": ["common", "uncommon"]
            }
        }
    )

    assert response.status_code == 200

    data = response.json()

    # Verify each filter is applied
    for card in data["cards"]:
        # Set filter
        assert any(c["set_name"] in ["Limited Edition Alpha", "Magic 2011"]
                   for c in card["cards"])

        # Color filter (any of R, U, B)
        assert any(color in card["colors"] for color in ["R", "U", "B"])

        # CMC range
        assert 1 <= card["cmc"] <= 3

        # Type filter
        assert "instant" in card["type_line"].lower()

        # Rarity filter
        assert card["rarity"] in ["common", "uncommon"]


@pytest.mark.integration
def test_search_filters_narrow_results(test_client):
    """Test that combining filters narrows results correctly.

    This validates:
    - More filters = fewer results (logical AND)
    - Each added filter reduces result count

    Flow:
    1. Search with no filters → N results
    2. Add color filter → M results (M <= N)
    3. Add CMC filter → K results (K <= M)
    """
    # No filters
    response1 = test_client.get("/cards/search/a")
    count1 = len(response1.json()["cards"])

    # Add color filter
    response2 = test_client.get(
        "/cards/search/a",
        params={"card_filter": {"colors": ["R"]}}
    )
    count2 = len(response2.json()["cards"])

    # Add CMC filter on top of color filter
    response3 = test_client.get(
        "/cards/search/a",
        params={"card_filter": {"colors": ["R"], "cmc_max": 2}}
    )
    count3 = len(response3.json()["cards"])

    # Each filter should reduce or maintain count (never increase)
    assert count2 <= count1
    assert count3 <= count2
```

**Why this test:**
- Most realistic user scenario (multiple filters at once)
- Validates complex MongoDB aggregation pipeline
- Ensures filters don't interfere with each other

---

## Acceptance Criteria

### Functional Requirements

✅ **Basic Search:**
- [ ] Text search matches card name and oracle_text
- [ ] Empty search query returns valid response
- [ ] No results return empty array with has_more=False

✅ **Pagination:**
- [ ] Default page size is 10 cards
- [ ] Custom page_count parameter works (tested with 5, 20)
- [ ] Cursor-based pagination returns next page correctly
- [ ] No duplicate cards across pages
- [ ] has_more flag is True when more results exist
- [ ] has_more flag is False on last page
- [ ] cursor is None when no more results

✅ **Filters - Individual:**
- [ ] Sets filter works with single set
- [ ] Sets filter works with multiple sets
- [ ] Colors filter with "or" operator ($in)
- [ ] Colors filter with "and" operator ($all)
- [ ] Colors filter with "exactly" operator ($all + $size)
- [ ] CMC min filter ($gte)
- [ ] CMC max filter ($lte)
- [ ] CMC range filter (min + max)
- [ ] Types filter with single type (regex)
- [ ] Types filter with multiple types ($or)
- [ ] Rarities filter with single rarity
- [ ] Rarities filter with multiple rarities

✅ **Filters - Combined:**
- [ ] All filters work together simultaneously
- [ ] Combining filters narrows results (logical AND)
- [ ] No filter interference or conflicts

✅ **Response Structure:**
- [ ] Response includes "cards" array
- [ ] Response includes "cursor" string or null
- [ ] Response includes "has_more" boolean
- [ ] Cards are grouped by oracle_id
- [ ] Aggregated cards include all required fields

### Technical Requirements

✅ **Mock MongoDB Enhancements:**
- [ ] `$size` operator implemented and tested
- [ ] Text search score simulation implemented
- [ ] Score added to $project stage
- [ ] Score used in $group $max accumulator
- [ ] Score-based cursor filtering works

✅ **Test Data:**
- [ ] 5 new sample cards added to fixtures
- [ ] Complete WUBRG color coverage
- [ ] CMC range 0-15 covered
- [ ] All rarities represented
- [ ] Multiple sets available
- [ ] Mix of creatures, instants, artifacts

✅ **Code Quality:**
- [ ] All tests marked with `@pytest.mark.integration`
- [ ] Descriptive docstrings with "Why" and "Expected"
- [ ] Clear assertions with helpful messages
- [ ] No hardcoded values (use constants from fixtures)
- [ ] Tests are independent and can run in any order

✅ **Test Execution:**
- [ ] All tests pass: `pytest tests/api/router/test_cards_search_integration.py -v`
- [ ] Integration marker works: `pytest -m integration`
- [ ] Tests run in under 2 seconds
- [ ] No test flakiness (100% reproducible)

### Coverage Requirements

✅ **Test Coverage:**
- [ ] Minimum 14 test functions
- [ ] All CardFilter parameters tested
- [ ] All color_operator values tested
- [ ] Pagination edge cases covered
- [ ] Empty results handled
- [ ] Combined filters tested

---

## Test Execution Plan

### Step 1: Run Mock MongoDB Tests
```bash
# Verify mock enhancements work
pytest tests/mocks/test_mongodb.py::test_size_operator -v
pytest tests/mocks/test_mongodb.py::test_text_search_score -v
```

### Step 2: Run Fixture Tests
```bash
# Verify new sample cards are loaded
pytest tests/fixtures/test_sample_cards.py -v
```

### Step 3: Run Search Integration Tests
```bash
# Run all search endpoint tests
pytest tests/api/router/test_cards_search_integration.py -v

# Run specific test category
pytest tests/api/router/test_cards_search_integration.py::test_search_basic_text_query -v
pytest tests/api/router/test_cards_search_integration.py::test_search_cursor_pagination -v
pytest tests/api/router/test_cards_search_integration.py::test_search_all_filters_combined -v
```

### Step 4: Run All Integration Tests
```bash
# Ensure no regressions in other phases
pytest -m integration -v
```

### Step 5: Check Coverage
```bash
# Verify code coverage for cards router
pytest tests/api/router/test_cards_search_integration.py --cov=api/router/cards --cov-report=term-missing
```

**Expected coverage:** 95%+ for search_card_by_text function

---

## Common Issues and Solutions

### Issue 1: FastAPI Query Parameter Parsing

**Problem:** CardFilter is a Pydantic model, but query parameters are flat strings.

**Solution:** Use FastAPI's dependency injection with `Query` or pass JSON in request body:

```python
# Option 1: JSON body (recommended for complex filters)
response = test_client.post(
    "/cards/search/lightning",
    json={"card_filter": {"colors": ["R"], "cmc_max": 2}}
)

# Option 2: Nested query params (if endpoint supports it)
response = test_client.get(
    "/cards/search/lightning?card_filter.colors=R&card_filter.cmc_max=2"
)
```

**Action:** Check actual endpoint implementation to determine correct format.

### Issue 2: Mock Score Consistency

**Problem:** Text search scores must be consistent for pagination tests.

**Solution:** Use deterministic scoring algorithm (avoid random values):
- Same search + same document = same score
- Store scores in mock collection state
- Reset state between tests

### Issue 3: $size Operator with $all

**Problem:** Endpoint uses both `$all` and `$size` for "exactly" operator, but applies them separately.

**Actual code:**
```python
match_conditions["colors"] = {"$size": len(card_filter.colors)}
match_conditions["colors"] = {"$all": card_filter.colors}  # Overwrites $size!
```

**Bug in implementation!** This is a bug - second assignment overwrites the first.

**Correct implementation should be:**
```python
match_conditions["colors"] = {
    "$all": card_filter.colors,
    "$size": len(card_filter.colors)
}
```

**Action:** Document this bug and fix it before writing tests, or write a failing test to demonstrate the bug.

### Issue 4: Language Parameter

**Problem:** Tests should verify lang parameter is applied.

**Solution:** Add tests with lang="fr" (need French card in fixtures, or verify default lang="en").

---

## Estimated Timeline

| Task | Duration | Dependencies |
|------|----------|--------------|
| 1. Add $size operator | 15 min | None |
| 2. Add score simulation | 45 min | Task 1 |
| 3. Add 5 new sample cards | 30 min | None |
| 4-7. Basic search tests | 30 min | Tasks 2, 3 |
| 8-11. Pagination tests | 60 min | Task 2 |
| 12-18. Filter tests | 90 min | Tasks 1, 2, 3 |
| 19. Combined filters test | 30 min | Tasks 12-18 |
| Testing and debugging | 30 min | All tasks |

**Total: ~5 hours**

---

## Next Steps After Phase 5

After completing Phase 5, proceed to:
- **Phase 6**: Response Structure Validation Tests
- **Phase 7**: Edge Cases and Error Handling
- **Phase 8**: Test Utilities and Helpers (refactor existing tests)
- **Phase 9**: CI/CD Integration

Phase 5 is the most complex testing phase. Once complete, subsequent phases will be faster as the test infrastructure is fully mature.
