# Phase 2 Implementation Plan: Base Router Integration Tests

**Date**: 2025-11-16
**Status**: ✅ COMPLETED
**Phase**: 2 of 9 - Base Router Integration Tests
**Project**: MTG API Integration Testing

---

## Overview

Phase 2 establishes the foundation for integration testing by implementing tests for the simplest FastAPI endpoint (`/ping`). This phase validates that the test infrastructure from Phase 1 is working correctly and serves as a template for more complex integration tests in later phases.

### Strategic Importance

- **First Integration Test**: Validates that TestClient and FastAPI app initialization work correctly
- **Template Pattern**: Establishes patterns for endpoint testing that will be reused in Phases 3-7
- **Infrastructure Validation**: Confirms Phase 1 setup is functional before proceeding to complex tests
- **Zero Dependencies**: Tests endpoint without database requirements, isolating infrastructure issues

---

## Dependencies from Phase 1

Phase 2 relies on these Phase 1 deliverables being complete:

### ✅ Required Infrastructure (Already Implemented)

1. **`tests/conftest.py`** - Shared fixtures including:
   - `test_client` fixture with FastAPI TestClient
   - `mock_cards_collection` fixture with sample data
   - `empty_collection` fixture for empty state testing
   - Dependency override mechanism for `get_cards_collection`

2. **`pyproject.toml`** - pytest configuration:
   - Test markers: `@pytest.mark.integration` and `@pytest.mark.unit`
   - Asyncio mode: `auto`
   - Test discovery patterns: `test_*.py`, `Test*`, `test_*`
   - Command-line options: `-v`, `--strict-markers`, `--tb=short`

3. **`api/helpers/database.py`** - Dependency injection:
   - `get_mongo_client()` - MongoDB client factory
   - `get_database()` - Database instance dependency
   - `get_cards_collection()` - Cards collection dependency
   - Type annotations: `MongoDatabase`, `CardsCollection`

4. **Mock Infrastructure**:
   - `tests/mocks/mongodb.py` - MockMongoCollection and MockMongoCursor
   - `tests/fixtures/sample_cards.py` - Reusable test card data

---

## What to Update and Why

### ✅ File Created: `tests/api/router/test_base_integration.py`

**Purpose**: Test the `/ping` endpoint to validate basic routing and TestClient functionality.

**Why This File**:
- **Simplest Test Case**: No database dependencies, minimal complexity
- **Infrastructure Validation**: If this test fails, the problem is in Phase 1 setup
- **Pattern Establishment**: Shows how to structure integration tests with pytest markers
- **Documentation**: Serves as reference implementation for future test files

**Implementation Details**:

```python
"""Integration tests for base router endpoints.

This module tests the basic API endpoints that don't require database access,
validating that the test infrastructure is working correctly.
"""

import pytest


@pytest.mark.integration
def test_ping_endpoint_returns_pong(test_client):
    """Test that /ping endpoint returns 'pong' with 200 status.

    This is the simplest integration test, validating that:
    - TestClient is configured correctly
    - FastAPI app is properly loaded
    - Basic routing works
    """
    response = test_client.get("/ping")

    assert response.status_code == 200
    assert response.text == "pong"
```

**Key Design Decisions**:

1. **Marker Usage**: `@pytest.mark.integration` allows running with `pytest -m integration`
2. **Fixture Injection**: Uses `test_client` from `conftest.py` for consistency
3. **Clear Assertions**: Separate assertions for status code and response body
4. **Comprehensive Docstring**: Explains what is being validated beyond just the endpoint

---

## Tests Required

### ✅ Test 1: Ping Endpoint Success Case

**File**: `tests/api/router/test_base_integration.py`
**Function**: `test_ping_endpoint_returns_pong(test_client)`

**What It Tests**:
- HTTP GET request to `/ping` returns 200 status code
- Response body is plain text "pong"
- No database dependency required
- TestClient configuration is correct

**Validation**:
```bash
$ uv run pytest tests/api/router/test_base_integration.py -v

tests/api/router/test_base_integration.py::test_ping_endpoint_returns_pong PASSED
```

**Edge Cases Covered**:
- ✅ Basic routing works (if broken, FastAPI app not loading correctly)
- ✅ Response class correct (PlainTextResponse returns text, not JSON)
- ✅ No unintended side effects (test is idempotent)

### Potential Additional Tests (Not Required for Phase 2)

These could be added if the base router gains more endpoints:

