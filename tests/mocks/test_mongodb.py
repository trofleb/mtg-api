"""Tests for custom MongoDB mock classes.

This module tests MockMongoCursor and MockMongoCollection to ensure they
correctly simulate MongoDB operations for integration testing.
"""

from typing import Optional

import pytest

from tests.mocks.mongodb import MockMongoCollection, MockMongoCursor

# Sample test data
SAMPLE_CARDS = [
    {
        "id": "1",
        "name": "Lightning Bolt",
        "colors": ["R"],
        "cmc": 1.0,
        "rarity": "common",
        "set_name": "Alpha",
    },
    {
        "id": "2",
        "name": "Counterspell",
        "colors": ["U"],
        "cmc": 2.0,
        "rarity": "uncommon",
        "set_name": "Alpha",
    },
    {
        "id": "3",
        "name": "Black Lotus",
        "colors": [],
        "cmc": 0.0,
        "rarity": "rare",
        "set_name": "Alpha",
    },
    {
        "id": "4",
        "name": "Progenitus",
        "colors": ["W", "U", "B", "R", "G"],
        "cmc": 10.0,
        "rarity": "mythic",
        "set_name": "Conflux",
    },
]


@pytest.mark.unit
def test_cursor_iteration():
    """Test that MockMongoCursor can be iterated."""
    cursor = MockMongoCursor(SAMPLE_CARDS)
    cards = list(cursor)

    assert len(cards) == 4
    assert cards[0]["name"] == "Lightning Bolt"
    assert cards[3]["name"] == "Progenitus"


@pytest.mark.unit
def test_cursor_sort_ascending():
    """Test that MockMongoCursor.sort() works in ascending order."""
    cursor = MockMongoCursor(SAMPLE_CARDS)
    cursor.sort("cmc", 1)
    cards = list(cursor)

    assert cards[0]["cmc"] == 0.0
    assert cards[1]["cmc"] == 1.0
    assert cards[2]["cmc"] == 2.0
    assert cards[3]["cmc"] == 10.0


@pytest.mark.unit
def test_cursor_sort_descending():
    """Test that MockMongoCursor.sort() works in descending order."""
    cursor = MockMongoCursor(SAMPLE_CARDS)
    cursor.sort("cmc", -1)
    cards = list(cursor)

    assert cards[0]["cmc"] == 10.0
    assert cards[3]["cmc"] == 0.0


@pytest.mark.unit
def test_cursor_limit():
    """Test that MockMongoCursor.limit() restricts results."""
    cursor = MockMongoCursor(SAMPLE_CARDS)
    cursor.limit(2)
    cards = list(cursor)

    assert len(cards) == 2


@pytest.mark.unit
def test_cursor_sort_and_limit_chaining():
    """Test that sort and limit can be chained together."""
    cursor = MockMongoCursor(SAMPLE_CARDS)
    cursor.sort("cmc", -1).limit(2)
    cards = list(cursor)

    assert len(cards) == 2
    assert cards[0]["name"] == "Progenitus"
    assert cards[1]["name"] == "Counterspell"


@pytest.mark.unit
def test_find_one_exact_match():
    """Test find_one with exact field match."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    result = collection.find_one({"name": "Lightning Bolt"})

    assert result is not None
    assert result["name"] == "Lightning Bolt"
    assert result["cmc"] == 1.0


@pytest.mark.unit
def test_find_one_returns_none():
    """Test find_one returns None when no match found."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    result = collection.find_one({"name": "Nonexistent Card"})

    assert result is None


@pytest.mark.unit
def test_find_one_with_projection():
    """Test find_one with field projection."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    result = collection.find_one(
        {"name": "Lightning Bolt"}, projection={"name": 1, "cmc": 1, "_id": 0}
    )

    assert result is not None
    assert "name" in result
    assert "cmc" in result
    assert "_id" not in result
    assert "colors" not in result


@pytest.mark.unit
def test_find_with_regex():
    """Test find with $regex operator."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    cursor = collection.find({"name": {"$regex": "bolt"}})
    results = list(cursor)

    assert len(results) == 1
    assert results[0]["name"] == "Lightning Bolt"


