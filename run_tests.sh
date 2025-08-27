#!/bin/bash
# Script to run tests for the diligence agent project

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Running Diligence Agent Tests..."
echo "================================"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}Warning: Virtual environment not activated${NC}"
    echo "Attempting to activate .venv..."
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    else
        echo -e "${RED}Virtual environment not found. Please create one first.${NC}"
        exit 1
    fi
fi

# Install test dependencies if needed
echo "Checking test dependencies..."
pip install -q pytest pytest-cov pytest-mock

# Run tests with coverage
echo ""
echo "Running unit tests..."
echo "--------------------"

# Run different test categories
if [ "$1" == "unit" ]; then
    echo "Running unit tests only..."
    pytest tests/ -m "not integration and not network" --cov=src/diligence_agent
elif [ "$1" == "integration" ]; then
    echo "Running integration tests..."
    pytest tests/ -m "integration or network"
elif [ "$1" == "all" ]; then
    echo "Running all tests with coverage..."
    pytest tests/ --cov=src/diligence_agent --cov-report=html --cov-report=term
elif [ "$1" == "fast" ]; then
    echo "Running fast tests only..."
    pytest tests/ -m "not slow and not integration and not network"
else
    # Default: run non-integration tests
    echo "Running standard tests (no integration)..."
    pytest tests/ -m "not integration and not network"
fi

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo ""
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi

# Optional: Open coverage report
if [ "$1" == "all" ] && [ -d "htmlcov" ]; then
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
    read -p "Open coverage report in browser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open htmlcov/index.html 2>/dev/null || xdg-open htmlcov/index.html 2>/dev/null
    fi
fi