1. **Test Response Headers**:
   ```python
   def test_ping_endpoint_headers(test_client):
       response = test_client.get("/ping")
       assert response.headers["content-type"] == "text/plain; charset=utf-8"
   ```

2. **Test Method Not Allowed**:
   ```python
   def test_ping_endpoint_post_not_allowed(test_client):
       response = test_client.post("/ping")
       assert response.status_code == 405  # Method Not Allowed
   ```

3. **Test CORS Headers** (if configured):
   ```python
   def test_ping_endpoint_cors_headers(test_client):
       response = test_client.options("/ping")
       assert "access-control-allow-origin" in response.headers
   ```

**Recommendation**: Keep Phase 2 minimal (single test) to validate infrastructure. Add these enhancements only if needed for specific requirements.

---

## Verification and Testing

### Running Phase 2 Tests

**Run only Phase 2 tests**:
```bash
uv run pytest tests/api/router/test_base_integration.py -v
```

**Run all integration tests**:
```bash
uv run pytest -m integration -v
```

**Run with coverage**:
```bash
uv run pytest tests/api/router/test_base_integration.py --cov=api.router.base --cov-report=term
```

**Expected Output**:
```
tests/api/router/test_base_integration.py::test_ping_endpoint_returns_pong PASSED [100%]
1 passed in 0.03s
```

### Phase 2 Completion Checklist

- [x] `tests/api/router/test_base_integration.py` created with integration marker
- [x] Test uses `test_client` fixture from `conftest.py`
- [x] Test validates `/ping` endpoint returns "pong" with 200 status
- [x] Test passes when run with `pytest`
- [x] Test can be filtered with `-m integration` marker
- [x] Test runs in under 1 second (no database connection delays)
- [x] Docstrings explain what infrastructure is being validated

---

## Acceptance Criteria

### ✅ Must Have (All Completed)

1. **Test File Exists**:
   - ✅ `tests/api/router/test_base_integration.py` created
   - ✅ Contains at least one test function

2. **Test Functionality**:
   - ✅ Test makes GET request to `/ping` endpoint
   - ✅ Asserts response status code is 200
   - ✅ Asserts response text is "pong"
   - ✅ Uses `@pytest.mark.integration` marker

3. **Test Infrastructure**:
   - ✅ Test uses `test_client` fixture from `conftest.py`
   - ✅ No direct MongoDB connection required
   - ✅ Test is isolated and idempotent

4. **Test Execution**:
   - ✅ Test passes when run with `pytest tests/api/router/test_base_integration.py`
   - ✅ Test can be selected with `pytest -m integration`
   - ✅ Test completes in under 1 second

5. **Code Quality**:
   - ✅ Test has descriptive docstring explaining what it validates
   - ✅ Assertions are clear and separated
   - ✅ Follows project testing conventions

### 🎯 Nice to Have (Optional Enhancements)

- [ ] Additional tests for error cases (POST method not allowed)
- [ ] Tests for response headers validation
- [ ] Tests for CORS configuration (if applicable)
- [ ] Performance benchmarking for response time

---

## Implementation Notes

### Why This Test Doesn't Need Database Mocking

The `/ping` endpoint in `api/router/base.py` is intentionally simple:

```python
@router.get("/ping", response_class=PlainTextResponse)
def read_root():
    return "pong"
```

**No Database Access**:
- Endpoint doesn't call `get_cards_collection`
- No MongoDB queries executed
- Pure function with no external dependencies

**Why Test Still Uses `test_client` Fixture**:
- Maintains consistency with other integration tests
- Validates FastAPI app initialization
- Ensures dependency override mechanism doesn't interfere with non-database endpoints

### Pattern Established for Future Phases

This test demonstrates the standard structure for integration tests:

```python
# 1. Import pytest
import pytest

# 2. Mark as integration test
@pytest.mark.integration

# 3. Use descriptive test function name
def test_<endpoint>_<scenario>(test_client):

    # 4. Comprehensive docstring
    """Explain what infrastructure is being validated."""

    # 5. Make HTTP request via TestClient
    response = test_client.get("/endpoint")

    # 6. Separate assertions for clarity
    assert response.status_code == <expected_code>
    assert response.json() == <expected_data>
```

**This pattern will be reused in**:
- Phase 3: Sets router integration tests
- Phase 4: Cards router basic endpoint tests
- Phase 5: Cards search endpoint tests

---

## Relation to Other Phases

### Phase 1 → Phase 2 (Dependencies)

Phase 2 consumes these Phase 1 deliverables:
- `test_client` fixture for TestClient with dependency overrides
- pytest markers for test categorization
- Mock MongoDB infrastructure (not used in Phase 2, but available)

