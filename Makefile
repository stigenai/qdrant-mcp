.PHONY: help install install-dev test format lint type-check run-server run-mcp docker-build docker-run clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make install        Install production dependencies with uv"
	@echo "  make install-dev    Install all dependencies including dev tools"
	@echo "  make test          Run tests with pytest"
	@echo "  make format        Format code with black"
	@echo "  make lint          Lint code with ruff"
	@echo "  make type-check    Type check with mypy"
	@echo "  make run-server    Run the REST API server"
	@echo "  make run-mcp       Run the MCP HTTP server"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-run    Run Docker container"
	@echo "  make clean         Clean up cache files"

# Install production dependencies
install:
	uv pip install --system -r pyproject.toml

# Install all dependencies including dev
install-dev:
	uv pip install --system -e ".[dev]"

# Run tests
test:
	uv run pytest tests/ -v

# Format code
format:
	uv run black .
	uv run ruff check --fix .

# Lint code
lint:
	uv run ruff check .
	uv run black --check .

# Type check
type-check:
	uv run mypy .

# Run servers
run-server:
	uv run python server.py

run-mcp:
	uv run python mcp_server.py

# Docker commands
docker-build:
	docker build -t qdrant-mcp:latest .

docker-build-dev:
	docker build -f Dockerfile.dev -t qdrant-mcp:dev .

docker-run:
	docker run -p 8000:8000 -p 8001:8001 -p 6333:6333 \
		-v $(PWD)/config:/app/config \
		-v qdrant_storage:/qdrant/storage \
		qdrant-mcp:latest

docker-run-dev:
	docker run -it --rm -p 8000:8000 -p 8001:8001 -p 6333:6333 \
		-v $(PWD):/app \
		-v qdrant_storage:/qdrant/storage \
		qdrant-mcp:dev

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/

# Create lock file
lock:
	uv pip compile pyproject.toml -o uv.lock

# Sync dependencies from lock file
sync:
	uv pip sync uv.lock