@pytest.mark.unit
def test_find_with_in_operator():
    """Test find with $in operator."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    cursor = collection.find({"rarity": {"$in": ["rare", "mythic"]}})
    results = list(cursor)

    assert len(results) == 2
    rarities = [r["rarity"] for r in results]
    assert "rare" in rarities
    assert "mythic" in rarities


@pytest.mark.unit
def test_find_with_all_operator():
    """Test find with $all operator."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    cursor = collection.find({"colors": {"$all": ["W", "U"]}})
    results = list(cursor)

    assert len(results) == 1
    assert results[0]["name"] == "Progenitus"


@pytest.mark.unit
def test_find_with_gte_lte_operators():
    """Test find with $gte and $lte comparison operators."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    cursor = collection.find({"cmc": {"$gte": 1.0, "$lte": 2.0}})
    results = list(cursor)

    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "Lightning Bolt" in names
    assert "Counterspell" in names


@pytest.mark.unit
def test_aggregate_match_stage():
    """Test aggregate with $match stage."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    pipeline = [{"$match": {"cmc": {"$gte": 2.0}}}]
    cursor = collection.aggregate(pipeline)
    results = list(cursor)

    assert len(results) == 2
    assert all(r["cmc"] >= 2.0 for r in results)


@pytest.mark.unit
def test_aggregate_project_stage():
    """Test aggregate with $project stage."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    pipeline = [{"$project": {"name": 1, "cmc": 1, "_id": 0}}]
    cursor = collection.aggregate(pipeline)
    results = list(cursor)

    assert len(results) == 4
    assert all("name" in r for r in results)
    assert all("cmc" in r for r in results)
    assert all("colors" not in r for r in results)


@pytest.mark.unit
def test_aggregate_group_stage():
    """Test aggregate with $group stage."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    pipeline = [
        {
            "$group": {
                "_id": "$set_name",
                "count": {"$sum": 1},
                "max_cmc": {"$max": "$cmc"},
            }
        }
    ]
    cursor = collection.aggregate(pipeline)
    results = list(cursor)

    assert len(results) == 2  # Alpha and Conflux
    alpha_group = next((r for r in results if r["_id"] == "Alpha"), None)
    assert alpha_group is not None
    assert alpha_group["count"] == 3
    assert alpha_group["max_cmc"] == 2.0


@pytest.mark.unit
def test_aggregate_sort_stage():
    """Test aggregate with $sort stage."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    pipeline = [{"$sort": {"cmc": -1}}]
    cursor = collection.aggregate(pipeline)
    results = list(cursor)

    assert len(results) == 4
    assert results[0]["cmc"] == 10.0
    assert results[-1]["cmc"] == 0.0


@pytest.mark.unit
def test_aggregate_limit_stage():
    """Test aggregate with $limit stage."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    pipeline = [{"$sort": {"cmc": -1}}, {"$limit": 2}]
    cursor = collection.aggregate(pipeline)
    results = list(cursor)

    assert len(results) == 2
    assert results[0]["name"] == "Progenitus"


@pytest.mark.unit
def test_aggregate_complex_pipeline():
    """Test aggregate with multiple stages combined."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    pipeline = [
        {"$match": {"set_name": "Alpha"}},
        {"$project": {"name": 1, "cmc": 1, "_id": 0}},
        {"$sort": {"cmc": 1}},
        {"$limit": 2},
    ]
    cursor = collection.aggregate(pipeline)
    results = list(cursor)

    assert len(results) == 2
    assert results[0]["name"] == "Black Lotus"
    assert results[0]["cmc"] == 0.0
    assert results[1]["name"] == "Lightning Bolt"
    assert results[1]["cmc"] == 1.0
    assert "colors" not in results[0]


@pytest.mark.unit
def test_text_search():
    """Test find with $text and $search operators."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    cursor = collection.find({"$text": {"$search": "bolt"}})
    results = list(cursor)

    assert len(results) == 1
    assert results[0]["name"] == "Lightning Bolt"


