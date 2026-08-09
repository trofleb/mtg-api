import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from utils.api import all_sets, search_cards

# Page configuration
st.set_page_config(
    page_title="Magic the Gathering Card Search",
    page_icon="👋",
    layout="wide",
)

# Initialize session state
if "cards" not in st.session_state:
    st.session_state["cards"] = []
if "current_search" not in st.session_state:
    st.session_state["current_search"] = None
if "cursor" not in st.session_state:
    st.session_state["cursor"] = None
if "has_more" not in st.session_state:
    st.session_state["has_more"] = False
if "filters" not in st.session_state:
    st.session_state["filters"] = {}
if "search_history" not in st.session_state:
    st.session_state["search_history"] = []
if "selected_card" not in st.session_state:
    st.session_state["selected_card"] = None
if "total_results" not in st.session_state:
    st.session_state["total_results"] = 0

# Info banners
st.info(
    "Card info comes from the [Scryfall API](https://scryfall.com/docs/api). "
    "Thank you so much for all the data!"
)

st.title("Magic the Gathering Card Search")

# Search bar with history
col1, col2 = st.columns([4, 1])
with col1:
    search_text = st.text_input(
        "Search",
        value="Black Lotus",
        placeholder="Enter card name, text, or ability...",
        help="Search for cards by name, oracle text, or abilities",
    )

with col2:
    if st.session_state["search_history"]:
        st.markdown("<br>", unsafe_allow_html=True)  # Align with input
        history_display = st.selectbox(
            "Recent",
            options=[""] + st.session_state["search_history"][:10],
            label_visibility="collapsed",
        )
        if history_display and history_display != search_text:
            search_text = history_display
            st.rerun()

# Advanced filters
with st.expander("Advanced Filters", expanded=False):
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        # Set filter
        set_list = all_sets()
        selected_sets = st.multiselect(
            "Sets",
            set_list,
            help="Filter by specific MTG sets",
        )

        # Color filter
        st.write("**Colors**")
        color_cols = st.columns(5)
        selected_colors = []
        color_map = {
            "W": ("White", "⚪"),
            "U": ("Blue", "🔵"),
            "B": ("Black", "⚫"),
            "R": ("Red", "🔴"),
            "G": ("Green", "🟢"),
        }
        for i, (color_code, (color_name, emoji)) in enumerate(color_map.items()):
            with color_cols[i]:
                if st.checkbox(f"{emoji} {color_code}", key=f"color_{color_code}"):
                    selected_colors.append(color_code)

        color_operator = st.radio(
            "Color matching",
            options=["or", "and", "exactly"],
            horizontal=True,
            help="'or': any of selected colors, 'and': all selected colors, "
            "'exactly': only selected colors",
        )

        # Card type filter
        card_types = [
            "Creature",
            "Instant",
            "Sorcery",
            "Enchantment",
            "Artifact",
            "Planeswalker",
            "Land",
            "Battle",
        ]
        selected_types = st.multiselect(
            "Card Types",
            card_types,
            help="Filter by card type",
        )

    with filter_col2:
        # CMC filter
        st.write("**Mana Cost (CMC)**")
        cmc_range = st.slider(
            "CMC Range",
            min_value=0,
            max_value=16,
            value=(0, 16),
            help="Filter by converted mana cost",
        )
        cmc_min = cmc_range[0] if cmc_range[0] > 0 else None
        cmc_max = cmc_range[1] if cmc_range[1] < 16 else None

        # Rarity filter
        rarities = ["common", "uncommon", "rare", "mythic"]
        selected_rarities = st.multiselect(
            "Rarity",
            rarities,
            help="Filter by card rarity",
        )

    # Apply and clear buttons
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 3])
    with btn_col1:
        apply_filters = st.button(
            "Apply Filters", type="primary", use_container_width=True
        )
    with btn_col2:
        clear_filters = st.button("Clear All", use_container_width=True)

    if clear_filters:
        st.rerun()

# Stop if no search text
if not search_text:
    st.info("👆 Enter a search term to find Magic cards")
    st.stop()


