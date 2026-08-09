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

**The documents themselves no longer live here.** They moved to
``web-app/e2e/stub/documents/reversible-cards.json`` when the e2e tier split
landed, and this module now loads that file. The MSW stub that backs Playwright
Tier B builds its fixtures from the same JSON, so pytest and Tier B cannot end
up disagreeing about what a reversible card looks like - which is the only
reason a Python module reads a file out of ``web-app/``.

Editing the JSON therefore changes both suites at once. ``ci.yml``'s ``backend``
paths-filter includes that file so this suite re-runs when it does.

The directory is ``documents/`` and not ``data/`` because the repository's
root ``.gitignore`` ignores ``data/`` anywhere in the tree - which silently
kept this file out of the first commit that added it, leaving a suite that
passed locally and could not even import on a fresh clone.
"""

import json
from pathlib import Path

# tests/fixtures/reversible_cards.py -> repository root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_FILE = (
    _REPO_ROOT / "web-app" / "e2e" / "stub" / "documents" / "reversible-cards.json"
)

_DOCUMENT = json.loads(_FIXTURE_FILE.read_text())

REVERSIBLE_PROPAGANDA, REVERSIBLE_COMMAND_TOWER = _DOCUMENT["cards"]

# A term present in both names and in nothing else in the sample set, so a
# single $text query returns exactly the two reversible cards. MongoDB's
# $text is an OR over terms, so "propaganda tower" matches both.
REVERSIBLE_SEARCH_TEXT: str = _DOCUMENT["search_text"]


def get_all_reversible_cards() -> list[dict]:
    """Get every reversible-layout sample card.

    Returns:
        List of card dictionaries, none of which carries a top-level oracle_id.
    """
    return [REVERSIBLE_PROPAGANDA, REVERSIBLE_COMMAND_TOWER]
