# Quick Start - Automated Testing

## 🚀 Fastest Way to Test Everything

### Option 1: Quick Test Script (Recommended)
Run the complete tournament flow in one command:

```bash
cd backend
source venv/bin/activate
python quick_test.py
```

This will automatically:
- Create test users (player1, player2)
- Set up a league
- Create a match
- Submit predictions
- Set match results
- Calculate scores
- Display final leaderboard

**Expected Output:**
```
🏏 Fantasy Cricket League - Quick Test
==================================================
✓ Creating tournament and teams...
✓ Signing up users...
✓ Logging in users...
✓ Creating league...
✓ Joining league...
✓ Creating match...
✓ Fetching match players...
✓ Making predictions...
✓ Setting match results...
✓ Checking leaderboard...

📊 Final Leaderboard:
--------------------------------------------------
  Rank 1: player1         - 100 points
  Rank 2: player2         -  10 points

==================================================
✅ All tests passed successfully!
==================================================
```

### Option 2: Full Pytest Suite
Run comprehensive automated tests:

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run only integration tests (tournament flow)
pytest tests/integration/ -v

# Run specific test
pytest tests/integration/test_tournament_flow.py::TestCompleteTournamentFlow::test_complete_tournament_workflow -v
```

## 📋 What Gets Tested

### Complete Tournament Flow Test
The main integration test covers:

1. **User Registration & Authentication**
   - Sign up two users
   - Login and get JWT tokens

2. **League Management**
   - Create a league (player1)
   - Generate unique invite code
   - Join league (player2)

3. **Match Setup**
   - Create upcoming match
   - Fetch available players

4. **Predictions**
   - Player1: Makes perfect predictions (all correct)
   - Player2: Makes partial predictions (only winner correct)

5. **Match Results**
   - Admin sets final results
   - System automatically calculates points

6. **Leaderboard Verification**
   - Player1: 100 points (10+20+20+50)
   - Player2: 10 points (only winner)
   - Correct ranking displayed

### Additional Test Scenarios

**Partial Correct Predictions**
- Tests scoring with mix of correct/incorrect predictions
- Verifies: Winner (10) + Most Runs (20) = 30 points

**Prediction Deadline Enforcement**
- Attempts to predict after match starts
- Expects: 400 error with "already started" message

**Update Predictions**
- Submit initial prediction
- Update before match starts
- Verify update is saved

**Multiple Matches Scoring**
- 3 matches created
- Both users predict all matches
- Points accumulate correctly:
  - Player1: 300 points (3 × 100)
  - Player2: 30 points (3 × 10)

## 🎯 Test Coverage

### Unit Tests (`tests/unit/`)
- **Authentication**: Signup, login, validation
- **Scoring Logic**: Points calculation for all scenarios

### Integration Tests (`tests/integration/`)
- **Complete workflow**: End-to-end tournament flow
- **Edge cases**: Deadlines, updates, multiple matches

## 🔧 Common Test Commands

```bash
# Activate environment (always run first)
source venv/bin/activate

# Quick verification
python quick_test.py

# All tests with verbose output
pytest tests/ -v

# Tests with coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Run only fast tests
pytest tests/ -m "not slow"

# Run integration tests only
pytest tests/integration/ -v

# Run specific test class
pytest tests/integration/test_tournament_flow.py::TestCompleteTournamentFlow -v

# Show print statements
pytest tests/ -v -s
```

## 📊 Understanding Test Results

### Success Output
```
tests/integration/test_tournament_flow.py::TestCompleteTournamentFlow::test_complete_tournament_workflow PASSED
```

### Failure Output
```
FAILED tests/integration/test_tournament_flow.py::TestCompleteTournamentFlow::test_complete_tournament_workflow
AssertionError: assert 90 == 100
```

## 🐛 Troubleshooting

### Issue: "Module not found"
**Solution:**
```bash
# Make sure you're in backend directory
cd backend
source venv/bin/activate
python -m pytest tests/
```

### Issue: "Database locked"
**Solution:**
```bash
# Remove test database
rm test.db quick_test.db
# Run tests again
python quick_test.py
```

### Issue: Tests fail with authentication errors
**Solution:**
Check that `.env` file exists with valid `SECRET_KEY`

## 🎓 Next Steps

1. **Add More Tests**: Create tests for your specific scenarios
2. **Frontend Tests**: Set up Jest for React component testing
3. **E2E Tests**: Add Playwright for browser automation
4. **CI/CD**: Set up GitHub Actions for automatic testing

## 📚 Full Documentation

For detailed documentation, see:
- [TESTING.md](./TESTING.md) - Complete testing guide
- [tests/conftest.py](./backend/tests/conftest.py) - Test fixtures
- [tests/integration/](./backend/tests/integration/) - Integration tests

## 💡 Tips

- Run `quick_test.py` before committing changes
- Use `-v` flag for verbose output
- Use `-s` flag to see print statements
- Tests use isolated database (no impact on dev DB)
- Each test starts with clean state
