# FastAPI Testing Guide - Best Practices (2025)

## Overview

This guide covers modern best practices for testing FastAPI applications using pytest, based on the latest FastAPI documentation and community standards.

## Table of Contents

1. [Testing Approaches](#testing-approaches)
2. [Basic Setup](#basic-setup)
3. [TestClient for Synchronous Tests](#testclient-for-synchronous-tests)
4. [AsyncClient for Async Tests](#asyncclient-for-async-tests)
5. [Database Testing](#database-testing)
6. [Dependency Overrides](#dependency-overrides)
7. [Authentication Testing](#authentication-testing)
8. [Best Practices](#best-practices)

---

## Testing Approaches

FastAPI supports two main testing approaches:

1. **Unit Tests with Mocking** - Fast, isolated tests that mock dependencies
2. **Integration Tests with TestClient/AsyncClient** - Test actual HTTP endpoints with real database interactions

### Current State

Our project uses **Unit Tests with Mocking** (see `tests/api/router/test_card_search.py`). This approach is excellent for testing business logic in isolation.

### Recommended Addition

Add **Integration Tests** to complement unit tests, ensuring endpoints work correctly with actual dependencies.

---

## Basic Setup

### Required Dependencies

Already installed in `pyproject.toml`:

```toml
[project.optional-dependencies]
tests = [
    "pytest>=8.3.4",
    "pytest-asyncio>=0.25.0",
    "pytest-httpx>=0.35.0",
    "pytest-cov>=6.0.0",
]
```

### Project Structure

```
tests/
├── conftest.py              # Shared fixtures
├── api/
│   ├── test_integration.py  # Integration tests with TestClient
│   └── router/
│       ├── test_cards_integration.py
│       └── test_card_search.py  # Existing unit tests
```

---

## TestClient for Synchronous Tests

### Basic Example

```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

### Testing with Query Parameters

```python
def test_search_cards():
    response = client.get("/cards/search", params={"q": "Lightning Bolt"})
    assert response.status_code == 200
    data = response.json()
    assert "cards" in data
    assert len(data["cards"]) > 0
```

### Testing POST Requests

```python
def test_create_deck():
    deck_data = {
        "name": "Red Deck Wins",
        "cards": ["card-id-1", "card-id-2"]
    }
    response = client.post("/decks", json=deck_data)
    assert response.status_code == 201
    assert response.json()["name"] == "Red Deck Wins"
```

### Testing Error Cases

```python
def test_card_not_found():
    response = client.get("/cards/id/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
```

---

## AsyncClient for Async Tests

For async endpoints or when testing with async database operations, use `httpx.AsyncClient`.

### Configuration in pytest

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

### Basic Async Test

```python
import pytest
from httpx import ASGITransport, AsyncClient
from api.main import app

@pytest.mark.asyncio
async def test_async_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        response = await ac.get("/cards/search?q=bolt")
        assert response.status_code == 200
```

### Fixture Setup

Create `tests/conftest.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from api.main import app

@pytest.fixture(scope="session")
def anyio_backend():
    """Tell pytest-asyncio to use asyncio."""
    return "asyncio"

@pytest.fixture
async def async_client():
    """Async client fixture for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
```

### Using Async Fixture

```python
@pytest.mark.asyncio
async def test_with_fixture(async_client):
    response = await async_client.get("/cards/search?q=bolt")
    assert response.status_code == 200
```

---

## Database Testing

### Test Database Isolation

**Option 1: Use Test Database**

```python
import pytest
from pymongo import MongoClient

@pytest.fixture(scope="function")
def test_db():
    """Create test database, yield, then cleanup."""
    client = MongoClient("mongodb://localhost:27017")
    db = client["mtg_test_db"]

    # Seed test data
    db.cards.insert_many([
        {"id": "test-1", "name": "Lightning Bolt"},
        {"id": "test-2", "name": "Counterspell"}
    ])

    yield db

    # Cleanup
    client.drop_database("mtg_test_db")
    client.close()
```

**Option 2: Transaction Rollback**

```python
@pytest.fixture
async def test_db_session():
    """Use transaction rollback for isolation."""
    async with AsyncSession() as session:
        async with session.begin():
            yield session
            # Transaction auto-rolls back after test
```

### Override Database Dependency

```python
from api.main import app
from api.helpers.database import get_database

def override_get_database():
    """Return test database."""
    client = MongoClient("mongodb://localhost:27017")
    return client["mtg_test_db"]

app.dependency_overrides[get_database] = override_get_database
```

---

## Dependency Overrides

Dependency overrides allow you to replace real dependencies (database, auth, external APIs) with test implementations.

### Override Authentication

```python
from api.dependencies.auth import get_current_user

def override_auth():
    """Skip authentication in tests."""
    return {"user_id": "test-user", "username": "testuser"}

app.dependency_overrides[get_current_user] = override_auth

def test_protected_endpoint():
    response = client.get("/protected")
    assert response.status_code == 200
```

### Override External API Calls

```python
from api.dependencies.external import get_scryfall_api

def mock_scryfall():
    """Mock Scryfall API client."""
    class MockScryfall:
        def get_card(self, card_id):
            return {"id": card_id, "name": "Mock Card"}
    return MockScryfall()

app.dependency_overrides[get_scryfall_api] = mock_scryfall
```

### Cleanup After Tests

```python
@pytest.fixture(autouse=True)
def cleanup_overrides():
    """Clear dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()
```

---

## Authentication Testing

### Testing JWT Authentication

```python
from datetime import datetime, timedelta
import jwt

def create_test_token(user_id: str = "test-user"):
    """Create valid JWT token for testing."""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, "secret-key", algorithm="HS256")

def test_authenticated_request():
    token = create_test_token()
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
```

### Testing Unauthorized Access

```python
def test_no_token():
    response = client.get("/protected")
    assert response.status_code == 401

def test_invalid_token():
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401
```

---

## Best Practices

### 1. Use Fixtures for Reusable Setup

**Good:**
```python
@pytest.fixture
def sample_cards():
    return [
        {"id": "1", "name": "Lightning Bolt"},
        {"id": "2", "name": "Counterspell"}
    ]

def test_search(sample_cards):
    # Use sample_cards fixture
    pass
```

**Bad:**
```python
def test_search():
    # Recreate test data in every test
    cards = [{"id": "1", "name": "Lightning Bolt"}]
```

### 2. Test Response Structure

```python
def test_card_response_structure():
    response = client.get("/cards/id/test-id")
    data = response.json()

    # Assert response structure
    assert "id" in data
    assert "name" in data
    assert "image_uris" in data
    assert isinstance(data["image_uris"], dict)
```

### 3. Use Parametrize for Multiple Cases

```python
@pytest.mark.parametrize("card_id,expected_name", [
    ("id-1", "Lightning Bolt"),
    ("id-2", "Counterspell"),
    ("id-3", "Giant Growth"),
])
def test_get_cards(card_id, expected_name):
    response = client.get(f"/cards/id/{card_id}")
    assert response.json()["name"] == expected_name
```

### 4. Separate Unit and Integration Tests

```python
# tests/unit/test_card_logic.py - Fast, mocked
def test_card_filter_logic():
    # Test pure logic with mocks
    pass

# tests/integration/test_card_api.py - Slower, real dependencies
def test_card_api_endpoint():
    # Test actual HTTP endpoint
    pass
```

### 5. Mock External HTTP Calls

```python
import httpx
import respx

@respx.mock
def test_external_api_call():
    # Mock external API
    respx.get("https://api.scryfall.com/cards/bolt").mock(
        return_value=httpx.Response(200, json={"name": "Lightning Bolt"})
    )

    response = client.get("/cards/fetch/bolt")
    assert response.status_code == 200
```

### 6. Test Error Handling

```python
def test_database_error_handling(monkeypatch):
    """Test graceful handling of database errors."""
    def mock_db_error(*args, **kwargs):
        raise ConnectionError("Database unavailable")

    monkeypatch.setattr("api.helpers.database.collection.find", mock_db_error)

    response = client.get("/cards/search?q=bolt")
    assert response.status_code == 503  # Service Unavailable
    assert "database" in response.json()["detail"].lower()
```

### 7. Use Coverage Reports

```bash
# Run tests with coverage
pytest --cov=api --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 8. Organize Tests by Feature

```
tests/
├── api/
│   ├── router/
│   │   ├── test_cards_unit.py          # Unit tests with mocks
│   │   ├── test_cards_integration.py   # Integration tests
│   │   ├── test_sets_unit.py
│   │   └── test_sets_integration.py
│   └── helpers/
│       └── test_database.py
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/api/router/test_cards_integration.py

# Run specific test
pytest tests/api/router/test_cards_integration.py::test_search_endpoint

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=api --cov-report=term-missing

# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit
```

---

## Example: Complete Integration Test

```python
# tests/api/router/test_cards_integration.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_test_db():
    """Setup test database with sample data."""
    # Connect to test database
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017")
    db = client["mtg_test_db"]

    # Insert test data
    db.cards.insert_many([
        {
            "id": "test-bolt-id",
            "oracle_id": "oracle-bolt",
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "cmc": 1,
            "colors": ["R"],
            "type_line": "Instant",
            "oracle_text": "Lightning Bolt deals 3 damage to any target.",
            "rarity": "common"
        },
        {
            "id": "test-counter-id",
            "oracle_id": "oracle-counter",
            "name": "Counterspell",
            "mana_cost": "{U}{U}",
            "cmc": 2,
            "colors": ["U"],
            "type_line": "Instant",
            "oracle_text": "Counter target spell.",
            "rarity": "uncommon"
        }
    ])

    yield db

    # Cleanup
    client.drop_database("mtg_test_db")
    client.close()

def test_health_check():
    """Test basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

def test_search_cards_basic(setup_test_db):
    """Test basic card search."""
    response = client.get("/cards/search?q=Lightning")

    assert response.status_code == 200
    data = response.json()
    assert "cards" in data
    assert len(data["cards"]) > 0
    assert data["cards"][0]["name"] == "Lightning Bolt"

def test_search_with_filters(setup_test_db):
    """Test search with color filter."""
    response = client.post(
        "/cards/search",
        params={"q": "instant"},
        json={"colors": ["U"], "color_operator": "or"}
    )

    assert response.status_code == 200
    data = response.json()
    # Should only return blue cards
    for card in data["cards"]:
        assert "U" in card["colors"]

def test_get_card_by_id(setup_test_db):
    """Test retrieving specific card by Scryfall ID."""
    response = client.get("/cards/id/test-bolt-id")

    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "Lightning Bolt"
    assert card["cmc"] == 1

def test_card_not_found():
    """Test 404 for nonexistent card."""
    response = client.get("/cards/id/nonexistent-id")
    assert response.status_code == 404
```

---

## Key Takeaways

1. **Use TestClient** for most endpoint testing - it's fast and doesn't require running the server
2. **Use AsyncClient** when testing async endpoints or async database operations
3. **Use dependency overrides** to mock authentication, databases, and external services
4. **Separate concerns** - unit tests for logic, integration tests for endpoints
5. **Centralize fixtures** in `conftest.py` for reusability
6. **Test both success and failure cases** - don't just test the happy path
7. **Use test databases** to avoid affecting production data
8. **Run tests in CI/CD** to catch issues early

---

## Next Steps

1. Create `tests/conftest.py` with shared fixtures
2. Add integration tests alongside existing unit tests
3. Configure pytest in `pyproject.toml`
4. Set up test database configuration
5. Add CI/CD pipeline to run tests automatically

---

## References

- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI Async Tests](https://fastapi.tiangolo.com/advanced/async-tests/)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
