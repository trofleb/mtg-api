"""Custom MongoDB mock classes for testing.

This module provides in-memory mock implementations of MongoDB cursor and
collection classes, enabling fast integration tests without external dependencies.

Supports MongoDB query operators: $regex, $in, $nin, $all, $size, $gte, $lte, $text, $search, $or, $and, $exists, $eq
Supports aggregation stages: $match, $project, $group, $sort, $limit
Supports projection expressions: {"$meta": "textScore"}

Deliberate fidelity choices, so tests cannot pass for the wrong reason:

- ``{"$project": {"score": 1}}`` projects the document's own ``score`` field.
  Card documents have none, so the field comes back absent -- exactly as in
  MongoDB. Only ``{"$meta": "textScore"}`` produces a relevance score.
- ``$max`` over a field no document carries yields ``None``, not an absent
  field, so ``f"{score}:{id}"`` cursors read ``"None:<id>"`` as in production.
- ``$sort`` never raises on ``None`` or mixed types; it orders them the way
  BSON does (null first ascending).
"""

import re
from copy import deepcopy
from typing import Any, Optional

# Relative field weights of the mock text index. The card name dominates, as
# in a MongoDB text index whose `name` field carries the highest weight.
_TEXT_FIELD_WEIGHTS = {
    "name": 10.0,
    "printed_name": 8.0,
    "type_line": 3.0,
    "oracle_text": 1.0,
    "flavor_text": 0.5,
    "set_name": 0.5,
}

_WORD_RE = re.compile(r"[\w']+")


def _tokenize(value: Any) -> list[str]:
    """Split a value into lowercase word tokens.

    Args:
        value: Any value; non-strings are stringified first.

    Returns:
        List of lowercase word tokens.
    """
    if value is None:
        return []
    return _WORD_RE.findall(str(value).lower())


def _sort_key(value: Any) -> tuple[int, Any]:
    """Build a total-order sort key mirroring BSON type ordering.

    MongoDB sorts null before numbers before strings and never raises on
    mixed types, while plain Python comparison would.

    Args:
        value: Field value to build a key for.

    Returns:
        (type rank, comparable value) tuple.
    """
    if value is None:
        return (0, 0)
    if isinstance(value, bool):
        return (3, value)
    if isinstance(value, (int, float)):
        return (1, value)
    if isinstance(value, str):
        return (2, value)
    return (4, str(value))


def _extract_search_text(query: Optional[dict]) -> Optional[str]:
    """Find the $text search string in a query, recursing into $or/$and.

    Args:
        query: MongoDB query dictionary.

    Returns:
        The $search string, or None when the query has no $text clause.
    """
    if not isinstance(query, dict):
        return None
    for field, condition in query.items():
        if field == "$text" and isinstance(condition, dict):
            return condition.get("$search")
        if field in ("$or", "$and") and isinstance(condition, list):
            for sub_query in condition:
                found = _extract_search_text(sub_query)
                if found is not None:
                    return found
    return None


class MockMongoCursor:
    """Mock MongoDB cursor supporting sort, limit, and iteration."""

    def __init__(self, documents: list[dict]):
        """Initialize cursor with documents.

        Args:
            documents: List of document dictionaries.
        """
        self._documents = deepcopy(documents)
        self._position = 0

    def sort(self, field: str, direction: int) -> "MockMongoCursor":
        """Sort documents by field.

        Args:
            field: Field name to sort by.
            direction: 1 for ascending, -1 for descending.

        Returns:
            Self for method chaining.
        """
        reverse = direction == -1
        self._documents.sort(key=lambda doc: _sort_key(doc.get(field)), reverse=reverse)
        return self

    def limit(self, count: int) -> "MockMongoCursor":
        """Limit number of documents.

        Args:
            count: Maximum number of documents to return.

        Returns:
            Self for method chaining.
        """
        self._documents = self._documents[:count]
        return self

    def __iter__(self):
        """Make cursor iterable."""
        self._position = 0
        return self

    def __next__(self):
        """Get next document in iteration."""
        if self._position >= len(self._documents):
            raise StopIteration
        document = self._documents[self._position]
        self._position += 1
        return document


