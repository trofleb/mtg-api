# Task List: FastAPI Integration Tests with Mocked MongoDB

**Date**: 2025-11-16
**Status**: Planning → Documentation Complete → Ready for Implementation
**Project**: MTG API Integration Testing

## Overview

Add comprehensive integration tests for FastAPI endpoints using TestClient with mocked MongoDB database. This complements the existing unit tests by testing actual HTTP endpoints without requiring a running database server.

## Planning Documentation

- [x] FastAPI Testing Guide created in `documentation/fastapi-testing-guide.md`
- [x] MongoDB mocking strategy documented in `documentation/mongodb-mocking-strategy.md`

---

## Implementation Tasks

### Phase 1: Test Infrastructure Setup

- [ ] Create `tests/conftest.py` with shared fixtures for TestClient, mock MongoDB, and test data helpers ✅ **Tests Required**

- [ ] Add pytest configuration to `pyproject.toml` including asyncio mode settings and test markers (unit/integration) ✅ **Tests Required**

- [ ] Create database dependency injection in `api/helpers/database.py` to enable easy mocking by refactoring hardcoded MongoDB connections to use dependency injection ✅ **Tests Required**

- [ ] Create `tests/fixtures/sample_cards.py` with reusable test card data (Lightning Bolt, Counterspell, etc.) in MongoDB document format ✅ **Tests Required**

- [ ] Create `tests/mocks/mongodb.py` with MockMongoCollection and MockMongoCursor classes that simulate MongoDB operations (find, find_one, aggregate, sort) ✅ **Tests Required**

### Phase 2: Base Router Integration Tests

- [ ] Create `tests/api/router/test_base_integration.py` to test `/ping` endpoint returning "pong" with 200 status ✅ **Tests Required**

### Phase 3: Sets Router Integration Tests

- [ ] Create `tests/api/router/test_sets_integration.py` to test `/sets` endpoint with mocked MongoDB aggregation returning list of unique set names ✅ **Tests Required**

- [ ] Add test for `/sets` endpoint with empty database returning empty sets list ✅ **Tests Required**

- [ ] Add test for `/sets` endpoint verifying alphabetical sorting of set names ✅ **Tests Required**

### Phase 4: Cards Router Integration Tests - Basic Endpoints

- [ ] Create `tests/api/router/test_cards_basic_integration.py` for `/cards/{name}` endpoint testing exact name match with mock MongoDB regex query ✅ **Tests Required**

- [ ] Add test for `/cards/{name}` with language parameter (lang=en, lang=fr) verifying language filtering ✅ **Tests Required**

- [ ] Add test for `/cards/{name}` with set parameter filtering by specific set code ✅ **Tests Required**

- [ ] Add test for `/cards/{name}` when card not found returning None ✅ **Tests Required**

- [ ] Add test for `/cards/id/{scryfall_id}` endpoint successfully retrieving card by Scryfall ID ✅ **Tests Required**

- [ ] Add test for `/cards/id/{scryfall_id}` returning 404 HTTPException when card not found ✅ **Tests Required**

- [ ] Add test for `/cards/oracle/{oracle_id}` endpoint returning all printings sorted by release date ✅ **Tests Required**

- [ ] Add test for `/cards/oracle/{oracle_id}` returning 404 when no printings exist ✅ **Tests Required**

### Phase 5: Cards Router Integration Tests - Search Endpoint

- [ ] Create `tests/api/router/test_cards_search_integration.py` for `/cards/search/{text}` basic text search with mocked MongoDB $text search ✅ **Tests Required**

- [ ] Add test for search with pagination using cursor parameter (score-based cursor) ✅ **Tests Required**

- [ ] Add test for search with custom page_count parameter (default 10, test with 5 and 20) ✅ **Tests Required**

- [ ] Add test for search verifying has_more flag (True when more results exist, False when at end) ✅ **Tests Required**

- [ ] Add test for search with CardFilter.sets (filtering by one or multiple set names) ✅ **Tests Required**

- [ ] Add test for search with CardFilter.colors using "or" operator ($in query) ✅ **Tests Required**

- [ ] Add test for search with CardFilter.colors using "and" operator ($all query) ✅ **Tests Required**

- [ ] Add test for search with CardFilter.colors using "exactly" operator ($all + $size query) ✅ **Tests Required**

- [ ] Add test for search with CardFilter.cmc_min only ($gte query) ✅ **Tests Required**

- [ ] Add test for search with CardFilter.cmc_max only ($lte query) ✅ **Tests Required**

- [ ] Add test for search with CardFilter.cmc_min and cmc_max range ($gte and $lte query) ✅ **Tests Required**

- [ ] Add test for search with CardFilter.types using regex pattern matching on type_line ✅ **Tests Required**

- [ ] Add test for search with CardFilter.rarities using $in query ✅ **Tests Required**

- [ ] Add test for search with all filters combined simultaneously verifying MongoDB aggregation pipeline ✅ **Tests Required**

### Phase 6: Response Structure Validation Tests

- [ ] Create `tests/api/router/test_cards_response_schema.py` to validate card response includes all required fields (id, name, oracle_id, image_uris, etc.) ✅ **Tests Required**

- [ ] Add test validating search response structure (cards array, cursor string, has_more boolean) ✅ **Tests Required**

- [ ] Add test validating image_uris structure (small, normal, large, png, art_crop, border_crop) ✅ **Tests Required**

- [ ] Add test validating sets response structure (sets array of strings) ✅ **Tests Required**

### Phase 7: Edge Cases and Error Handling