@pytest.mark.unit
def test_exists_operator():
    """Test find with $exists operator."""
    # Add a card without colors field for this test
    cards_with_missing = SAMPLE_CARDS + [{"id": "5", "name": "Test Card", "cmc": 1.0}]
    collection = MockMongoCollection(cards_with_missing)

    # Find cards where colors exists
    cursor = collection.find({"colors": {"$exists": True}})
    results = list(cursor)
    assert len(results) == 4

    # Find cards where colors doesn't exist
    cursor = collection.find({"colors": {"$exists": False}})
    results = list(cursor)
    assert len(results) == 1
    assert results[0]["name"] == "Test Card"


@pytest.mark.unit
def test_or_operator():
    """Test find with $or operator."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    cursor = collection.find({"$or": [{"cmc": 0.0}, {"rarity": "mythic"}]})
    results = list(cursor)

    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "Black Lotus" in names
    assert "Progenitus" in names


@pytest.mark.unit
def test_and_operator():
    """Test find with $and operator."""
    collection = MockMongoCollection(SAMPLE_CARDS)
    cursor = collection.find({"$and": [{"cmc": {"$gte": 1.0}}, {"cmc": {"$lte": 2.0}}]})
    results = list(cursor)

    assert len(results) == 2
    assert all(1.0 <= r["cmc"] <= 2.0 for r in results)


@pytest.mark.unit
def test_size_operator():
    """Test find with $size operator for exact array length matching.

    This validates:
    - $size operator filters arrays by exact length
    - Works correctly for empty arrays (size=0)
    - Works correctly for multi-element arrays
    - Returns no matches when size doesn't match
    """
    collection = MockMongoCollection(SAMPLE_CARDS)

    # Find cards with exactly 2 colors (none in sample data)
    cursor = collection.find({"colors": {"$size": 2}})
    results = list(cursor)
    assert len(results) == 0

    # Find cards with exactly 1 color
    cursor = collection.find({"colors": {"$size": 1}})
    results = list(cursor)
    assert len(results) == 2  # Lightning Bolt (R), Counterspell (U)
    names = [r["name"] for r in results]
    assert "Lightning Bolt" in names
    assert "Counterspell" in names

    # Find cards with exactly 0 colors (colorless)
    cursor = collection.find({"colors": {"$size": 0}})
    results = list(cursor)
    assert len(results) == 1
    assert results[0]["name"] == "Black Lotus"

    # Find cards with exactly 5 colors
    cursor = collection.find({"colors": {"$size": 5}})
    results = list(cursor)
    assert len(results) == 1
    assert results[0]["name"] == "Progenitus"


@pytest.mark.unit
def test_size_and_all_operators_combined():
    """Test $size and $all operators together for exact color matching.

    This simulates the 'exactly' color operator from CardFilter:
    - Card must have ALL specified colors ($all)
    - Card must have EXACTLY that many colors ($size)

    This is critical for Phase 5 search endpoint testing.
    """
    # Add a two-color card to test data
    cards_with_multicolor = SAMPLE_CARDS + [
        {
            "id": "5",
            "name": "Izzet Charm",
            "colors": ["U", "R"],
            "cmc": 2.0,
            "rarity": "uncommon",
            "set_name": "Return to Ravnica",
        }
    ]
    collection = MockMongoCollection(cards_with_multicolor)

    # Find cards with exactly U and R (no more, no less)
    cursor = collection.find({"colors": {"$all": ["U", "R"], "$size": 2}})
    results = list(cursor)

    assert len(results) == 1
    assert results[0]["name"] == "Izzet Charm"
    assert results[0]["colors"] == ["U", "R"]

    # Verify Progenitus is NOT included (has U+R but also W+B+G)
    cursor = collection.find({"colors": {"$all": ["U", "R"], "$size": 2}})
    results = list(cursor)
    names = [r["name"] for r in results]
    assert "Progenitus" not in names


# Cards with deliberately different relevance profiles for the query
# "lightning bolt". Their _id values sort in the *reverse* of their relevance
# order, so a test can tell real score ordering apart from an _id fallback.
RELEVANCE_CARDS = [
    {
        # Exact name match: both query terms fill the whole name field.
        "_id": "id-4",
        "name": "Lightning Bolt",
        "type_line": "Instant",
        "oracle_text": "Lightning Bolt deals 3 damage to any target.",
    },
    {
        # One term in a two-word name, short oracle text.
        "_id": "id-3",
        "name": "Chain Lightning",
        "type_line": "Sorcery",
        "oracle_text": "Chain Lightning deals 3 damage to any target.",
    },
    {
        # One term in a three-word name, long oracle text: lower density.
        "_id": "id-2",
        "name": "Lightning-Rig Crew",
        "type_line": "Creature — Goblin",
        "oracle_text": (
            "Whenever an instant or sorcery spell is cast, "
            "Lightning-Rig Crew deals 1 damage to each opponent."
        ),
    },
    {
        # No name match at all: hits only the low-weighted flavor text.
        "_id": "id-1",
        "name": "Shock",
        "type_line": "Instant",
        "oracle_text": "Shock deals 2 damage to any target.",
        "flavor_text": "A bolt of lightning from a cloudless sky.",
    },
]

# Relevance order for the query "lightning bolt", most relevant first.
EXPECTED_RELEVANCE_ORDER = [
    "Lightning Bolt",
    "Chain Lightning",
    "Lightning-Rig Crew",
    "Shock",
]


def _text_score_pipeline(search: str, sort: Optional[dict] = None) -> list[dict]:
    """Build a pipeline that projects a real textScore, like the search route."""
    pipeline: list[dict] = [
        {"$match": {"$text": {"$search": search}}},
        {"$project": {"score": {"$meta": "textScore"}, "name": 1, "_id": 1}},
    ]
    if sort is not None:
        pipeline.append({"$sort": sort})
    return pipeline


@pytest.mark.unit
def test_project_meta_text_score_projects_a_score():
    """$project with {"$meta": "textScore"} must project a numeric score.

    This is the capability the search route needs (issue #21): without it a
    relevance test cannot distinguish {"score": 1} from a real text score.
    """
    collection = MockMongoCollection(RELEVANCE_CARDS)

    results = list(collection.aggregate(_text_score_pipeline("lightning bolt")))

    assert len(results) == len(RELEVANCE_CARDS)
    assert all("score" in card for card in results), (
        f"$meta textScore projected no score: {results}"
    )
    assert all(isinstance(card["score"], float) for card in results)
    assert all(card["score"] > 0.0 for card in results)


@pytest.mark.unit
def test_meta_text_score_differs_per_document():
    """Scores must vary with relevance, not be a constant.

    A constant score would make a relevance test meaningless because $sort
    would silently fall back to the tie-breaker field.
    """
    collection = MockMongoCollection(RELEVANCE_CARDS)

    results = list(collection.aggregate(_text_score_pipeline("lightning bolt")))
    scores = [card["score"] for card in results]

    assert len(set(scores)) == len(scores), f"scores are not distinct: {scores}"


@pytest.mark.unit
def test_meta_text_score_ranks_exact_name_match_highest():
    """The card whose name is exactly the query must score highest."""
    collection = MockMongoCollection(RELEVANCE_CARDS)

    results = list(collection.aggregate(_text_score_pipeline("lightning bolt")))
    by_name = {card["name"]: card["score"] for card in results}

    others = [score for name, score in by_name.items() if name != "Lightning Bolt"]
    assert all(by_name["Lightning Bolt"] > score for score in others), by_name


@pytest.mark.unit
def test_sort_orders_documents_by_meta_projected_score():
    """$sort on a $meta-projected score must actually order documents.

    Branch 2 depends on this: the score has to drive the ordering, not the
    _id tie-breaker. RELEVANCE_CARDS' _ids sort in the reverse order, so an
    _id fallback cannot pass this test by accident.
    """
    collection = MockMongoCollection(RELEVANCE_CARDS)

    results = list(
        collection.aggregate(
            _text_score_pipeline("lightning bolt", sort={"score": -1, "_id": 1})
        )
    )

    assert [card["name"] for card in results] == EXPECTED_RELEVANCE_ORDER
    scores = [card["score"] for card in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.unit
def test_project_score_one_does_not_invent_a_score():
    """{"$project": {"score": 1}} must not fabricate a score.

    MongoDB projects the document's own `score` field; card documents have
    none, so the field is simply absent. The mock must reproduce that or a
    test for issue #21 passes whether or not the bug is fixed.
    """
    collection = MockMongoCollection(RELEVANCE_CARDS)

    pipeline = [
        {"$match": {"$text": {"$search": "lightning bolt"}}},
        {"$project": {"score": 1, "name": 1}},
    ]
    results = list(collection.aggregate(pipeline))

    assert len(results) == len(RELEVANCE_CARDS)
    assert all("score" not in card for card in results), (
        f"mock invented a score for a plain inclusion projection: {results}"
    )


@pytest.mark.unit
def test_project_score_one_keeps_a_stored_score():
    """A document that really has a `score` field keeps it."""
    collection = MockMongoCollection([{"_id": "1", "name": "Shock", "score": 4.25}])

    results = list(collection.aggregate([{"$project": {"score": 1, "name": 1}}]))

    assert results[0]["score"] == 4.25


@pytest.mark.unit
def test_group_max_of_absent_score_is_none():
    """$max over a field no document has yields null, as MongoDB does.

    This is what makes issue #21's broken cursor observable: the route emits
    f"{score}:{id}" and so produces the literal string "None:<id>".
    """
    collection = MockMongoCollection(RELEVANCE_CARDS)

    pipeline = [
        {"$match": {"$text": {"$search": "lightning bolt"}}},
        {"$project": {"score": 1, "name": 1, "_id": 1}},
        {"$group": {"_id": "$_id", "score": {"$max": "$score"}}},
    ]
    results = list(collection.aggregate(pipeline))

    assert all("score" in group for group in results)
    assert all(group["score"] is None for group in results)


@pytest.mark.unit
def test_sort_on_null_score_falls_back_to_id_order():
    """Sorting by a null score must not raise and degenerates to _id order.

    This is the production behaviour of issue #21, and the mock has to model
    it rather than crash, so the bug is observable end to end.
    """
    collection = MockMongoCollection(RELEVANCE_CARDS)

    pipeline = [
        {"$match": {"$text": {"$search": "lightning bolt"}}},
        {"$project": {"score": 1, "name": 1, "_id": 1}},
        {
            "$group": {
                "_id": "$_id",
                "name": {"$first": "$name"},
                "score": {"$max": "$score"},
            }
        },
        {"$sort": {"score": -1, "_id": 1}},
    ]
    results = list(collection.aggregate(pipeline))

    assert [group["_id"] for group in results] == ["id-1", "id-2", "id-3", "id-4"]
    # Reverse of the relevance order: no ranking happened at all.
    assert [group["name"] for group in results] == EXPECTED_RELEVANCE_ORDER[::-1]


@pytest.mark.unit
def test_meta_text_score_requires_a_text_query():
    """$meta textScore without a $text query is an error, as in MongoDB."""
    collection = MockMongoCollection(RELEVANCE_CARDS)

    with pytest.raises(ValueError, match="textScore"):
        list(collection.aggregate([{"$project": {"score": {"$meta": "textScore"}}}]))


@pytest.mark.unit
def test_meta_text_score_not_leaked_between_pipelines():
    """A previous pipeline's $text query must not score a later one."""
    collection = MockMongoCollection(RELEVANCE_CARDS)

    list(collection.aggregate(_text_score_pipeline("lightning bolt")))

    with pytest.raises(ValueError, match="textScore"):
        list(collection.aggregate([{"$project": {"score": {"$meta": "textScore"}}}]))


@pytest.mark.unit
def test_text_search_matches_any_term():
    """$text matches documents containing any query term, as MongoDB does."""
    collection = MockMongoCollection(RELEVANCE_CARDS)

    results = list(collection.find({"$text": {"$search": "counterspell shock"}}))

    assert [card["name"] for card in results] == ["Shock"]


@pytest.mark.unit
def test_find_projection_supports_meta_text_score():
    """find() projections accept {"$meta": "textScore"} too."""
    collection = MockMongoCollection(RELEVANCE_CARDS)

    results = list(
        collection.find(
            {"$text": {"$search": "lightning bolt"}},
            {"name": 1, "score": {"$meta": "textScore"}},
        )
    )

    assert all(card["score"] > 0.0 for card in results)
