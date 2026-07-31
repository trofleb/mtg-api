"""Tests for CardBuilder test data builder.

This module tests that the CardBuilder fluent API correctly
constructs test card objects.
"""

from tests.utils.builders import CardBuilder


class TestCardBuilderDefaults:
    """Test default card construction."""

    def test_default_build_creates_valid_card(self):
        """Default build should create a card with all required fields."""
        card = CardBuilder().build()

        # Core fields
        assert "id" in card
        assert "oracle_id" in card
        assert "name" in card
        assert card["name"] == "Test Card"

        # Gameplay fields
        assert card["cmc"] == 2
        assert card["colors"] == ["U"]
        assert card["type_line"] == "Instant"

        # Set info
        assert card["set"] == "TST"
        assert card["rarity"] == "common"

        # Image URIs
        assert "image_uris" in card
        assert len(card["image_uris"]) == 6

    def test_build_returns_copy(self):
        """Build should return a copy, not the internal dict."""
        builder = CardBuilder()
        card1 = builder.build()
        card2 = builder.build()

        # Modifying one shouldn't affect the other
        card1["name"] = "Modified"
        assert card2["name"] == "Test Card"


class TestCardBuilderFluentApi:
    """Test fluent API methods."""

    def test_with_name(self):
        """Should set card name."""
        card = CardBuilder().with_name("Lightning Bolt").build()
        assert card["name"] == "Lightning Bolt"

    def test_with_colors(self):
        """Should set card colors and color identity."""
        card = CardBuilder().with_colors(["R", "U"]).build()
        assert card["colors"] == ["R", "U"]
        assert card["color_identity"] == ["R", "U"]

    def test_with_cmc(self):
        """Should set converted mana cost."""
        card = CardBuilder().with_cmc(5).build()
        assert card["cmc"] == 5

    def test_with_cmc_float(self):
        """Should accept float CMC."""
        card = CardBuilder().with_cmc(2.5).build()
        assert card["cmc"] == 2.5

    def test_with_rarity(self):
        """Should set rarity."""
        card = CardBuilder().with_rarity("mythic").build()
        assert card["rarity"] == "mythic"

    def test_with_type_line(self):
        """Should set type line."""
        card = CardBuilder().with_type_line("Legendary Creature — Dragon").build()
        assert card["type_line"] == "Legendary Creature — Dragon"

    def test_with_set(self):
        """Should set set code and name."""
        card = CardBuilder().with_set("MH2", "Modern Horizons 2").build()
        assert card["set"] == "MH2"
        assert card["set_name"] == "Modern Horizons 2"

    def test_with_set_defaults_name(self):
        """Should default set_name to set code."""
        card = CardBuilder().with_set("MH2").build()
        assert card["set"] == "MH2"
        assert card["set_name"] == "MH2"

    def test_with_oracle_text(self):
        """Should set oracle text."""
        card = CardBuilder().with_oracle_text("Draw a card.").build()
        assert card["oracle_text"] == "Draw a card."

    def test_with_mana_cost(self):
        """Should set mana cost."""
        card = CardBuilder().with_mana_cost("{2}{R}{R}").build()
        assert card["mana_cost"] == "{2}{R}{R}"

    def test_with_lang(self):
        """Should set language."""
        card = CardBuilder().with_lang("fr").build()
        assert card["lang"] == "fr"

    def test_with_released_at(self):
        """Should set release date."""
        card = CardBuilder().with_released_at("2024-12-25").build()
        assert card["released_at"] == "2024-12-25"

    def test_with_artist(self):
        """Should set artist."""
        card = CardBuilder().with_artist("John Avon").build()
        assert card["artist"] == "John Avon"

    def test_with_layout(self):
        """Should set layout."""
        card = CardBuilder().with_layout("transform").build()
        assert card["layout"] == "transform"

    def test_with_image_uris(self):
        """Should set custom image URIs."""
        custom_uris = {
            "small": "https://custom.com/small.jpg",
            "normal": "https://custom.com/normal.jpg",
            "large": "https://custom.com/large.jpg",
            "png": "https://custom.com/card.png",
            "art_crop": "https://custom.com/art.jpg",
            "border_crop": "https://custom.com/border.jpg",
        }
        card = CardBuilder().with_image_uris(custom_uris).build()
        assert card["image_uris"] == custom_uris

    def test_with_power_toughness(self):
        """Should set power and toughness for creatures."""
        card = CardBuilder().with_power_toughness("3", "4").build()
        assert card["power"] == "3"
        assert card["toughness"] == "4"

    def test_with_loyalty(self):
        """Should set loyalty for planeswalkers."""
        card = CardBuilder().with_loyalty("5").build()
        assert card["loyalty"] == "5"


