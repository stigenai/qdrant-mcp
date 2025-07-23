#!/bin/bash

echo "Qdrant MCP Test Runner"
echo "====================="
echo
echo "This script helps run the tests for the Qdrant MCP project."
echo
echo "Prerequisites:"
echo "- Python 3.10+ with pip"
echo "- Virtual environment (recommended)"
echo
echo "To run tests locally:"
echo "1. Create a virtual environment:"
echo "   python -m venv venv"
echo
echo "2. Activate the virtual environment:"
echo "   source venv/bin/activate  # On Linux/Mac"
echo "   venv\\Scripts\\activate     # On Windows"
echo
echo "3. Install dependencies:"
echo "   pip install -r requirements.txt"
echo
echo "4. Run tests:"
echo "   pytest -v                  # Run all tests with verbose output"
echo "   pytest --cov=.             # Run with coverage report"
echo "   pytest tests/unit/         # Run only unit tests"
echo
echo "Test files created:"
ls -la tests/unit/test_*.py 2>/dev/null || echo "   No test files found in tests/unit/"
echo
echo "GitHub Actions will automatically run these tests on push/PR."