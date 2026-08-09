"""Guards on the fixture documents pytest shares with the Playwright stub.

``web-app/e2e/stub/documents/reversible-cards.json`` is loaded by
``tests.fixtures.reversible_cards`` and by ``e2e/stub/fixtures.ts``. One copy,
two suites - which is the point, and also the risk: an edit made for the
frontend's benefit lands in the backend suite without anyone reading it.

Two things are asserted here. The first is that the file is committed at all,
after it was silently swallowed by the repository's ``data/`` ignore rule and
left a suite that passed locally and could not import on a fresh clone. The
second is the property both suites are built on: a ``reversible_card`` has no
top-level ``oracle_id``. If that ever stops being true of these documents,
every test about issue #22 quietly stops testing anything.
"""

import shutil
import subprocess

import pytest

from tests.fixtures.reversible_cards import (
    _FIXTURE_FILE,
    REVERSIBLE_SEARCH_TEXT,
    get_all_reversible_cards,
)


def test_shared_document_is_committed():
    """A fresh clone has to contain it, or this whole package fails to import."""
    if shutil.which("git") is None:
        pytest.skip("git is not available")

    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(_FIXTURE_FILE)],
        capture_output=True,
        text=True,
        cwd=_FIXTURE_FILE.parents[4],
        check=False,
    )

    assert result.returncode == 0, (
        f"{_FIXTURE_FILE} is not tracked by git. Check .gitignore - the root "
        f"file ignores 'data/' anywhere in the tree, which is why this "
        f"directory is called 'documents'."
    )


def test_reversible_documents_have_no_top_level_oracle_id():
    """The absence is the fixture. Present-and-null would not reproduce #22."""
    for card in get_all_reversible_cards():
        assert "oracle_id" not in card, f"{card['name']} gained a top-level oracle_id"


def test_every_face_carries_its_own_oracle_id():
    """The face id is the only key the grouping can use, so it has to be there."""
    for card in get_all_reversible_cards():
        faces = card["card_faces"]
        assert len(faces) == 2, f"{card['name']} is not two-faced"

        for face in faces:
            assert face["oracle_id"], f"a face of {card['name']} has no oracle_id"


def test_the_shared_query_matches_both_documents():
    """One term per card, so a single $text query returns exactly the two.

    The stub's matcher is an OR over terms for the same reason MongoDB's
    ``$text`` is. If this query stopped straddling both names, the pytest and
    Tier B suites would silently be searching for different things.
    """
    terms = REVERSIBLE_SEARCH_TEXT.lower().split()

    for card in get_all_reversible_cards():
        assert any(term in card["name"].lower() for term in terms), (
            f"{card['name']} is not matched by {REVERSIBLE_SEARCH_TEXT!r}"
        )