class MockMongoCollection:
    """Mock MongoDB collection supporting find, find_one, and aggregate."""

    def __init__(self, documents: list[dict]):
        """Initialize collection with documents.

        Args:
            documents: List of document dictionaries.
        """
        self._documents = deepcopy(documents)
        self._last_search_text = None  # Track last text search for scoring

    def find_one(
        self, query: dict, projection: Optional[dict] = None
    ) -> Optional[dict]:
        """Find single document matching query.

        Args:
            query: MongoDB query dictionary.
            projection: Fields to include/exclude.

        Returns:
            Matching document or None.
        """
        self._last_search_text = _extract_search_text(query)
        for doc in self._documents:
            if self._matches_query(doc, query):
                return self._project(doc, projection)
        return None

    def find(self, query: dict, projection: Optional[dict] = None) -> MockMongoCursor:
        """Find all documents matching query.

        Args:
            query: MongoDB query dictionary.
            projection: Fields to include/exclude.

        Returns:
            MockMongoCursor with matching documents.
        """
        self._last_search_text = _extract_search_text(query)
        matching_docs = [
            self._project(doc, projection)
            for doc in self._documents
            if self._matches_query(doc, query)
        ]
        return MockMongoCursor(matching_docs)

    def aggregate(self, pipeline: list[dict]) -> MockMongoCursor:
        """Execute aggregation pipeline.

        Args:
            pipeline: List of aggregation stage dictionaries.

        Returns:
            MockMongoCursor with aggregation results.
        """
        # Each pipeline is self-contained: a $text query from an earlier call
        # must not silently score this one.
        self._last_search_text = None
        documents = deepcopy(self._documents)

        for stage in pipeline:
            documents = self._execute_aggregation_stage(documents, stage)

        return MockMongoCursor(documents)

    def _matches_query(self, doc: dict, query: dict) -> bool:
        """Check if document matches query.

        Args:
            doc: Document to check.
            query: Query dictionary.

        Returns:
            True if document matches query.
        """
        if not query:
            return True

        for field, condition in query.items():
            # Handle special operators
            if field == "$or":
                if not any(
                    self._matches_query(doc, sub_query) for sub_query in condition
                ):
                    return False
            elif field == "$and":
                if not all(
                    self._matches_query(doc, sub_query) for sub_query in condition
                ):
                    return False
            elif field == "$text":
                # Text search: MongoDB matches a document carrying ANY of the
                # query terms, so a multi-word query is not a phrase match.
                terms = _tokenize(condition.get("$search", ""))
                doc_text = str(doc).lower()
                if terms and not any(term in doc_text for term in terms):
                    return False
            elif isinstance(condition, dict):
                # Field with operators
                field_value = doc.get(field)

                for operator, value in condition.items():
                    if operator == "$regex":
                        if field_value is None:
                            return False
                        if not re.search(value, str(field_value), re.IGNORECASE):
                            return False
                    elif operator == "$in":
                        # Handle list fields (e.g., colors): check if ANY element matches
                        if isinstance(field_value, list):
                            if not any(item in value for item in field_value):
                                return False
                        # Handle scalar fields: check if value itself is in list
                        else:
                            if field_value not in value:
                                return False
                    elif operator == "$nin":
                        if field_value in value:
                            return False
                    elif operator == "$all":
                        if not isinstance(field_value, list):
                            return False
                        if not all(item in field_value for item in value):
                            return False
                    elif operator == "$size":
                        if not isinstance(field_value, list):
                            return False
                        if len(field_value) != value:
                            return False
                    elif operator == "$gt":
                        if field_value is None or field_value <= value:
                            return False
                    elif operator == "$gte":
                        if field_value is None or field_value < value:
                            return False
                    elif operator == "$lt":
                        if field_value is None or field_value >= value:
                            return False
                    elif operator == "$lte":
                        if field_value is None or field_value > value:
                            return False
                    elif operator == "$exists":
                        exists = field in doc
                        if exists != value:
                            return False
                    elif operator == "$eq":
                        if field_value != value:
                            return False
            else:
                # Direct field match
                if doc.get(field) != condition:
                    return False

        return True

    def _project(self, doc: dict, projection: Optional[dict]) -> dict:
        """Project a document, resolving any {"$meta": ...} expressions.

        Args:
            doc: Document to project.
            projection: Projection dictionary, possibly with $meta fields.

        Returns:
            Projected document.
        """
        if not projection:
            return deepcopy(doc)

        meta_fields = {
            field: spec["$meta"]
            for field, spec in projection.items()
            if isinstance(spec, dict) and "$meta" in spec
        }
        plain = {
            field: spec
            for field, spec in projection.items()
            if field not in meta_fields
        }

        result = self._apply_projection(doc, plain)
        for field, meta_kind in meta_fields.items():
            result[field] = self._resolve_meta(meta_kind, doc)
        return result

    def _resolve_meta(self, meta_kind: str, doc: dict) -> float:
        """Resolve a $meta expression for a document.

        Args:
            meta_kind: The $meta keyword, e.g. "textScore".
            doc: Source document.

        Returns:
            The metadata value.

        Raises:
            ValueError: For unsupported keywords, or for "textScore" when the
                query ran no $text search -- MongoDB errors there too.
        """
        if meta_kind != "textScore":
            raise ValueError(
                f"MockMongoCollection does not support $meta {meta_kind!r}"
            )
        if self._last_search_text is None:
            raise ValueError(
                'query requires "textScore" metadata, '
                "but no $text search ran in this query"
            )
        return self._calculate_text_score(doc, self._last_search_text)

    def _apply_projection(self, doc: dict, projection: dict) -> dict:
        """Apply projection to document.

        Args:
            doc: Document to project.
            projection: Projection dictionary.

        Returns:
            Projected document.
        """
        result = {}

        # Check if it's inclusion or exclusion projection
        is_inclusion = any(v == 1 for k, v in projection.items() if k != "_id")

        for field, include in projection.items():
            if include == 1:
                if field in doc:
                    result[field] = deepcopy(doc[field])
            elif include == 0 and not is_inclusion:
                # Exclusion mode
                result = {k: deepcopy(v) for k, v in doc.items() if k != field}

        # If inclusion mode, add all included fields
        if is_inclusion:
            for field in projection:
                if projection[field] == 1 and field in doc:
                    result[field] = deepcopy(doc[field])

        # Handle _id special case (included by default unless explicitly excluded)
        if "_id" not in projection or projection.get("_id") != 0:
            if "_id" in doc and "_id" not in result:
                result["_id"] = deepcopy(doc["_id"])

        return result

    def _execute_aggregation_stage(
        self, documents: list[dict], stage: dict
    ) -> list[dict]:
        """Execute single aggregation stage.

        Args:
            documents: Current documents.
            stage: Aggregation stage dictionary.

        Returns:
            Documents after applying stage.
        """
        stage_type = list(stage.keys())[0]
        stage_spec = stage[stage_type]

        if stage_type == "$match":
            # Remember any $text query so a later $meta stage can score it.
            # Read from the query itself, not from matched documents, so an
            # empty collection still knows a text search ran.
            self._last_search_text = (
                _extract_search_text(stage_spec) or self._last_search_text
            )
            return [doc for doc in documents if self._matches_query(doc, stage_spec)]

        elif stage_type == "$project":
            # A plain {"field": 1} projects the document's own field; only
            # {"$meta": "textScore"} produces a relevance score.
            return [self._project(doc, stage_spec) for doc in documents]

        elif stage_type == "$group":
            # Group documents
            return self._execute_group_stage(documents, stage_spec)

        elif stage_type == "$sort":
            # Stable sort, least significant field first: this supports mixed
            # directions and never compares incompatible types directly.
            ordered = list(documents)
            for field, direction in reversed(list(stage_spec.items())):
                ordered.sort(
                    key=lambda doc, field=field: _sort_key(doc.get(field)),
                    reverse=(direction == -1),
                )
            return ordered

        elif stage_type == "$limit":
            # Limit documents
            return documents[:stage_spec]

        else:
            # Unsupported stage - return as is
            return documents

    def _execute_group_stage(
        self, documents: list[dict], group_spec: dict
    ) -> list[dict]:
        """Execute $group aggregation stage.

        Args:
            documents: Documents to group.
            group_spec: Group specification.

        Returns:
            Grouped documents.
        """
        # Simple grouping implementation
        groups: dict[Any, dict] = {}
        group_id = group_spec.get("_id")

        for doc in documents:
            # Determine group key
            if isinstance(group_id, str) and group_id.startswith("$"):
                key = doc.get(group_id[1:])
            else:
                key = group_id

            if key not in groups:
                groups[key] = {"_id": key}

            # Apply accumulators
            for field, accumulator in group_spec.items():
                if field == "_id":
                    continue

                if isinstance(accumulator, dict):
                    acc_type = list(accumulator.keys())[0]
                    acc_value = accumulator[acc_type]

                    if acc_type == "$first":
                        if field not in groups[key]:
                            field_name = (
                                acc_value[1:]
                                if acc_value.startswith("$")
                                else acc_value
                            )
                            groups[key][field] = doc.get(field_name)

                    elif acc_type == "$sum":
                        if field not in groups[key]:
                            groups[key][field] = 0
                        if acc_value == 1:
                            groups[key][field] += 1
                        else:
                            field_name = (
                                acc_value[1:]
                                if acc_value.startswith("$")
                                else acc_value
                            )
                            groups[key][field] += doc.get(field_name, 0)

                    elif acc_type == "$max":
                        field_name = (
                            acc_value[1:] if acc_value.startswith("$") else acc_value
                        )
                        current_value = doc.get(field_name)
                        # MongoDB emits null when no document carries a value,
                        # rather than omitting the field.
                        best = groups[key].setdefault(field, None)
                        if current_value is not None and (
                            best is None or _sort_key(current_value) > _sort_key(best)
                        ):
                            groups[key][field] = current_value

                    elif acc_type == "$addToSet":
                        if field not in groups[key]:
                            groups[key][field] = []
                        if acc_value == "$$ROOT":
                            if doc not in groups[key][field]:
                                groups[key][field].append(deepcopy(doc))
                        else:
                            field_name = (
                                acc_value[1:]
                                if acc_value.startswith("$")
                                else acc_value
                            )
                            value = doc.get(field_name)
                            if value not in groups[key][field]:
                                groups[key][field].append(value)

        return list(groups.values())

    def _calculate_text_score(self, doc: dict, search_text: str) -> float:
        """Calculate a deterministic mock of MongoDB's $text relevance score.

        Each weighted field contributes term *density* (how much of the field
        the query terms cover) times term *coverage* (how many of the query's
        terms the field matches). So a card whose whole name is the query
        outscores one that merely mentions a term, and documents of differing
        relevance get differing scores -- which is what makes ordering by the
        score observable through $sort.

        Two documents with identical relevance profiles score identically,
        as they would in MongoDB.

        Args:
            doc: Document to score.
            search_text: Search query text.

        Returns:
            Non-negative relevance score; 0.0 when nothing matches.
        """
        terms = _tokenize(search_text)
        if not terms:
            return 0.0

        score = 0.0
        for field, weight in _TEXT_FIELD_WEIGHTS.items():
            words = _tokenize(doc.get(field))
            if not words:
                continue
            hits = sum(1 for word in words for term in terms if term in word)
            if not hits:
                continue
            matched = sum(1 for term in terms if any(term in word for word in words))
            score += weight * (hits / len(words)) * (matched / len(terms))

        return round(score, 6)