# Function to perform search
def perform_search(cursor=None):
    """Perform card search with current filters."""
    # Build filters dict
    filters = {
        "selected_sets": selected_sets if selected_sets else None,
        "colors": selected_colors if selected_colors else None,
        "color_operator": color_operator if selected_colors else "or",
        "cmc_min": cmc_min,
        "cmc_max": cmc_max,
        "types": selected_types if selected_types else None,
        "rarities": selected_rarities if selected_rarities else None,
    }

    with st.spinner("Searching cards..." if not cursor else "Loading more cards..."):
        try:
            results = search_cards(
                text=search_text,
                cursor=cursor,
                **filters,
            )

            if "error" in results:
                st.error(f"Error searching cards: {results['error']}")
                return None

            return results
        except Exception as e:
            st.error(f"Failed to search cards: {str(e)}")
            return None


# Check if we need to perform a new search
filters_changed = (
    selected_sets,
    selected_colors,
    color_operator,
    cmc_min,
    cmc_max,
    selected_types,
    selected_rarities,
) != st.session_state.get("filters", {})

new_search = (
    search_text != st.session_state["current_search"]
    or apply_filters
    or filters_changed
)

if new_search:
    # Perform new search
    results = perform_search(cursor=None)
    if results:
        st.session_state["current_search"] = search_text
        st.session_state["cards"] = results["cards"]
        st.session_state["cursor"] = results["cursor"]
        st.session_state["has_more"] = results.get("has_more", False)
        st.session_state["total_results"] = len(results["cards"])
        st.session_state["filters"] = (
            selected_sets,
            selected_colors,
            color_operator,
            cmc_min,
            cmc_max,
            selected_types,
            selected_rarities,
        )

        # Add to search history
        if search_text and search_text not in st.session_state["search_history"]:
            st.session_state["search_history"].insert(0, search_text)
            st.session_state["search_history"] = st.session_state["search_history"][:20]

