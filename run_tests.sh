#!/bin/bash

echo "Qdrant MCP Test Runner"
echo "====================="
echo
echo "This script helps run the tests for the Qdrant MCP project using uv."
echo
echo "Prerequisites:"
echo "- Python 3.10+"
echo "- uv package manager (https://github.com/astral-sh/uv)"
echo
echo "To install uv:"
echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
echo "   # or"
echo "   pip install uv"
echo
echo "To run tests locally:"
echo "1. Install dependencies:"
echo "   uv pip install --system -e '.[dev]'"
echo "   # or using Makefile"
echo "   make install-dev"
echo
echo "2. Run tests:"
echo "   uv run pytest -v                  # Run all tests with verbose output"
echo "   uv run pytest --cov=.             # Run with coverage report"
echo "   uv run pytest tests/unit/         # Run only unit tests"
echo "   # or using Makefile"
echo "   make test"
echo
echo "3. Format and lint code:"
echo "   uv run black ."
echo "   uv run ruff check ."
echo "   # or using Makefile"
echo "   make format"
echo "   make lint"
echo
echo "Test files created:"
ls -la tests/unit/test_*.py 2>/dev/null || echo "   No test files found in tests/unit/"
echo
echo "GitHub Actions will automatically run these tests on push/PR."