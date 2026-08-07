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
"""

from typing import Optional

from pydantic import BaseModel

from common.scyfall_models import Color


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
    colors: Optional[list[Color]] = None
    color_identity: Optional[list[Color]] = None
    artist: Optional[str] = None
    layout: Optional[str] = None
    flavor_name: Optional[str] = None
    flavor_text: Optional[str] = None
    games: Optional[list[str]] = None
    image_uris: Optional[dict[str, str]] = None
    promo: Optional[bool] = None
    rarity: Optional[str] = None
    related_uris: Optional[dict[str, str]] = None
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
    colors: Optional[list[Color]] = None
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
