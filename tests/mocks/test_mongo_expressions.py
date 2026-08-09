"""Tests for the mock's field-path and expression evaluation.

Written after the implementation rather than before it: these cover test
*infrastructure* added so the #22 tests could run truthfully, not the defect
itself. The red-first tests for #22 are in
``tests/api/router/test_reversible_cards.py``.

They matter because a mock that quietly returns None where MongoDB returns a
value is how a test passes for the wrong reason - the failure mode the fix
plan calls out for this file specifically.
"""

import pytest

from api.helpers.cards_mongo import CARD_PROJECTION, ORACLE_ID
from tests.fixtures.reversible_cards import REVERSIBLE_PROPAGANDA
from tests.fixtures.sample_cards import DELVER_OF_SECRETS, LIGHTNING_BOLT
from tests.mocks.mongo_expressions import (
    MISSING,
    read_field,
    resolve_expression,
    resolve_path,
)
from tests.mocks.mongodb import MockMongoCollection


class TestResolvePath:
    """Dotted paths, including the array mapping MongoDB does."""

    def test_resolves_a_nested_field(self):
        assert (
            resolve_path(LIGHTNING_BOLT, "image_uris.normal")
            == "https://cards.scryfall.io/normal/lightning-bolt.jpg"
        )

    def test_maps_over_an_array_of_subdocuments(self):
        assert resolve_path(DELVER_OF_SECRETS, "card_faces.name") == [
            "Delver of Secrets",
            "Insectile Aberration",
        ]

    def test_absent_field_is_missing_not_none(self):
        # $ifNull and $exists both turn on this distinction.
        assert resolve_path(LIGHTNING_BOLT, "card_faces") is MISSING
        assert resolve_path(LIGHTNING_BOLT, "image_uris.nope") is MISSING

    def test_read_field_flattens_missing_to_none(self):
        assert read_field(LIGHTNING_BOLT, "card_faces") is None


class TestResolveExpression:
    """$ifNull and $arrayElemAt, the two operators #22's fix needs."""

    def test_if_null_prefers_the_first_present_value(self):
        expression = {"$ifNull": ["$oracle_id", "fallback"]}
        assert (
            resolve_expression(expression, LIGHTNING_BOLT)
            == (LIGHTNING_BOLT["oracle_id"])
        )

    def test_if_null_falls_through_when_the_field_is_absent(self):
        expression = {"$ifNull": ["$oracle_id", "fallback"]}
        assert resolve_expression(expression, REVERSIBLE_PROPAGANDA) == "fallback"

    def test_array_elem_at_indexes_a_mapped_path(self):
        expression = {"$arrayElemAt": ["$card_faces.name", 1]}
        assert resolve_expression(expression, DELVER_OF_SECRETS) == (
            "Insectile Aberration"
        )

    def test_array_elem_at_past_the_end_is_missing(self):
        expression = {"$arrayElemAt": ["$card_faces.name", 9]}
        assert resolve_expression(expression, DELVER_OF_SECRETS) is MISSING

    def test_unsupported_operator_raises_rather_than_yielding_none(self):
        with pytest.raises(ValueError, match=r"\$toUpper"):
            resolve_expression({"$toUpper": "$name"}, LIGHTNING_BOLT)

    def test_oracle_id_expression_resolves_both_layouts(self):
        """The production expression, against a card of each shape."""
        assert (
            resolve_expression(ORACLE_ID, LIGHTNING_BOLT)
            == (LIGHTNING_BOLT["oracle_id"])
        )
        assert (
            resolve_expression(ORACLE_ID, REVERSIBLE_PROPAGANDA)
            == REVERSIBLE_PROPAGANDA["card_faces"][0]["oracle_id"]
        )


class TestComputedProjection:
    """CARD_PROJECTION's computed fields now survive the mock."""

    def test_thumbnail_is_projected_from_image_uris(self):
        collection = MockMongoCollection([LIGHTNING_BOLT])

        card = collection.find_one({"id": LIGHTNING_BOLT["id"]}, CARD_PROJECTION)

        assert card["thumbnail"] == LIGHTNING_BOLT["image_uris"]["normal"]
        assert card["imageXL"] == LIGHTNING_BOLT["image_uris"]["png"]

    def test_faces_thumbnails_are_projected_from_card_faces(self):
        """Both faces, which is what issue #35 needs to be observable."""
        collection = MockMongoCollection([DELVER_OF_SECRETS])

        card = collection.find_one({"id": DELVER_OF_SECRETS["id"]}, CARD_PROJECTION)

        assert card["faces_thumbnails"] == [
            "https://cards.scryfall.io/normal/delver-front.jpg",
            "https://cards.scryfall.io/normal/delver-back.jpg",
        ]

    def test_a_card_without_images_omits_the_derived_fields(self):
        """Absent, not null: Mongo drops a projected field with no source."""
        collection = MockMongoCollection([{"id": "x", "name": "Placeholder"}])

        card = collection.find_one({"id": "x"}, CARD_PROJECTION)

        assert "thumbnail" not in card
        assert "faces_thumbnails" not in card


class TestDottedQueryMatching:
    """A dotted query path matches into an array of subdocuments."""

    def test_matches_a_value_on_any_face(self):
        collection = MockMongoCollection([REVERSIBLE_PROPAGANDA, LIGHTNING_BOLT])
        face_oracle_id = REVERSIBLE_PROPAGANDA["card_faces"][0]["oracle_id"]

        found = list(collection.find({"card_faces.oracle_id": face_oracle_id}))

        assert [doc["name"] for doc in found] == ["Propaganda // Propaganda"]

    def test_does_not_match_an_unrelated_value(self):
        collection = MockMongoCollection([REVERSIBLE_PROPAGANDA])

        assert list(collection.find({"card_faces.oracle_id": "nope"})) == []

    def test_exists_follows_a_dotted_path(self):
        collection = MockMongoCollection([REVERSIBLE_PROPAGANDA, LIGHTNING_BOLT])

        found = list(collection.find({"card_faces.oracle_id": {"$exists": True}}))

        assert [doc["name"] for doc in found] == ["Propaganda // Propaganda"]