- [ ] Create `tests/api/router/test_cards_edge_cases.py` for colorless cards (empty colors array) with "exactly" operator ✅ **Tests Required**

- [ ] Add test for five-color cards (all WUBRG) with "exactly" operator ✅ **Tests Required**

- [ ] Add test for CMC 0 cards (cmc_min=0, cmc_max=0) ✅ **Tests Required**

- [ ] Add test for very high CMC cards (cmc_min=15+) ✅ **Tests Required**

- [ ] Add test for invalid Scryfall ID format (UUID validation) ✅ **Tests Required**

- [ ] Add test for search with special characters in text query (quotes, slashes, unicode) ✅ **Tests Required**

- [ ] Add test for database connection error handling returning 503 Service Unavailable ✅ **Tests Required**

### Phase 8: Test Utilities and Helpers

- [ ] Create `tests/utils/assertions.py` with helper functions for common assertions (assert_card_structure, assert_search_response, etc.) ✅ **Tests Required**

- [ ] Create `tests/utils/builders.py` with builder pattern for creating test card objects (CardBuilder().with_colors(['R']).with_cmc(3).build()) ✅ **Tests Required**

### Phase 9: CI/CD Integration

- [ ] Add pytest-cov configuration in `pyproject.toml` with minimum coverage threshold (80%) ✅ **Tests Required**

- [ ] Update `Justfile` with integration test commands (just test-integration, just test-unit, just test-all) ✅ **Tests Required**

- [ ] Create `.github/workflows/tests.yml` for automated test running on push/PR (if using GitHub Actions) ✅ **Tests Required**

---

## Documentation Tasks

- [ ] Create `documentation/mongodb-mocking-strategy.md` explaining the mock MongoDB architecture and how to use it

- [ ] Update `CLAUDE.md` with testing commands and best practices for running integration tests

- [ ] Update `README.md` testing section with examples of running unit vs integration tests

- [ ] Add inline documentation to `tests/conftest.py` explaining each fixture and its purpose

---

## Notes

### Architecture Decisions

1. **Mock Strategy**: Use in-memory mock MongoDB (not mongomock library) for full control over test data and faster execution
2. **Dependency Injection**: Refactor router files to use dependency injection for database connections, enabling easy mocking via `app.dependency_overrides`
3. **Test Organization**: Separate integration tests from unit tests using pytest markers and directory structure
4. **Fixture Scope**: Use `function` scope for most fixtures to ensure test isolation; use `session` scope only for immutable test data

### Test Data Strategy

- **Lightning Bolt**: Red instant, CMC 1, common rarity - for basic testing
- **Counterspell**: Blue instant, CMC 2, uncommon rarity - for color/CMC filtering
- **Black Lotus**: Colorless artifact, CMC 0, rare - for edge cases
- **Progenitus**: Five-color creature, CMC 10, mythic - for multi-color testing
- **Double-faced cards**: For layout/card_faces testing
- **Multiple printings**: Same oracle_id, different set_codes - for oracle endpoint testing

### Dependencies Between Tasks

```
Phase 1 (Infrastructure) → Required for all other phases
Phase 2-4 (Basic tests) → Can be done in parallel after Phase 1
Phase 5 (Search tests) → Depends on Phase 1 and Phase 4
Phase 6 (Validation) → Depends on Phases 2-5
Phase 7 (Edge cases) → Depends on Phases 2-5
Phase 8 (Utilities) → Can be done in parallel, refactor earlier phases to use utilities
Phase 9 (CI/CD) → Depends on all previous phases completing
```

### MongoDB Mock Implementation Details

The mock MongoDB should support:
- `find_one(query, projection)` → Returns single document or None
- `find(query, projection).sort(field, direction)` → Returns cursor with list of documents
- `aggregate(pipeline)` → Returns cursor with aggregation results
- Support for MongoDB query operators: `$eq`, `$regex`, `$in`, `$all`, `$gte`, `$lte`, `$text`, `$search`, `$or`, `$and`
- Support for aggregation operators: `$match`, `$project`, `$group`, `$sort`, `$limit`

### Refactoring Strategy for Database Injection

Current code (in `api/router/cards.py`):
```python
client = MongoClient(f"mongodb://...")
db = client[DATABASE]
collection = db["cards"]
```

Refactored code:
```python
def get_database():
    client = MongoClient(f"mongodb://...")
    db = client[DATABASE]
    return db

def get_collection(db=Depends(get_database)):
    return db["cards"]

@router.get("/cards/{name}")
def search_card_by_name(
    name: str,
    collection=Depends(get_collection)
):
    # Use injected collection
```

Test override:
```python
app.dependency_overrides[get_collection] = lambda: mock_collection
```

### Success Criteria

- ✅ All integration tests pass with 100% success rate
- ✅ Code coverage for router files reaches minimum 80%
- ✅ Tests run in under 5 seconds (mock MongoDB should be fast)
- ✅ No external database dependencies required to run tests
- ✅ Tests are isolated and can run in any order
- ✅ CI/CD pipeline successfully runs tests on every commit

---

## Running Tests

After implementation, tests can be run with:

```bash
# Run all tests
pytest

# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific test file
pytest tests/api/router/test_cards_search_integration.py

# Run specific test
pytest tests/api/router/test_cards_search_integration.py::test_search_with_color_filter

# Run with verbose output
pytest -v

# Run with print statements
pytest -s
```

Using Justfile shortcuts:
```bash
just test                    # Run all tests
just test-integration        # Integration tests only
just test-unit              # Unit tests only
just test-cov               # With coverage report
```
