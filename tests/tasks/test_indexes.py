"""The card collection is indexed for the queries the API actually runs.

A missing index is not a wrong answer, it is a slow one, so nothing in an
integration suite can see it: the mock has no query planner and the real
collection returns the same documents either way. What *is* checkable is
whether a field the API queries was ever declared indexable at all, and
that is where this class of regression starts.

Issue #22's fix added one. ``oracle_id_match`` looks a card up by either
its top-level oracle id or one carried on a face, because Scryfall puts
the oracle id on the faces of a ``reversible_card``. Only the first branch
had an index, so the second was a collection scan - on every card page
load, since the ``$or`` runs whatever the layout.
"""

import pytest

from api.helpers.cards_mongo import oracle_id_match
from tasks.indexes import INDEX_BASE


def indexed_fields() -> set[str]:
    """Every field name INDEX_BASE declares an index on."""
    return {key for model in INDEX_BASE for key in model.document["key"]}


@pytest.mark.unit
def test_every_field_the_oracle_lookup_queries_has_an_index():
    """Both branches of the oracle-id $or, not just the top-level one."""
    queried = {field for clause in oracle_id_match("x")["$or"] for field in clause}

    assert queried <= indexed_fields(), (
        f"queried without an index: {sorted(queried - indexed_fields())}"
    )


@pytest.mark.unit
def test_no_index_is_declared_twice():
    """A duplicate entry is dead weight on every write."""
    declared = [
        name for model in INDEX_BASE for name in [tuple(model.document["key"].items())]
    ]

    assert len(declared) == len(set(declared))
