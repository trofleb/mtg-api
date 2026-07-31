# MongoDB Mocking Strategy for FastAPI Testing

## Table of Contents

1. [Overview](#overview)
2. [Mocking Approaches Comparison](#mocking-approaches-comparison)
3. [Recommended Approach](#recommended-approach)
4. [Implementation Guide](#implementation-guide)
5. [mongomock Library](#mongomock-library)
6. [Custom Mock Implementation](#custom-mock-implementation)
7. [FastAPI Dependency Injection](#fastapi-dependency-injection)
8. [Testing Patterns](#testing-patterns)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

When testing FastAPI applications that use MongoDB, you need to decide how to handle database interactions. This document explores different strategies and provides recommendations based on industry best practices (2025).

### Why Mock MongoDB?

✅ **Faster tests** - No network I/O or disk operations
✅ **Isolated tests** - No shared state between tests
✅ **CI/CD friendly** - No need to run MongoDB in CI environment
✅ **Deterministic** - Consistent test data and behavior
✅ **Portable** - Tests run anywhere without database setup

### Testing Levels

```
┌─────────────────────────────────────────────┐
│ E2E Tests (Real MongoDB)                    │  Slowest, most realistic
├─────────────────────────────────────────────┤
│ Integration Tests (mongomock or Test DB)    │  Medium speed, realistic behavior
├─────────────────────────────────────────────┤
│ Unit Tests (unittest.mock)                  │  Fastest, test logic only
└─────────────────────────────────────────────┘
```

---

## Mocking Approaches Comparison

### 1. mongomock Library

**Description**: In-memory MongoDB implementation with PyMongo-compatible interface

**Pros:**
- ✅ Drop-in replacement for PyMongo's MongoClient
- ✅ Supports most common MongoDB operations
- ✅ No external dependencies or services
- ✅ Fast execution
- ✅ Realistic MongoDB behavior
- ✅ Active maintenance and community support

**Cons:**
- ❌ Not a perfect MongoDB replica (some features missing)
- ❌ May behave differently than real MongoDB in edge cases
- ❌ Doesn't test actual database connectivity

**Best for:** Integration tests where you want realistic MongoDB behavior without running a database

**Example:**
```python
import mongomock

# Replace real MongoDB client
client = mongomock.MongoClient()
db = client["test_db"]
collection = db["cards"]

# Use exactly like PyMongo
collection.insert_one({"name": "Lightning Bolt"})
result = collection.find_one({"name": "Lightning Bolt"})
```

### 2. unittest.mock (MagicMock)

**Description**: Python's built-in mocking framework for creating mock objects

**Pros:**
- ✅ No external dependencies
- ✅ Full control over mock behavior
- ✅ Fast execution
- ✅ Test specific function calls and arguments
- ✅ Good for testing error handling

**Cons:**
- ❌ Requires manual setup for each test
- ❌ Doesn't validate MongoDB query syntax
- ❌ Tests may pass even if MongoDB queries are wrong
- ❌ Verbose boilerplate code

**Best for:** Unit tests focusing on business logic rather than database queries

**Example:**
```python
from unittest.mock import MagicMock, patch

mock_collection = MagicMock()
mock_collection.find_one.return_value = {"name": "Lightning Bolt"}

with patch("api.router.cards.collection", mock_collection):
    result = get_card("bolt")
    assert result["name"] == "Lightning Bolt"
```

### 3. Real Test Database

**Description**: Use actual MongoDB instance with separate test database

**Pros:**
- ✅ 100% realistic behavior
- ✅ Tests actual database operations
- ✅ Validates query syntax and performance
- ✅ No abstraction layer

**Cons:**
- ❌ Slower test execution
- ❌ Requires MongoDB installation
- ❌ Complex CI/CD setup
- ❌ Cleanup between tests needed
- ❌ Potential for test pollution

**Best for:** E2E tests and pre-production validation

**Example:**
```python
import pytest
from pymongo import MongoClient

@pytest.fixture
def test_db():
    client = MongoClient("mongodb://localhost:27017")
    db = client["test_db"]
    yield db
    client.drop_database("test_db")  # Cleanup
```

### 4. MockupDB

**Description**: Wire protocol server that mimics MongoDB for testing

**Pros:**
- ✅ Tests wire protocol level interactions
- ✅ Simulate connection failures and network issues
- ✅ Fine-grained control over server responses

**Cons:**
- ❌ More complex setup
- ❌ Requires learning specific API
- ❌ Overkill for most use cases

**Best for:** Testing MongoDB driver behavior and error handling

---

## Recommended Approach

### For This Project: **Hybrid Strategy**

```
┌──────────────────────────────────────────────┐
│ Unit Tests (existing)                        │
│ - unittest.mock for business logic          │
│ - Fast, focused on algorithms               │
└──────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────┐
│ Integration Tests (new)                      │
│ - mongomock for endpoint testing            │
│ - Realistic MongoDB behavior                │
│ - Test actual HTTP requests                 │
└──────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────┐
│ E2E Tests (future/optional)                  │
│ - Real MongoDB with Docker Compose          │
│ - Full system testing                       │
└──────────────────────────────────────────────┘
```

**Why mongomock for integration tests?**

1. **Realistic behavior** - Tests will catch actual MongoDB query issues
2. **Fast enough** - Still runs in milliseconds
3. **Easy setup** - Two-line replacement of MongoClient
4. **Maintenance** - Active project with good PyMongo compatibility
5. **CI/CD friendly** - No external services needed

---

## Implementation Guide

### Step 1: Install mongomock

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
tests = [
    "pytest>=8.3.4",
    "pytest-asyncio>=0.25.0",
    "pytest-httpx>=0.35.0",
    "pytest-cov>=6.0.0",
    "mongomock>=4.2.0",  # Add this
]
```

Install:
```bash
uv sync --extra tests
```

### Step 2: Refactor Database Connection (Dependency Injection)

**Current code** (`api/router/cards.py`):
```python
from pymongo import MongoClient

# Module-level connection (hard to mock)
client = MongoClient(f"mongodb://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}")
db = client[DATABASE]
collection = db["cards"]

@router.get("/cards/{name}")
def search_card_by_name(name: str):
    results = collection.find_one({"name": name})  # Uses global collection
    return results
```

**Refactored code** with dependency injection:

Create `api/dependencies/database.py`:
```python
from pymongo import MongoClient
from common.constants import DATABASE, DATABASE_HOST, DATABASE_PASSWORD, DATABASE_PORT, DATABASE_USER

def get_mongo_client():
    """Get MongoDB client connection.

    This function is a dependency that can be overridden in tests.
    """
    return MongoClient(
        f"mongodb://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}"
    )

def get_database(client: MongoClient = Depends(get_mongo_client)):
    """Get database instance."""
    return client[DATABASE]

def get_cards_collection(db = Depends(get_database)):
    """Get cards collection.

    This dependency can be overridden in tests to use mongomock.
    """
    return db["cards"]
```

Update `api/router/cards.py`:
```python
from fastapi import Depends
from api.dependencies.database import get_cards_collection

@router.get("/cards/{name}")
def search_card_by_name(
    name: str,
    collection = Depends(get_cards_collection)  # Inject collection
):
    results = collection.find_one({"name": name})
    return results
```

### Step 3: Create Test Fixtures

Create `tests/conftest.py`:

```python
import pytest
import mongomock
from fastapi.testclient import TestClient
from api.main import app
from api.dependencies.database import get_cards_collection

@pytest.fixture
def mock_mongo_collection():
    """Create a mongomock collection for testing."""
    client = mongomock.MongoClient()
    db = client["test_db"]
    collection = db["cards"]
    return collection

@pytest.fixture
def client_with_mock_db(mock_mongo_collection):
    """TestClient with mocked MongoDB."""

    # Override dependency to use mongomock
    app.dependency_overrides[get_cards_collection] = lambda: mock_mongo_collection

    client = TestClient(app)
    yield client

    # Cleanup
    app.dependency_overrides.clear()

@pytest.fixture
def sample_cards():
    """Sample card data for testing."""
    return [
        {
            "id": "test-bolt-id",
            "oracle_id": "oracle-bolt",
            "name": "Lightning Bolt",
            "name_search": "lightning bolt",
            "mana_cost": "{R}",
            "cmc": 1,
            "colors": ["R"],
            "type_line": "Instant",
            "oracle_text": "Lightning Bolt deals 3 damage to any target.",
            "rarity": "common",
            "set": "lea",
            "set_name": "Limited Edition Alpha",
            "lang": "en",
            "layout": "normal",
            "released_at": "1993-08-05",
            "image_uris": {
                "small": "https://example.com/small.jpg",
                "normal": "https://example.com/normal.jpg",
                "large": "https://example.com/large.jpg",
                "png": "https://example.com/card.png"
            }
        },
        {
            "id": "test-counter-id",
            "oracle_id": "oracle-counter",
            "name": "Counterspell",
            "name_search": "counterspell",
            "mana_cost": "{U}{U}",
            "cmc": 2,
            "colors": ["U"],
            "type_line": "Instant",
            "oracle_text": "Counter target spell.",
            "rarity": "uncommon",
            "set": "lea",
            "set_name": "Limited Edition Alpha",
            "lang": "en",
            "layout": "normal",
            "released_at": "1993-08-05",
            "image_uris": {
                "small": "https://example.com/small.jpg",
                "normal": "https://example.com/normal.jpg",
                "large": "https://example.com/large.jpg",
                "png": "https://example.com/card.png"
            }
        }
    ]

@pytest.fixture
def populated_db(mock_mongo_collection, sample_cards):
    """MongoDB collection populated with sample cards."""
    mock_mongo_collection.insert_many(sample_cards)

    # Create text index for search
    mock_mongo_collection.create_index([("name", "text"), ("oracle_text", "text")])

    return mock_mongo_collection
```

### Step 4: Write Integration Tests

Create `tests/api/router/test_cards_integration.py`:

```python
import pytest
from fastapi.testclient import TestClient

def test_get_card_by_scryfall_id(client_with_mock_db, populated_db):
    """Test retrieving card by Scryfall ID."""
    response = client_with_mock_db.get("/cards/id/test-bolt-id")

    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "Lightning Bolt"
    assert card["cmc"] == 1
    assert card["colors"] == ["R"]

def test_get_card_not_found(client_with_mock_db, populated_db):
    """Test 404 when card doesn't exist."""
    response = client_with_mock_db.get("/cards/id/nonexistent-id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_search_cards(client_with_mock_db, populated_db):
    """Test card text search."""
    response = client_with_mock_db.get("/cards/search/damage")

    assert response.status_code == 200
    data = response.json()
    assert "cards" in data
    assert len(data["cards"]) > 0
    assert data["cards"][0]["name"] == "Lightning Bolt"
```

---

## mongomock Library

### Installation

```bash
pip install mongomock
# or
uv add --optional tests mongomock
```

### Basic Usage

```python
import mongomock

# Create client (in-memory)
client = mongomock.MongoClient()

# Get database and collection
db = client["test_db"]
collection = db["cards"]

# Use exactly like PyMongo
collection.insert_one({"name": "Lightning Bolt", "cmc": 1})
collection.insert_many([{"name": "Card 1"}, {"name": "Card 2"}])

# Query operations
result = collection.find_one({"name": "Lightning Bolt"})
results = list(collection.find({"cmc": {"$gte": 2}}))

# Aggregation
pipeline = [
    {"$match": {"colors": {"$in": ["R"]}}},
    {"$group": {"_id": "$set_name", "count": {"$sum": 1}}}
]
results = list(collection.aggregate(pipeline))

# Indexes
collection.create_index([("name", "text")])
```

### Supported Operations

mongomock supports most common MongoDB operations:

**CRUD:**
- `insert_one()`, `insert_many()`
- `find()`, `find_one()`
- `update_one()`, `update_many()`, `replace_one()`
- `delete_one()`, `delete_many()`

**Query Operators:**
- `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`
- `$in`, `$nin`
- `$and`, `$or`, `$not`, `$nor`
- `$exists`, `$type`
- `$regex`
- `$all`, `$size`

**Aggregation:**
- `$match`, `$project`, `$group`, `$sort`, `$limit`, `$skip`
- `$lookup` (basic support)
- `$unwind`
- `$addToSet`, `$push`, `$sum`, `$avg`, `$max`, `$min`

**Indexes:**
- `create_index()`
- Text search (basic support)

### Limitations

mongomock is not a perfect MongoDB replica:

❌ **Not supported or limited:**
- Some advanced aggregation operators
- Transactions (no-op implementation)
- GridFS
- Change streams
- Some edge cases in query behavior

⚠️ **Important:** If you need exact MongoDB behavior, use a real test database

### Testing Text Search

```python
# mongomock supports basic text search
collection.create_index([("name", "text"), ("oracle_text", "text")])

# Search works
results = collection.find({"$text": {"$search": "lightning damage"}})

# Note: Text search scoring may differ from real MongoDB
```

---

## Custom Mock Implementation

For simple tests or when mongomock doesn't support a feature, you can create custom mocks.

### Using unittest.mock

```python
from unittest.mock import MagicMock, patch

def test_with_custom_mock():
    """Test using custom mock collection."""

    # Create mock collection
    mock_collection = MagicMock()

    # Configure return values
    mock_collection.find_one.return_value = {
        "id": "test-id",
        "name": "Lightning Bolt"
    }

    mock_collection.find.return_value = [
        {"name": "Card 1"},
        {"name": "Card 2"}
    ]

    # Mock aggregation
    mock_collection.aggregate.return_value = [
        {"_id": "oracle-1", "name": "Lightning Bolt", "score": 10.5}
    ]

    # Use with patch
    with patch("api.router.cards.collection", mock_collection):
        # Run your test
        result = get_card_by_id("test-id")
        assert result["name"] == "Lightning Bolt"

    # Verify mock was called correctly
    mock_collection.find_one.assert_called_once_with({"id": "test-id"})
```

### Custom Mock Classes

For more realism, create custom mock classes:

```python
class MockMongoCollection:
    """Custom mock MongoDB collection."""

    def __init__(self, documents=None):
        self._documents = documents or []

    def find_one(self, query, projection=None):
        """Simple find_one implementation."""
        for doc in self._documents:
            if self._matches_query(doc, query):
                return self._apply_projection(doc, projection)
        return None

    def find(self, query, projection=None):
        """Simple find implementation."""
        results = []
        for doc in self._documents:
            if self._matches_query(doc, query):
                results.append(self._apply_projection(doc, projection))
        return MockMongoCursor(results)

    def _matches_query(self, doc, query):
        """Simple query matching (extend as needed)."""
        for key, value in query.items():
            if key not in doc or doc[key] != value:
                return False
        return True

    def _apply_projection(self, doc, projection):
        """Apply field projection."""
        if not projection:
            return doc
        # Implementation here
        return doc

class MockMongoCursor:
    """Mock MongoDB cursor."""

    def __init__(self, documents):
        self._documents = documents

    def sort(self, field, direction=1):
        """Sort documents."""
        # Sort implementation
        return self._documents

    def limit(self, count):
        """Limit results."""
        return self._documents[:count]
```

---

## FastAPI Dependency Injection

### Pattern 1: Collection-Level Injection

```python
# api/dependencies/database.py
from fastapi import Depends
from pymongo import MongoClient

def get_cards_collection():
    client = MongoClient("mongodb://...")
    db = client["mtg_db"]
    return db["cards"]

# api/router/cards.py
from fastapi import Depends
from api.dependencies.database import get_cards_collection

@router.get("/cards/id/{card_id}")
def get_card(card_id: str, collection = Depends(get_cards_collection)):
    return collection.find_one({"id": card_id})

# tests/test_cards.py
def test_get_card(mock_collection):
    app.dependency_overrides[get_cards_collection] = lambda: mock_collection

    client = TestClient(app)
    response = client.get("/cards/id/test-id")

    app.dependency_overrides.clear()
```

### Pattern 2: Client-Level Injection

```python
# api/dependencies/database.py
def get_mongo_client():
    return MongoClient("mongodb://...")

def get_database(client = Depends(get_mongo_client)):
    return client["mtg_db"]

# tests/test_cards.py
def test_with_mock_client():
    mock_client = mongomock.MongoClient()

    app.dependency_overrides[get_mongo_client] = lambda: mock_client
    # All routes will now use mongomock
```

### Pattern 3: Fixture-Based Override

```python
# tests/conftest.py
@pytest.fixture
def client_with_mock_db():
    """Automatically override dependencies."""
    mock_collection = mongomock.MongoClient()["test"]["cards"]

    app.dependency_overrides[get_cards_collection] = lambda: mock_collection

    yield TestClient(app)

    app.dependency_overrides.clear()

# tests/test_cards.py
def test_example(client_with_mock_db):
    # Dependencies already overridden
    response = client_with_mock_db.get("/cards/id/test")
```

---

## Testing Patterns

### Pattern 1: Arrange-Act-Assert with Fixtures

```python
def test_search_with_filters(client_with_mock_db, populated_db):
    # Arrange - data is already in populated_db fixture

    # Act
    response = client_with_mock_db.post(
        "/cards/search/instant",
        json={"colors": ["R"], "cmc_min": 1, "cmc_max": 3}
    )

    # Assert
    assert response.status_code == 200
    cards = response.json()["cards"]
    assert all(card["cmc"] >= 1 and card["cmc"] <= 3 for card in cards)
    assert all("R" in card["colors"] for card in cards)
```

### Pattern 2: Test Data Builders

```python
class CardBuilder:
    """Builder pattern for creating test cards."""

    def __init__(self):
        self.data = {
            "id": "test-id",
            "name": "Test Card",
            "cmc": 3,
            "colors": [],
            "type_line": "Creature"
        }

    def with_id(self, card_id):
        self.data["id"] = card_id
        return self

    def with_name(self, name):
        self.data["name"] = name
        return self

    def with_cmc(self, cmc):
        self.data["cmc"] = cmc
        return self

    def with_colors(self, colors):
        self.data["colors"] = colors
        return self

    def build(self):
        return self.data

# Usage in tests
def test_with_builder(mock_collection):
    bolt = CardBuilder().with_name("Lightning Bolt").with_cmc(1).with_colors(["R"]).build()
    mock_collection.insert_one(bolt)

    result = mock_collection.find_one({"name": "Lightning Bolt"})
    assert result["cmc"] == 1
```

### Pattern 3: Parametrized Tests

```python
@pytest.mark.parametrize("color,expected_count", [
    (["R"], 5),
    (["U"], 3),
    (["W", "U"], 2),
])
def test_color_filtering(client_with_mock_db, populated_db, color, expected_count):
    response = client_with_mock_db.post(
        "/cards/search/card",
        json={"colors": color, "color_operator": "or"}
    )

    assert response.status_code == 200
    assert len(response.json()["cards"]) == expected_count
```

---

## Best Practices

### 1. Use Fixtures for Reusable Setup

✅ **Good:**
```python
@pytest.fixture
def sample_cards():
    return [...]

def test_1(sample_cards):
    # Use fixture

def test_2(sample_cards):
    # Reuse fixture
```

❌ **Bad:**
```python
def test_1():
    cards = [...]  # Duplicate setup

def test_2():
    cards = [...]  # Duplicate setup
```

### 2. Clean Up After Tests

✅ **Good:**
```python
@pytest.fixture
def client_with_mock_db():
    # Setup
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app)
    # Teardown
    app.dependency_overrides.clear()
```

❌ **Bad:**
```python
def test_something():
    app.dependency_overrides[get_db] = lambda: mock_db
    # No cleanup - affects other tests!
```

### 3. Test Isolation

✅ **Good:**
```python
@pytest.fixture(scope="function")  # New instance per test
def mock_db():
    return mongomock.MongoClient()["test"]["cards"]
```

❌ **Bad:**
```python
@pytest.fixture(scope="session")  # Shared across tests
def mock_db():
    return mongomock.MongoClient()["test"]["cards"]
    # Tests can pollute each other's data!
```

### 4. Realistic Test Data

✅ **Good:**
```python
{
    "id": "bd8fa327-dd41-4737-8f19-2cf5eb1f7cdd",  # Real UUID format
    "oracle_id": "e3285e6b-3e79-4d7c-bf96-d920f973b122",
    "name": "Lightning Bolt",
    "mana_cost": "{R}",
    "cmc": 1,
    # All required fields present
}
```

❌ **Bad:**
```python
{
    "id": "123",  # Unrealistic
    "name": "Test Card"
    # Missing fields
}
```

### 5. Test Both Success and Failure

```python
def test_get_card_success(client_with_mock_db, populated_db):
    response = client_with_mock_db.get("/cards/id/test-id")
    assert response.status_code == 200

def test_get_card_not_found(client_with_mock_db, populated_db):
    response = client_with_mock_db.get("/cards/id/nonexistent")
    assert response.status_code == 404
```

### 6. Use Descriptive Test Names

✅ **Good:**
```python
def test_search_returns_cards_matching_color_filter_with_or_operator():
    ...

def test_search_returns_404_when_no_cards_match_filter():
    ...
```

❌ **Bad:**
```python
def test_search():
    ...

def test_colors():
    ...
```

### 7. Don't Test MongoDB Itself

✅ **Good:**
```python
def test_get_card_by_id_returns_correct_card():
    # Test your API logic
    response = client.get("/cards/id/test-id")
    assert response.json()["name"] == "Lightning Bolt"
```

❌ **Bad:**
```python
def test_mongodb_find_one_works():
    # Don't test PyMongo/MongoDB
    result = collection.find_one({"id": "test"})
    assert result is not None
```

---

## Troubleshooting

### Issue: Tests pass with mock but fail in production

**Cause:** Mock behavior differs from real MongoDB

**Solution:**
- Use mongomock instead of custom mocks for more realistic behavior
- Add E2E tests with real MongoDB for critical paths
- Verify query syntax matches MongoDB documentation

### Issue: Dependency overrides not working

**Cause:** Wrong dependency being overridden or not cleared

**Solution:**
```python
# Make sure you override the exact dependency used in routes
app.dependency_overrides[get_cards_collection] = lambda: mock_collection

# Always clear after tests
app.dependency_overrides.clear()
```

### Issue: mongomock doesn't support a feature

**Cause:** mongomock has limited support for some advanced MongoDB features

**Solution:**
- Check mongomock documentation for supported features
- Use custom mock for unsupported features
- Use real test database for complex queries

### Issue: Tests are slow

**Cause:** Creating new MongoDB connections for each test

**Solution:**
```python
# Use function scope for isolation, but reuse client
@pytest.fixture(scope="session")
def mock_client():
    return mongomock.MongoClient()

@pytest.fixture
def mock_collection(mock_client):
    db = mock_client["test"]
    collection = db["cards"]
    yield collection
    collection.drop()  # Clean up
```

### Issue: Text search not working in mongomock

**Cause:** mongomock text search is limited

**Solution:**
```python
# Create text index first
collection.create_index([("name", "text")])

# Use basic text search
collection.find({"$text": {"$search": "lightning"}})

# For complex text search, use real database or custom mock
```

---

## Summary

### Quick Decision Guide

**Use mongomock when:**
- ✅ Writing integration tests for FastAPI endpoints
- ✅ Testing MongoDB queries and aggregations
- ✅ Need realistic database behavior without external dependencies
- ✅ CI/CD pipeline needs database testing

**Use unittest.mock when:**
- ✅ Writing unit tests for pure business logic
- ✅ Testing error handling and edge cases
- ✅ Need to verify specific function calls
- ✅ Mocking is trivial (simple return values)

**Use real test database when:**
- ✅ Running E2E tests
- ✅ Testing complex queries mongomock doesn't support
- ✅ Validating production-like behavior
- ✅ Performance testing

### Recommended Setup for This Project

```python
# tests/conftest.py
import pytest
import mongomock
from fastapi.testclient import TestClient
from api.main import app
from api.dependencies.database import get_cards_collection

@pytest.fixture
def mock_collection():
    """mongomock collection for integration tests."""
    client = mongomock.MongoClient()
    return client["test"]["cards"]

@pytest.fixture
def client_with_mock_db(mock_collection):
    """TestClient with mongomock."""
    app.dependency_overrides[get_cards_collection] = lambda: mock_collection
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def sample_cards():
    """Realistic test card data."""
    return [
        # Lightning Bolt, Counterspell, etc.
    ]

@pytest.fixture
def populated_db(mock_collection, sample_cards):
    """Pre-populated test database."""
    mock_collection.insert_many(sample_cards)
    mock_collection.create_index([("name", "text")])
    return mock_collection
```

---

## References

- [mongomock GitHub Repository](https://github.com/mongomock/mongomock)
- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [PyMongo Documentation](https://pymongo.readthedocs.io/)
