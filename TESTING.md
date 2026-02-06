# Testing Guide - Fantasy Cricket League

This document explains how to test the Fantasy Cricket League application using automated tests.

## Overview

The testing suite includes:
- **Unit Tests**: Test individual functions and components in isolation
- **Integration Tests**: Test complete workflows and API endpoints
- **End-to-End Tests**: Test the entire tournament flow from start to finish

## Backend Testing

### Setup

1. Install test dependencies:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Running Tests

#### Run All Tests
```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

#### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v -m integration

# Specific test file
pytest tests/integration/test_tournament_flow.py -v

# Specific test
pytest tests/integration/test_tournament_flow.py::TestCompleteTournamentFlow::test_complete_tournament_workflow -v
```

#### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html
# Open htmlcov/index.html to see coverage report
```

### Test Categories

#### 1. Authentication Tests (`tests/unit/test_auth.py`)
Tests user signup and login flows:
- Successful signup with valid data
- Duplicate username/email detection
- Successful login with correct credentials
- Invalid login attempts

#### 2. Scoring Logic Tests (`tests/unit/test_scoring.py`)
Tests the points calculation system:
- Perfect predictions (100 points)
- No correct predictions (0 points)
- Partial correct predictions (varying points)

#### 3. Complete Tournament Flow (`tests/integration/test_tournament_flow.py`)

**Test: Complete Tournament Workflow**
This is the main integration test that simulates a full tournament:

1. **User Registration**: Two users sign up
2. **League Creation**: User 1 creates a league
3. **League Joining**: User 2 joins via invite code
4. **Match Creation**: Admin creates an upcoming match
5. **Predictions**: Both users make predictions
6. **Results**: Admin sets match results
7. **Scoring**: System calculates points automatically
8. **Leaderboard**: Verify correct rankings

Expected Results:
- User 1 (perfect predictions): 100 points (Rank 1)
- User 2 (no correct predictions): 0 points (Rank 2)

**Test: Partial Correct Predictions**
Tests scoring when only some predictions are correct.

**Test: Prediction Deadline Enforcement**
Verifies that predictions cannot be made after a match starts.

**Test: Update Prediction Before Match**
Ensures users can modify predictions before match start time.

**Test: Multiple Matches Leaderboard**
Tests cumulative scoring across multiple matches:
- User 1 makes perfect predictions for 3 matches: 300 points
- User 2 only predicts winners correctly: 30 points

## Test Fixtures

The test suite uses pytest fixtures defined in `tests/conftest.py`:

### Database Fixtures
- `db_engine`: Creates a fresh test database for each test
- `db_session`: Provides a database session
- `client`: FastAPI test client with database override

### User Fixtures
- `test_user`: Creates a test user (username: testuser)
- `test_user2`: Creates a second test user
- `auth_token`: Generates JWT token for test user
- `auth_headers`: Authorization headers for authenticated requests

### Match Fixtures
- `test_tournament`: Creates a test tournament
- `test_teams`: Creates two teams with 11 players each
- `test_match`: Creates a scheduled match
- `completed_match`: Creates a completed match with results

### League Fixtures
- `test_league`: Creates a test league with owner
- `test_prediction`: Creates a sample prediction

## Test Data

### Points System
- Match Winner: +10 points
- Most Runs Player: +20 points
- Most Wickets Player: +20 points
- Player of the Match: +50 points
- **Maximum per match: 100 points**

### Sample Test Flow

```python
# Example: Testing a complete user journey
def test_user_journey(client):
    # 1. Sign up
    response = client.post("/auth/signup", json={
        "username": "player1",
        "email": "player1@test.com",
        "password": "secure123"
    })
    assert response.status_code == 201

    # 2. Login
    response = client.post("/auth/login", data={
        "username": "player1",
        "password": "secure123"
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create league
    response = client.post("/leagues/",
        json={"name": "My League"},
        headers=headers
    )
    league_id = response.json()["id"]

    # 4. Make predictions, set results, check leaderboard...
```

## Continuous Integration

### GitHub Actions (Optional)

Create `.github/workflows/test.yml`:

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v --cov=app
```

## Writing New Tests

### Structure
```python
import pytest

@pytest.mark.integration  # or @pytest.mark.unit
class TestFeatureName:
    """Test description."""

    def test_specific_scenario(self, client, auth_headers):
        """Test case description."""
        # Arrange
        data = {...}

        # Act
        response = client.post("/endpoint", json=data, headers=auth_headers)

        # Assert
        assert response.status_code == 200
        assert response.json()["field"] == "expected_value"
```

### Best Practices
1. **Descriptive Names**: Test names should describe what they test
2. **Single Responsibility**: Each test should test one thing
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Use Fixtures**: Reuse common setup code
5. **Test Edge Cases**: Include boundary conditions and error cases

## Troubleshooting

### Common Issues

**Issue**: Tests fail with database errors
**Solution**: Ensure test database is being created fresh for each test

**Issue**: Authentication tests fail
**Solution**: Check that JWT secret key is set in test environment

**Issue**: Timezone-related failures
**Solution**: All datetime objects should use `timezone.utc`

## Manual Testing Checklist

For manual verification, test this flow:

- [ ] User can sign up with unique credentials
- [ ] User can log in with correct credentials
- [ ] User can create a league and get invite code
- [ ] Another user can join using invite code
- [ ] Users can view upcoming matches
- [ ] Users can make predictions before match starts
- [ ] Users cannot predict after match starts
- [ ] Users can update predictions before match starts
- [ ] Admin can set match results
- [ ] Points are calculated correctly
- [ ] Leaderboard shows correct rankings
- [ ] Points accumulate across multiple matches

## Performance Testing

To test with larger datasets:

```bash
# Create 100 users and 50 matches
pytest tests/performance/test_load.py -v
```

## Monitoring Test Coverage

Current test coverage targets:
- **Overall**: 80%+
- **Critical paths** (auth, predictions, scoring): 95%+
- **Admin endpoints**: 70%+

Run coverage report:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Next Steps

1. Add frontend tests using Jest and React Testing Library
2. Add E2E tests using Playwright
3. Add performance tests for load testing
4. Set up CI/CD pipeline
5. Add database migration tests