# Display results count
if st.session_state["cards"]:
    result_info_col1, result_info_col2, result_info_col3 = st.columns([2, 2, 1])
    with result_info_col1:
        count = len(st.session_state["cards"])
        more_text = "+" if st.session_state["has_more"] else ""
        st.write(f"**{count}{more_text} results found**")
    with result_info_col2:
        if st.session_state["has_more"]:
            st.caption("Scroll down and click 'Load More' to see additional cards")
    with result_info_col3:
        # Export button
        if st.button("📥 Export", help="Export search results"):
            export_data = []
            for card in st.session_state["cards"]:
                export_data.append(
                    {
                        "name": card.get("name", ""),
                        "type": card.get("type_line", ""),
                        "mana_cost": card.get("mana_cost", ""),
                        "cmc": card.get("cmc", 0),
                        "rarity": card.get("rarity", ""),
                        "oracle_text": card.get("card_text", ""),
                    }
                )

            # Create downloadable JSON
            json_str = json.dumps(export_data, indent=2)
            st.download_button(
                label="Download as JSON",
                data=json_str,
                file_name=f"mtg_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

            # Create downloadable CSV
            df = pd.DataFrame(export_data)
            csv_str = df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv_str,
                file_name=f"mtg_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

    st.divider()

if not st.session_state["cards"]:
    st.warning(
        "No cards found matching your search criteria. Try adjusting your filters."
    )
    st.stop()


# Card detail dialog
@st.dialog("Card Details", width="large")
def show_card_details(card):
    """Display detailed card information in a modal."""
    detail_col1, detail_col2 = st.columns([1, 2])

    with detail_col1:
        # Display card image(s)
        if card.get("thumbnail"):
            st.image(card["thumbnail"], use_container_width=True)
        elif card.get("faces_thumbnails"):
            for i, thumbnail in enumerate(card["faces_thumbnails"]):
                st.image(thumbnail, caption=f"Face {i + 1}", use_container_width=True)
        else:
            placeholder_path = (
                Path(__file__).parent.parent / "utils" / "Magic no image.png"
            )
            st.image(str(placeholder_path), use_container_width=True)

    with detail_col2:
        # Card name and type
        st.subheader(card.get("name", "Unknown Card"))
        st.write(f"**Type:** {card.get('type_line', 'N/A')}")

        # Mana cost and CMC
        if card.get("mana_cost"):
            st.write(f"**Mana Cost:** {card['mana_cost']}")
        st.write(f"**CMC:** {card.get('cmc', 'N/A')}")

        # Colors
        if card.get("colors"):
            colors_display = " ".join(card["colors"])
            st.write(f"**Colors:** {colors_display}")

        # Rarity
        if card.get("rarity"):
            st.write(f"**Rarity:** {card['rarity'].capitalize()}")

        st.divider()

        # Oracle text
        if card.get("card_text"):
            st.write("**Oracle Text:**")
            st.write(card["card_text"])

        # Printings info
        if card.get("card_count"):
            st.write(f"**Printings:** {card['card_count']}")

        # Rankings. No EDHREC rank: the ingestion deletes it from the card and
        # stores it in a dated collection of its own, so the API never sends
        # one and this branch had never rendered.
        if card.get("penny_rank"):
            st.write(f"**Penny Rank:** #{card['penny_rank']}")

        st.divider()

        # All printings
        if card.get("cards"):
            with st.expander(f"View All {len(card['cards'])} Printings"):
                for printing in card["cards"]:
                    print_col1, print_col2 = st.columns([1, 3])
                    with print_col1:
                        if printing.get("image_uris", {}).get("small"):
                            st.image(
                                printing["image_uris"]["small"],
                                width=100,
                            )
                    with print_col2:
                        st.write(f"**{printing.get('set_name', 'Unknown Set')}**")
                        st.caption(f"Set: {printing.get('set', 'N/A').upper()}")
                        st.caption(f"Released: {printing.get('released_at', 'N/A')}")
                    st.divider()


# Display cards in responsive grid
# Determine grid columns based on screen size (approximation)
num_cols = st.columns(1)  # Default
container_width = st.session_state.get("container_width", 1200)

# Responsive grid: 2 cols on mobile, 3 on tablet, 4 on desktop
if container_width < 768:
    grid_cols = 2
elif container_width < 1024:
    grid_cols = 3
else:
    grid_cols = 4

cols = st.columns(grid_cols)

for i, oracle_card in enumerate(st.session_state["cards"]):
    col = cols[i % grid_cols]
    with col:
        # Card container
        with st.container():
            # Card name (truncated)
            card_name = oracle_card.get("name", "Unknown")
            st.markdown(
                f"<div style='text-overflow: ellipsis; white-space: nowrap; "
                f"overflow: hidden; font-weight: bold; margin-bottom: 5px;'>"
                f"{card_name}</div>",
                unsafe_allow_html=True,
            )

            # Card image with click handler
            if oracle_card.get("thumbnail"):
                st.image(oracle_card["thumbnail"], use_container_width=True)
            elif oracle_card.get("faces_thumbnails"):
                thumbnail = oracle_card["faces_thumbnails"][0]
                st.image(thumbnail, use_container_width=True)
            else:
                # Use absolute path for placeholder
                placeholder_path = (
                    Path(__file__).parent.parent / "utils" / "Magic no image.png"
                )
                if placeholder_path.exists():
                    st.image(str(placeholder_path), use_container_width=True)
                else:
                    st.write("No image available")

            # Card info row
            info_parts = []
            if oracle_card.get("mana_cost"):
                info_parts.append(oracle_card["mana_cost"])
            if oracle_card.get("rarity"):
                rarity_emoji = {
                    "common": "⚪",
                    "uncommon": "🔵",
                    "rare": "🟡",
                    "mythic": "🔴",
                }.get(oracle_card["rarity"], "⚪")
                info_parts.append(f"{rarity_emoji}")

            if info_parts:
                st.caption(" | ".join(info_parts))

            # View details button
            if st.button("View Details", key=f"card_{i}", use_container_width=True):
                show_card_details(oracle_card)

        st.markdown("<br>", unsafe_allow_html=True)

# Pagination - Load more button
if st.session_state["has_more"]:
    st.divider()
    _, load_col, _ = st.columns([2, 1, 2])
    with load_col:
        if st.button("Load More Cards", type="primary", use_container_width=True):
            # Load more results
            results = perform_search(cursor=st.session_state["cursor"])
            if results:
                st.session_state["cards"].extend(results["cards"])
                st.session_state["cursor"] = results["cursor"]
                st.session_state["has_more"] = results.get("has_more", False)
                st.rerun()
else:
    if st.session_state["cards"]:
        st.divider()
        st.caption("All matching cards have been loaded.")
