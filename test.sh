#!/bin/bash

# Quick Test Runner for Fantasy Cricket League
# This script works even without Xcode Command Line Tools

cd "$(dirname "$0")/backend"

echo "Activating virtual environment..."
source venv/bin/activate

echo "Running tests..."
python simple_test.py

exit $?
