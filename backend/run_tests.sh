#!/bin/bash

# Fantasy Cricket League - Test Runner Script

set -e

echo "🏏 Fantasy Cricket League - Running Tests"
echo "========================================"

# Activate virtual environment
source venv/bin/activate

# Run all tests
echo ""
echo "Running all tests..."
pytest tests/ -v

# Run with coverage
echo ""
echo "Running tests with coverage..."
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

echo ""
echo "✅ All tests completed!"
echo "📊 Coverage report generated in htmlcov/index.html"