### Phase 2 → Phase 3 (Foundation)

Phase 3 will extend the pattern established here:
- Similar test structure with `@pytest.mark.integration`
- Uses `test_client` and `test_client_empty` fixtures
- Introduces database mocking for `/sets` endpoint testing

### Phase 2 → Phases 4-7 (Template)

All subsequent phases follow this test structure template.

---

## Success Metrics

### ✅ Phase 2 Success Indicators (All Met)

1. **Test Execution**:
   - ✅ 1/1 tests passing (100% pass rate)
   - ✅ Execution time < 1 second

2. **Code Coverage**:
   - ✅ `api/router/base.py` covered by integration test
   - ✅ `/ping` endpoint has test coverage

3. **Infrastructure Validation**:
   - ✅ TestClient successfully loads FastAPI app
   - ✅ Dependency override mechanism doesn't break simple endpoints
   - ✅ pytest markers work correctly

4. **Documentation**:
   - ✅ Test has clear docstring
   - ✅ Pattern is reusable for future phases

### Measured Results

```bash
$ uv run pytest tests/api/router/test_base_integration.py -v
======================== test session starts =========================
tests/api/router/test_base_integration.py::test_ping_endpoint_returns_pong PASSED [100%]
========================= 1 passed in 0.03s ==========================
```

**Performance**: ✅ 0.03 seconds (well under 1 second target)
**Pass Rate**: ✅ 100% (1/1 tests passing)
**Infrastructure**: ✅ No database connection errors

---

## Troubleshooting Guide

### Common Issues and Solutions

**Issue**: Test fails with "ModuleNotFoundError: No module named 'api'"
- **Cause**: pytest not running from project root
- **Solution**: Ensure `pytest` is run from `/Users/nico/Desktop/coding/mtg/mtg-api/`

**Issue**: Test fails with "fixture 'test_client' not found"
- **Cause**: `conftest.py` not being loaded
- **Solution**: Ensure `tests/conftest.py` exists and contains `test_client` fixture

**Issue**: Test passes but response is JSON instead of plain text
- **Cause**: `response_class=PlainTextResponse` missing from endpoint
- **Solution**: Verify `api/router/base.py` has correct response class configuration

**Issue**: Test takes several seconds to run
- **Cause**: Attempting to connect to real MongoDB
- **Solution**: Verify dependency overrides are working in `conftest.py`

---

## Next Steps

### ✅ Phase 2 Complete - Ready to Proceed to Phase 3

**What's Next**: Phase 3 - Sets Router Integration Tests

Phase 3 will:
- Test `/sets` endpoint with mocked MongoDB aggregation
- Introduce database mocking for the first time
- Test empty database scenarios
- Verify alphabetical sorting of set names

**Prerequisites for Phase 3**:
- ✅ Phase 1 infrastructure complete
- ✅ Phase 2 template established
- ✅ MockMongoCollection supports `aggregate()` method
- ✅ Sample cards fixture includes multiple sets

**Estimated Complexity**: Medium (requires MongoDB aggregation mocking)

---

## References

### Related Files

- **Test File**: `tests/api/router/test_base_integration.py` (23 lines)
- **Endpoint Under Test**: `api/router/base.py:7-9` (`/ping` endpoint)
- **Fixtures**: `tests/conftest.py:37-56` (`test_client` fixture)
- **pytest Config**: `pyproject.toml:84-98` (markers and settings)

### Documentation

- FastAPI Testing Guide: `documentation/fastapi-testing-guide.md`
- MongoDB Mocking Strategy: `documentation/mongodb-mocking-strategy.md`
- Task List: `planning/2025-11-16 - tasks list - fastapi-integration-tests.md`

### External Resources

- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest Fixtures Guide](https://docs.pytest.org/en/stable/fixture.html)
- [TestClient API Reference](https://www.starlette.io/testclient/)

---

## Conclusion

**Phase 2 Status**: ✅ **COMPLETE**

Phase 2 successfully validates the test infrastructure by implementing a simple integration test for the `/ping` endpoint. The test passes consistently, runs quickly (0.03s), and establishes a reusable pattern for future phases.

**Key Achievements**:
- ✅ First integration test implemented and passing
- ✅ Test infrastructure validated (TestClient, fixtures, markers)
- ✅ Pattern established for Phases 3-7
- ✅ Zero database dependencies for simple endpoints confirmed

**Ready for Phase 3**: All prerequisites met, infrastructure proven, template pattern established.
