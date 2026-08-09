"""Structural guards keeping a whole class of defect out of the responses.

``tests/api/test_response_model_tolerance.py`` proves two specific odd
documents are served. These prove the next one will be too, by refusing the
shapes that turn odd data into an outage: a closed literal, a format
constraint, a required field nobody signed off on.

The rule, from the plan's resolved open decision:

    Strictness on a *response* model is an availability risk, not a
    test-coverage question. A request model rejects bad input; a response
    model returns HTTP 500.

Worth stating plainly, because it is the reason these guards can be this
blunt: nothing validates a card on the way *in*. ``tasks/fetch_dataset.py``
inserts Scryfall's bulk JSON verbatim (``InsertOne(card)``), and
``common.scyfall_models.PrintedCard`` - the hierarchy these models borrow
their field names from - is imported by tests only, never by the ingestion
or the API. So no narrowing here has ever been "verified against
production"; it has only been unfalsified.
"""

import typing
from typing import Literal, get_args, get_origin

import pytest
from pydantic import BaseModel

from api.models.cards import CardPrinting, OracleCard, SearchResponse, SearchResultCard

RESPONSE_MODELS = (CardPrinting, OracleCard, SearchResultCard, SearchResponse)

# Requiredness is the other half of the availability risk: a required field
# a document may not carry is a 500 for that document. Each entry is a
# deliberate decision, not an accident of how the model was written.
#
#   CardPrinting.id/name  - every Scryfall printing carries both.
#   OracleCard.id         - the value clients build a card URL from. Issue
#                           #22 is exactly the case where it is missing,
#                           which is why 0b must not deploy without the
#                           branch that guarantees it.
#   card_count / cards    - computed by the $group, never absent.
#   has_more              - computed by the handler, never absent.
EXPECTED_REQUIRED = {
    CardPrinting: {"id", "name"},
    OracleCard: {"id", "name", "card_count", "cards"},
    SearchResultCard: {"id", "name", "card_count", "cards"},
    SearchResponse: {"cards", "has_more"},
}


def annotations(model: type[BaseModel]) -> typing.Iterator[tuple[str, str, object]]:
    """Yield ``(owner, field, annotation)`` for every nested annotation.

    Walks into ``Optional``/``list``/``dict``/``Union`` arguments and into
    nested response models, so a literal buried in ``list[Color] | None`` -
    which is exactly where the colour one hid - is still found.
    """
    for name, field in model.model_fields.items():
        seen: set[object] = set()
        stack = [field.annotation]
        while stack:
            annotation = stack.pop()
            if annotation in seen:
                continue
            seen.add(annotation)
            yield model.__name__, name, annotation
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                if annotation is not model:
                    yield from annotations(annotation)
                continue
            stack.extend(get_args(annotation))


@pytest.mark.parametrize("model", RESPONSE_MODELS)
def test_no_response_field_is_typed_as_a_closed_literal(model):
    """A ``Literal`` on a response is a 500 waiting for its first new value.

    Card data is other people's data, and its value sets grow: rarity,
    layout, security_stamp, games and frame_effects have all gained members.
    None of those additions should be able to take an endpoint down, so the
    fields most tempting to narrow are deliberately plain ``str``. Document
    the value set in the field description instead - it survives into the
    generated TypeScript as a JSDoc comment and rejects nothing.
    """
    offenders = [
        f"{owner}.{field}"
        for owner, field, annotation in annotations(model)
        if get_origin(annotation) is Literal
    ]

    assert offenders == [], f"closed literals on a response model: {offenders}"


@pytest.mark.parametrize("model", RESPONSE_MODELS)
def test_no_response_field_carries_a_format_constraint(model):
    """No ``UUID4``, ``AnyUrl``, pattern or bound on a response field.

    The same reasoning one level down. A card whose id is not a v4 UUID, or
    whose ``related_uris`` holds something that will not parse as a URL, is
    an odd card - but odd and serviceable, and turning it into an outage
    buys nothing that the generated ``string`` type does not already give.
    """
    offenders = [
        f"{owner}.{field}: {getattr(annotation, '__name__', annotation)}"
        for owner, field, annotation in annotations(model)
        if any(
            bad in getattr(annotation, "__name__", str(annotation))
            for bad in ("UUID", "Url", "URL")
        )
    ]

    # Field metadata is where Field(pattern=...), gt/ge/min_length and
    # Annotated[str, StringConstraints(...)] all end up.
    offenders.extend(
        f"{model.__name__}.{name}: {field.metadata}"
        for name, field in model.model_fields.items()
        if field.metadata
    )

    assert offenders == [], f"format-constrained response fields: {offenders}"


@pytest.mark.parametrize("model", RESPONSE_MODELS)
def test_required_response_fields_are_a_deliberate_list(model):
    """Requiring a field is a deploy-coupled decision, so it is written down.

    A newly-required field must ship in the same deploy as the branch that
    guarantees it. Keeping the list explicit means adding one cannot happen
    quietly: the test names the field, and a reviewer has to agree.
    """
    required = {
        name for name, field in model.model_fields.items() if field.is_required()
    }

    assert required == EXPECTED_REQUIRED[model]
