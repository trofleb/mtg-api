"""Response models for the card endpoints.

These exist so ``/openapi.json`` says something about responses. Without
them the document describes request parameters only, codegen against it
yields ``unknown``, and every client is left to guess - which is how
``lib/api.ts``'s ``id ?? _id ?? ""`` fallback came about.

Two shapes, mirroring the two MongoDB stages in ``api.helpers.cards_mongo``:

* :class:`CardPrinting` - one printing, as ``CARD_PROJECTION`` projects it.
* :class:`OracleCard` - printings grouped by oracle id, as ``AGGREGATE_CARD``
  groups them.

Field *names* are taken from the Scryfall hierarchy in
``common.scyfall_models``; ``tests/api/test_openapi_contract.py`` fails if
either model drifts from its pipeline stage or names a field Scryfall does
not have.

Field *types* are deliberately looser than the hierarchy's. ``PrintedCard``
declares ``UUID4`` and ``AnyUrl`` where these declare ``str``, because a
response model rejects what it cannot validate: a card whose id is not a
v4 UUID would become a 500 rather than a card. The generated TypeScript is
``string`` either way, so the strictness would buy nothing and cost
availability. Strictness is spent where it is worth an outage instead - on
``id``, below.

The same reasoning removed the one hierarchy type this module did reuse.
``colors``/``color_identity`` were ``list[Color]``, i.e. the closed
``Literal["W","U","B","R","G"]``, so a stored card carrying the colorless
code ``["C"]`` raised ``ResponseValidationError`` and the caller got a 500
instead of a card. Scryfall writes colorless as ``[]``, but MTGJSON and
several Scryfall-adjacent dumps write ``["C"]``, and nobody could check
which the production collection holds. That unquantified exposure is the
point: on a *response* model, narrowing is an availability risk rather than
a coverage question, because there is no bad-input path to reject - only a
card the client no longer receives. The value set is documented in the
field description instead, which reaches clients as a JSDoc comment on the
generated TypeScript and rejects nothing.

``tests/api/test_response_model_tolerance.py`` holds that line: it fails if
a closed literal, a format constraint or an undeclared required field
reappears on any of these models.
"""

from typing import Optional

from pydantic import BaseModel, Field

COLOR_DESCRIPTION = (
    "Colour codes. Normally W, U, B, R or G; colourless is usually an empty "
    "list, though some sources write the code C instead. Not validated "
    "against a fixed set - an unrecognised code is passed through rather "
    "than failing the response."
)


class CardPrinting(BaseModel):
    """A single printing of a card, shaped by ``CARD_PROJECTION``.

    Only ``id`` and ``name`` are required: the projection asks for fields
    that plenty of real cards simply do not carry (no watermark, no flavour
    text, no images on a placeholder printing), and Mongo omits a projected
    field entirely when the source is missing.
    """

    id: str
    name: str
    printed_name: Optional[str] = None
    oracle_id: Optional[str] = None
    lang: Optional[str] = None
    oracle_text: Optional[str] = None
    set_name: Optional[str] = None
    type_line: Optional[str] = None
    mana_cost: Optional[str] = None
    cmc: Optional[float] = None
    colors: Optional[list[str]] = Field(default=None, description=COLOR_DESCRIPTION)
    color_identity: Optional[list[str]] = Field(
        default=None, description=COLOR_DESCRIPTION
    )
    artist: Optional[str] = None
    layout: Optional[str] = None
    flavor_name: Optional[str] = None
    flavor_text: Optional[str] = None
    games: Optional[list[str]] = None
    # dict[str, str] would be a claim that every value of somebody else's
    # object is a string; a single null failed the whole card. Scryfall uses
    # nulls for absent values in the sibling "prices" object, so the
    # convention exists in these very documents.
    image_uris: Optional[dict[str, Optional[str]]] = None
    promo: Optional[bool] = None
    rarity: Optional[str] = None
    related_uris: Optional[dict[str, Optional[str]]] = None
    released_at: Optional[str] = None
    reprint: Optional[bool] = None
    set: Optional[str] = None
    variation: Optional[bool] = None
    variation_of: Optional[str] = None
    security_stamp: Optional[str] = None
    watermark: Optional[str] = None
    # Derived by the projection rather than taken from Scryfall: the image
    # sizes clients actually render, lifted out of image_uris / card_faces.
    thumbnail: Optional[str] = None
    faces_thumbnails: Optional[list[str]] = None
    image: Optional[str] = None
    imageXL: Optional[str] = None


class OracleCard(BaseModel):
    """A card aggregated across its printings, shaped by ``AGGREGATE_CARD``.

    ``id`` is the oracle id the group was keyed on, and it is required. That
    is the one piece of strictness worth an outage: it is the value every
    client builds a card URL from, and while it lived only in ``_expose_id``
    it was a convention rather than a contract. Declaring it required turns
    a group with no oracle id - what a ``reversible_card`` layout produces,
    since Scryfall puts the oracle id on each face instead of the card -
    into a loud failure at the boundary instead of an empty ``href``.
    """

    id: str
    name: str
    card_count: int
    cards: list[CardPrinting]
    card_text: Optional[str] = None
    type_line: Optional[str] = None
    mana_cost: Optional[str] = None
    cmc: Optional[float] = None
    colors: Optional[list[str]] = Field(default=None, description=COLOR_DESCRIPTION)
    rarity: Optional[str] = None
    edhrec_rank: Optional[int] = None
    penny_rank: Optional[int] = None
    thumbnail: Optional[str] = None
    faces_thumbnails: Optional[list[str]] = None


class SearchResultCard(OracleCard):
    """An :class:`OracleCard` carrying the relevance score that ranked it.

    Only search produces a score, so it is declared here rather than on
    ``OracleCard``: the aggregated endpoint should not advertise a field it
    never returns. The score is also what the pagination cursor is built
    from, which makes it worth exposing rather than hiding.
    """

    score: Optional[float] = None


class SearchResponse(BaseModel):
    """A page of search results plus the cursor that continues it."""

    cards: list[SearchResultCard]
    cursor: Optional[str] = None
    has_more: bool
