"""Builder pattern for creating test card objects.

This module provides a fluent API for building test card dictionaries,
reducing boilerplate code in test files.
"""

import uuid
from typing import Any


class CardBuilder:
    """Fluent API builder for creating test MTG card objects.

    Example:
        card = (CardBuilder()
                .with_name("Test Card")
                .with_colors(["R", "U"])
                .with_cmc(3)
                .with_rarity("rare")
                .build())
    """

    def __init__(self) -> None:
        """Initialize a new CardBuilder with default values."""
        self._card: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "oracle_id": str(uuid.uuid4()),
            "name": "Test Card",
            "lang": "en",
            "mana_cost": "{1}{U}",
            "cmc": 2,
            "colors": ["U"],
            "color_identity": ["U"],
            "type_line": "Instant",
            "oracle_text": "Test card text.",
            "set": "TST",
            "set_name": "Test Set",
            "set_id": str(uuid.uuid4()),
            "rarity": "common",
            "released_at": "2024-01-01",
            "artist": "Test Artist",
            "layout": "normal",
            "image_uris": {
                "small": "https://example.com/small.jpg",
                "normal": "https://example.com/normal.jpg",
                "large": "https://example.com/large.jpg",
                "png": "https://example.com/png.png",
                "art_crop": "https://example.com/art_crop.jpg",
                "border_crop": "https://example.com/border_crop.jpg",
            },
            "games": ["paper", "mtgo", "arena"],
            "digital": False,
            "promo": False,
            "reprint": False,
        }

    def with_id(self, card_id: str) -> "CardBuilder":
        """Set the Scryfall ID of the card.

        Args:
            card_id: The Scryfall UUID for the card

        Returns:
            Self for method chaining
        """
        self._card["id"] = card_id
        return self

    def with_oracle_id(self, oracle_id: str) -> "CardBuilder":
        """Set the Oracle ID of the card.

        Args:
            oracle_id: The Oracle UUID for the card concept

        Returns:
            Self for method chaining
        """
        self._card["oracle_id"] = oracle_id
        return self

    def with_name(self, name: str) -> "CardBuilder":
        """Set the name of the card.

        Args:
            name: The card name

        Returns:
            Self for method chaining
        """
        self._card["name"] = name
        return self

    def with_lang(self, lang: str) -> "CardBuilder":
        """Set the language of the card.

        Args:
            lang: Language code (e.g., 'en', 'fr', 'ja')

        Returns:
            Self for method chaining
        """
        self._card["lang"] = lang
        return self

    def with_mana_cost(self, mana_cost: str) -> "CardBuilder":
        """Set the mana cost of the card.

        Args:
            mana_cost: Mana cost in Scryfall format (e.g., '{2}{R}{R}')

        Returns:
            Self for method chaining
        """
        self._card["mana_cost"] = mana_cost
        return self

    def with_cmc(self, cmc: int | float) -> "CardBuilder":
        """Set the converted mana cost of the card.

        Args:
            cmc: Converted mana cost (0-15+)

        Returns:
            Self for method chaining
        """
        self._card["cmc"] = cmc
        return self

    def with_colors(self, colors: list[str]) -> "CardBuilder":
        """Set the colors of the card.

        Args:
            colors: List of color codes (e.g., ['W', 'U', 'B', 'R', 'G'])

        Returns:
            Self for method chaining
        """
        self._card["colors"] = colors
        self._card["color_identity"] = colors  # Usually the same
        return self

    def with_color_identity(self, color_identity: list[str]) -> "CardBuilder":
        """Set the color identity of the card (for Commander format).

        Args:
            color_identity: List of color codes

        Returns:
            Self for method chaining
        """
        self._card["color_identity"] = color_identity
        return self

    def with_type_line(self, type_line: str) -> "CardBuilder":
        """Set the type line of the card.

        Args:
            type_line: Type line (e.g., 'Legendary Creature — Human Wizard')

        Returns:
            Self for method chaining
        """
        self._card["type_line"] = type_line
        return self

    def with_oracle_text(self, oracle_text: str) -> "CardBuilder":
        """Set the oracle text of the card.

        Args:
            oracle_text: Rules text of the card

        Returns:
            Self for method chaining
        """
        self._card["oracle_text"] = oracle_text
        return self

    def with_set(self, set_code: str, set_name: str | None = None) -> "CardBuilder":
        """Set the set code and optionally set name.

        Args:
            set_code: Three-letter set code (e.g., 'MH2')
            set_name: Full set name (optional, defaults to set_code)

        Returns:
            Self for method chaining
        """
        self._card["set"] = set_code
        self._card["set_name"] = set_name or set_code
        return self

    def with_rarity(self, rarity: str) -> "CardBuilder":
        """Set the rarity of the card.

        Args:
            rarity: One of 'common', 'uncommon', 'rare', 'mythic'

        Returns:
            Self for method chaining
        """
        self._card["rarity"] = rarity
        return self

    def with_released_at(self, date: str) -> "CardBuilder":
        """Set the release date of the card.

        Args:
            date: ISO date string (YYYY-MM-DD)

        Returns:
            Self for method chaining
        """
        self._card["released_at"] = date
        return self

    def with_artist(self, artist: str) -> "CardBuilder":
        """Set the artist of the card.

        Args:
            artist: Artist name

        Returns:
            Self for method chaining
        """
        self._card["artist"] = artist
        return self

    def with_layout(self, layout: str) -> "CardBuilder":
        """Set the layout of the card.

        Args:
            layout: Layout type (e.g., 'normal', 'transform', 'split')

        Returns:
            Self for method chaining
        """
        self._card["layout"] = layout
        return self

    def with_image_uris(self, image_uris: dict[str, str]) -> "CardBuilder":
        """Set the image URIs of the card.

        Args:
            image_uris: Dictionary with image variant URLs

        Returns:
            Self for method chaining
        """
        self._card["image_uris"] = image_uris
        return self

    def with_power_toughness(self, power: str, toughness: str) -> "CardBuilder":
        """Set power and toughness for creature cards.

        Args:
            power: Power value (can be *, X, or number)
            toughness: Toughness value (can be *, X, or number)

        Returns:
            Self for method chaining
        """
        self._card["power"] = power
        self._card["toughness"] = toughness
        return self

    def with_loyalty(self, loyalty: str) -> "CardBuilder":
        """Set loyalty for planeswalker cards.

        Args:
            loyalty: Starting loyalty value

        Returns:
            Self for method chaining
        """
        self._card["loyalty"] = loyalty
        return self

    def colorless(self) -> "CardBuilder":
        """Make this card colorless (empty colors array).

        Returns:
            Self for method chaining
        """
        self._card["colors"] = []
        self._card["color_identity"] = []
        self._card["mana_cost"] = ""
        return self

    def five_color(self) -> "CardBuilder":
        """Make this card five-color (WUBRG).

        Returns:
            Self for method chaining
        """
        self._card["colors"] = ["W", "U", "B", "R", "G"]
        self._card["color_identity"] = ["W", "U", "B", "R", "G"]
        return self

    def instant(self) -> "CardBuilder":
        """Make this card an instant.

        Returns:
            Self for method chaining
        """
        self._card["type_line"] = "Instant"
        return self

    def sorcery(self) -> "CardBuilder":
        """Make this card a sorcery.

        Returns:
            Self for method chaining
        """
        self._card["type_line"] = "Sorcery"
        return self

    def creature(self, power: str = "2", toughness: str = "2") -> "CardBuilder":
        """Make this card a creature with optional power/toughness.

        Args:
            power: Power value (default: "2")
            toughness: Toughness value (default: "2")

        Returns:
            Self for method chaining
        """
        self._card["type_line"] = "Creature"
        self._card["power"] = power
        self._card["toughness"] = toughness
        return self

    def artifact(self) -> "CardBuilder":
        """Make this card an artifact.

        Returns:
            Self for method chaining
        """
        self._card["type_line"] = "Artifact"
        return self

    def enchantment(self) -> "CardBuilder":
        """Make this card an enchantment.

        Returns:
            Self for method chaining
        """
        self._card["type_line"] = "Enchantment"
        return self

    def planeswalker(self, loyalty: str = "3") -> "CardBuilder":
        """Make this card a planeswalker with optional loyalty.

        Args:
            loyalty: Starting loyalty value (default: "3")

        Returns:
            Self for method chaining
        """
        self._card["type_line"] = "Planeswalker"
        self._card["loyalty"] = loyalty
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the card dictionary.

        Returns:
            Complete card dictionary with all configured values
        """
        return self._card.copy()
