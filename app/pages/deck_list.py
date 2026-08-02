import streamlit as st
from requests import get
from utils.parse_cards import CardSearch, parse_deck_string

st.set_page_config(
    page_title="MTG Deck list",
    page_icon="👋",
)

st.title("MTG Deck list")
st.info(
    "Card info comes from the [Scryfall API](https://scryfall.com/docs/api). Thank you so much for all the data !"
)


# st.warning("This is a work in progress, please don't share the link yet.")
# st.stop()


@st.cache_data
def get_card(info: CardSearch):
    map_to_params = {
        "set": "set",
        "num": "collector_number",
        # "special": "special",
        # "foil": "foil",
    }
    response = get(
        f"http://api:8000/cards/{info['name']}",
        params={
            map_to_params[key]: info[key]
            for key in info
            if key in map_to_params and info[key]
        },
    )

    # An unknown card is a 404 whose body is an error object, which is truthy.
    # Return None so the caller's "Could not find" check still works.
    if response.status_code == 404:
        return None

    return response.json()


deck_list = st.text_area("Deck list")

if not deck_list:
    st.stop()
    st.info("Please paste a deck list in the text area above.")

deck = parse_deck_string(deck_list)["deck_list"]


card_list = [(card_info, get_card(card_info)) for card_info in deck]

missing_cards = [card_info["name"] for card_info, card in card_list if not card]
if missing_cards:
    st.warning(f"Could not find: {', '.join(missing_cards)}")

width = 3
cols = st.columns(width)
for i, card in enumerate([card for card in card_list if card[1]]):
    card_info, oracle_card = card
    col = cols[i % width]
    with col:
        st.html(
            f'<div style="text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">{card_info["name"]}</div>',
        )
        # st.write(oracle_card)
        if oracle_card.get("thumbnail"):
            st.image(oracle_card["thumbnail"], use_container_width=True)
        elif oracle_card.get("faces_thumbnails"):
            thumbnail = oracle_card["faces_thumbnails"][0]
            st.image(thumbnail, use_container_width=True)
        else:
            st.image("./utils/Magic no image.png", use_container_width=True)
