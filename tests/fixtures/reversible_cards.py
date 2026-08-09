"""Sample ``reversible_card`` documents - cards with **no** top-level oracle_id.

Scryfall omits ``oracle_id`` at the top level of a ``reversible_card`` and puts
one on each face instead, because the two faces are separate Oracle cards
printed back-to-back. Every other layout - including ``transform``, which also
has ``card_faces`` - keeps the top-level field.

That absence is the whole of issue #22, so these documents model it exactly:
``oracle_id`` is not present at all, rather than present and null or empty.
A generator cannot produce this shape; it has to be written by hand.

Both cards below are from *Secret Lair Drop: Heads I Win, Tails You Lose*
(set ``sld``), the drop that introduced the layout.

**Temporary home.** The fix plan gives Branch 0d ownership of the shared
fixture set, including "a reversible card with no ``oracle_id``". When 0d
lands, these should move into it - and the MSW/TypeScript fixtures it defines
should be built from the same two documents, so the pytest and Tier B suites
disagree about nothing.
"""

REVERSIBLE_PROPAGANDA = {
    # No "oracle_id" key here - that is the point of the fixture.
    "id": "8b8e6e5e-6a51-4d5f-9b06-0a1c1e1d1f20",
    "name": "Propaganda // Propaganda",
    "name_search": "propaganda // propaganda",
    "lang": "en",
    "released_at": "2022-04-22",
    "layout": "reversible_card",
    "cmc": 3.0,
    "type_line": "Enchantment // Enchantment",
    "oracle_text": (
        "Creatures can't attack you unless their controller pays {2} for "
        "each creature they control that's attacking you."
    ),
    "mana_cost": "{2}{U}",
    "colors": ["U"],
    "color_identity": ["U"],
    "rarity": "rare",
    "set_name": "Secret Lair Drop",
    "set": "sld",
    "artist": "Dan Frazier",
    "card_faces": [
        {
            "oracle_id": "b0e0c0d0-1111-4222-8333-444455556666",
            "name": "Propaganda",
            "type_line": "Enchantment",
            "image_uris": {
                "normal": "https://cards.scryfall.io/normal/propaganda-front.jpg",
                "large": "https://cards.scryfall.io/large/propaganda-front.jpg",
                "png": "https://cards.scryfall.io/png/propaganda-front.png",
            },
        },
        {
            "oracle_id": "b0e0c0d0-1111-4222-8333-444455556666",
            "name": "Propaganda",
            "type_line": "Enchantment",
            "image_uris": {
                "normal": "https://cards.scryfall.io/normal/propaganda-back.jpg",
                "large": "https://cards.scryfall.io/large/propaganda-back.jpg",
                "png": "https://cards.scryfall.io/png/propaganda-back.png",
            },
        },
    ],
    "promo": False,
    "reprint": True,
}

REVERSIBLE_COMMAND_TOWER = {
    # Also no "oracle_id" - a second one, so a test can tell "grouped
    # correctly" apart from "collapsed into a single null-keyed bucket".
    "id": "3d3c2b1a-9f8e-4d7c-8b6a-5e4d3c2b1a09",
    "name": "Command Tower // Command Tower",
    "name_search": "command tower // command tower",
    "lang": "en",
    "released_at": "2022-04-22",
    "layout": "reversible_card",
    "cmc": 0.0,
    "type_line": "Land // Land",
    "oracle_text": (
        "{T}: Add one mana of any color in your commander's color identity."
    ),
    "mana_cost": "",
    "colors": [],
    "color_identity": [],
    "rarity": "rare",
    "set_name": "Secret Lair Drop",
    "set": "sld",
    "artist": "Yeong-Hao Han",
    "card_faces": [
        {
            "oracle_id": "c1f1d1e1-2222-4333-8444-555566667777",
            "name": "Command Tower",
            "type_line": "Land",
            "image_uris": {
                "normal": "https://cards.scryfall.io/normal/tower-front.jpg",
                "large": "https://cards.scryfall.io/large/tower-front.jpg",
                "png": "https://cards.scryfall.io/png/tower-front.png",
            },
        },
        {
            "oracle_id": "c1f1d1e1-2222-4333-8444-555566667777",
            "name": "Command Tower",
            "type_line": "Land",
            "image_uris": {
                "normal": "https://cards.scryfall.io/normal/tower-back.jpg",
                "large": "https://cards.scryfall.io/large/tower-back.jpg",
                "png": "https://cards.scryfall.io/png/tower-back.png",
            },
        },
    ],
    "promo": False,
    "reprint": True,
}

# A term present in both names and in nothing else in the sample set, so a
# single $text query returns exactly the two reversible cards. MongoDB's
# $text is an OR over terms, so "propaganda tower" matches both.
REVERSIBLE_SEARCH_TEXT = "propaganda tower"


def get_all_reversible_cards() -> list[dict]:
    """Get every reversible-layout sample card.

    Returns:
        List of card dictionaries, none of which carries a top-level oracle_id.
    """
    return [REVERSIBLE_PROPAGANDA, REVERSIBLE_COMMAND_TOWER]
