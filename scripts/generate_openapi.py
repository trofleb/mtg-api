"""Write the API's OpenAPI document to openapi.json at the repo root.

The document is generated from *this checkout's* code, not from a running
server: ``api.main`` opens no database connection at import time, so
``app.openapi()`` works with no Mongo, no Meilisearch and no container.

It is committed rather than passed around as a CI artifact. A frontend-only
pull request skips the backend job entirely, so an artifact would not exist
when the web app needs a schema to generate types and stub responses from.
Committing it means the schema is always there, the backend job proves it is
current (``--check``), and a change to the API's contract shows up in the
diff where a reviewer can see it.

Usage::

    uv run python scripts/generate_openapi.py           # write
    uv run python scripts/generate_openapi.py --check    # fail if stale
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app  # noqa: E402

OPENAPI_PATH = PROJECT_ROOT / "openapi.json"


def render() -> str:
    """The document's canonical on-disk form.

    Keys are sorted so the file is a function of the API's shape alone.
    Without that, an unrelated reordering of route declarations or model
    fields would show up as a diff and the ``--check`` gate would cry wolf.
    """
    app.openapi_schema = None
    spec = app.openapi()
    app.openapi_schema = None
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def check() -> int:
    """Return 0 if the committed document matches the code, 1 otherwise."""
    expected = render()
    if not OPENAPI_PATH.exists():
        print(f"{OPENAPI_PATH} is missing. Run: just openapi", file=sys.stderr)
        return 1
    if OPENAPI_PATH.read_text() != expected:
        print(
            f"{OPENAPI_PATH.name} is out of date with the API. Run: just openapi",
            file=sys.stderr,
        )
        return 1
    return 0


def write() -> int:
    """Write the document, reporting whether anything changed."""
    rendered = render()
    changed = not OPENAPI_PATH.exists() or OPENAPI_PATH.read_text() != rendered
    OPENAPI_PATH.write_text(rendered)
    print(f"{'updated' if changed else 'unchanged'}: {OPENAPI_PATH}")
    return 0


def main() -> int:
    if "--check" in sys.argv[1:]:
        return check()
    return write()


if __name__ == "__main__":
    raise SystemExit(main())