class TestCardBuilderConvenienceMethods:
    """Test convenience methods for common card types."""

    def test_colorless(self):
        """Should create colorless card."""
        card = CardBuilder().colorless().build()
        assert card["colors"] == []
        assert card["color_identity"] == []
        assert card["mana_cost"] == ""

    def test_five_color(self):
        """Should create five-color card."""
        card = CardBuilder().five_color().build()
        assert card["colors"] == ["W", "U", "B", "R", "G"]
        assert card["color_identity"] == ["W", "U", "B", "R", "G"]

    def test_instant(self):
        """Should create instant."""
        card = CardBuilder().instant().build()
        assert card["type_line"] == "Instant"

    def test_sorcery(self):
        """Should create sorcery."""
        card = CardBuilder().sorcery().build()
        assert card["type_line"] == "Sorcery"

    def test_creature(self):
        """Should create creature with default P/T."""
        card = CardBuilder().creature().build()
        assert card["type_line"] == "Creature"
        assert card["power"] == "2"
        assert card["toughness"] == "2"

    def test_creature_with_custom_pt(self):
        """Should create creature with custom P/T."""
        card = CardBuilder().creature(power="5", toughness="7").build()
        assert card["type_line"] == "Creature"
        assert card["power"] == "5"
        assert card["toughness"] == "7"

    def test_artifact(self):
        """Should create artifact."""
        card = CardBuilder().artifact().build()
        assert card["type_line"] == "Artifact"

    def test_enchantment(self):
        """Should create enchantment."""
        card = CardBuilder().enchantment().build()
        assert card["type_line"] == "Enchantment"

    def test_planeswalker(self):
        """Should create planeswalker with default loyalty."""
        card = CardBuilder().planeswalker().build()
        assert card["type_line"] == "Planeswalker"
        assert card["loyalty"] == "3"

    def test_planeswalker_with_custom_loyalty(self):
        """Should create planeswalker with custom loyalty."""
        card = CardBuilder().planeswalker(loyalty="6").build()
        assert card["type_line"] == "Planeswalker"
        assert card["loyalty"] == "6"


class TestCardBuilderChaining:
    """Test method chaining capabilities."""

    def test_method_chaining(self):
        """Should support chaining multiple methods."""
        card = (
            CardBuilder()
            .with_name("Chained Card")
            .with_colors(["R", "G"])
            .with_cmc(4)
            .with_rarity("rare")
            .creature(power="4", toughness="4")
            .build()
        )

        assert card["name"] == "Chained Card"
        assert card["colors"] == ["R", "G"]
        assert card["cmc"] == 4
        assert card["rarity"] == "rare"
        assert card["type_line"] == "Creature"
        assert card["power"] == "4"

    def test_complex_chaining(self):
        """Should support complex method chains."""
        card = (
            CardBuilder()
            .with_name("Complex Card")
            .with_oracle_id("550c74d4-a843-4208-a3c2-c71e84a21979")
            .with_colors(["W", "U", "B"])
            .with_cmc(6)
            .with_type_line("Legendary Creature — Angel")
            .with_rarity("mythic")
            .with_set("MH2", "Modern Horizons 2")
            .with_power_toughness("5", "5")
            .build()
        )

        assert card["name"] == "Complex Card"
        assert card["oracle_id"] == "550c74d4-a843-4208-a3c2-c71e84a21979"
        assert card["colors"] == ["W", "U", "B"]
        assert card["cmc"] == 6
        assert card["set"] == "MH2"
        assert card["power"] == "5"


class TestCardBuilderEdgeCases:
    """Test edge cases and special scenarios."""

    def test_colorless_artifact(self):
        """Should create colorless artifact."""
        card = (
            CardBuilder()
            .colorless()
            .artifact()
            .with_name("Sol Ring")
            .with_cmc(1)
            .build()
        )

        assert card["name"] == "Sol Ring"
        assert card["colors"] == []
        assert card["type_line"] == "Artifact"
        assert card["cmc"] == 1

    def test_five_color_legendary(self):
        """Should create five-color legendary creature."""
        card = (
            CardBuilder()
            .five_color()
            .with_name("Progenitus")
            .with_type_line("Legendary Creature — Hydra Avatar")
            .with_cmc(10)
            .with_power_toughness("10", "10")
            .with_rarity("mythic")
            .build()
        )

        assert card["name"] == "Progenitus"
        assert card["colors"] == ["W", "U", "B", "R", "G"]
        assert card["cmc"] == 10
        assert card["power"] == "10"

    def test_zero_cmc(self):
        """Should support zero CMC."""
        card = CardBuilder().with_name("Black Lotus").colorless().with_cmc(0).build()

        assert card["name"] == "Black Lotus"
        assert card["cmc"] == 0
        assert card["colors"] == []

    def test_high_cmc(self):
        """Should support very high CMC."""
        card = CardBuilder().with_name("Emrakul").with_cmc(15).build()
        assert card["cmc"] == 15
