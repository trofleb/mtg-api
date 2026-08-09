"""Field-path and aggregation-expression evaluation for the MongoDB mock.

Split out of ``mongodb.py`` to keep that module from growing further: these
are pure functions over plain dictionaries with no knowledge of collections,
cursors or pipelines.

What they exist for: ``CARD_PROJECTION`` is not a list of 0/1 flags. It
computes ``thumbnail`` from ``"$image_uris.normal"``, ``faces_thumbnails``
from ``"$card_faces.image_uris.normal"``, and - since issue #22 -
``oracle_id`` through an ``$ifNull``/``$arrayElemAt`` fallback onto the card
faces. A mock that ignores those values cannot tell a working projection
from a broken one.
"""

from typing import Any


class _Missing:
    """Sentinel for a field that is absent, as opposed to present and null.

    MongoDB draws this distinction and both ``$ifNull`` and ``$exists`` turn
    on it, so collapsing "absent" onto ``None`` would make them untestable.
    """

    def __repr__(self) -> str:
        return "<missing>"


MISSING = _Missing()


def resolve_path(doc: Any, path: str) -> Any:
    """Resolve a dotted field path, mapping over arrays as MongoDB does.

    Crossing an array of subdocuments maps rather than indexes, so
    ``"card_faces.image_uris.normal"`` yields a list of image URLs.

    Args:
        doc: Document, or any intermediate value, to read from.
        path: Dotted field path, without a leading "$".

    Returns:
        The value at the path, a list of values when the path crosses an
        array of subdocuments, or :data:`MISSING` when it does not exist.
    """
    current: Any = doc
    for part in path.split("."):
        if isinstance(current, list):
            current = [
                item[part]
                for item in current
                if isinstance(item, dict) and part in item
            ]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return MISSING
    return current


def resolve_expression(expression: Any, doc: dict) -> Any:
    """Evaluate an aggregation expression against a document.

    Args:
        expression: Field path ("$a.b"), operator document, or literal.
        doc: Document to evaluate against.

    Returns:
        The expression's value, or :data:`MISSING` when it resolves to
        nothing - which a projection turns into an absent field.

    Raises:
        ValueError: For an operator this mock does not implement, so an
            unsupported expression fails loudly rather than yielding None
            and quietly making a test pass.
    """
    if isinstance(expression, str) and expression.startswith("$"):
        return resolve_path(doc, expression[1:])

    if isinstance(expression, dict) and len(expression) == 1:
        operator, arguments = next(iter(expression.items()))

        if operator == "$ifNull":
            for candidate in arguments:
                value = resolve_expression(candidate, doc)
                if value is not MISSING and value is not None:
                    return value
            return MISSING

        if operator == "$arrayElemAt":
            array = resolve_expression(arguments[0], doc)
            index = resolve_expression(arguments[1], doc)
            if not isinstance(array, list) or not isinstance(index, int):
                return MISSING
            try:
                return array[index]
            except IndexError:
                return MISSING

        if operator.startswith("$"):
            raise ValueError(
                f"MockMongoCollection does not support the {operator!r} expression"
            )

    return expression


def read_field(doc: dict, field: str) -> Any:
    """Read a query field from a document, following dotted paths.

    Args:
        doc: Document to read from.
        field: Field name, possibly dotted.

    Returns:
        The field's value, or None when absent - matching the None that
        ``doc.get`` returned before, so operator handling is unchanged.
    """
    value = resolve_path(doc, field)
    return None if value is MISSING else value
