# Qdrant MCP Server

A unified Docker container that runs both a Qdrant vector database server and provides REST API + MCP (Model Context Protocol) interfaces for vector operations. This server is designed to be compatible with Claude vector hooks.

## Features

- **Single Docker Container**: Runs Qdrant server, REST API, and MCP HTTP server in one container
- **REST API**: Compatible with Claude vector hooks for storing and searching vectors (port 8000)
- **MCP HTTP Server**: Accessible via mcp-remote for semantic memory capabilities (port 8001)
- **Auto-embedding**: Automatically generates embeddings using sentence-transformers
- **Claude Hooks Compatible**: Works with existing Claude vector hooks in `~/.claude/hooks/`

## Prerequisites

- Python 3.10+ 
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for containerized deployment)

### Installing uv

```bash
# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv
```

## Quick Start

### Local Development with uv

```bash
# Clone the repository
git clone https://github.com/qdrant/mcp-server-qdrant.git
cd mcp-server-qdrant

# Install dependencies
uv pip install --system -e ".[dev]"

# Or using Makefile
make install-dev

# Run the server
uv run python server.py

# Run tests
uv run pytest
# Or using Makefile
make test
```

### Build the Docker Image

```bash
# Standard build (using uv)
docker build -t qdrant-mcp .

# Development build
docker build -f Dockerfile.dev -t qdrant-mcp:dev .

# Or using Makefile
make docker-build
make docker-build-dev
```

### Run the Container

```bash
# Basic usage
docker run -p 8000:8000 -p 8001:8001 -p 6333:6333 -v qdrant-data:/qdrant/storage qdrant-mcp

# Development mode with live code reload
docker run -it --rm -p 8000:8000 -p 8001:8001 -p 6333:6333 \
  -v $(pwd):/app \
  -v qdrant-data:/qdrant/storage \
  qdrant-mcp:dev

# Secure production deployment (recommended)
docker run -d --name qdrant-mcp \
  --security-opt no-new-privileges:true \
  --read-only \
  --tmpfs /tmp --tmpfs /var/run --tmpfs /var/log/supervisor \
  -v qdrant-data:/qdrant/storage \
  -p 127.0.0.1:8000:8000 \
  -p 127.0.0.1:8001:8001 \
  -p 127.0.0.1:6333:6333 \
  qdrant-mcp:secure

# Using Docker Compose with security settings
docker-compose -f docker-compose.secure.yml up -d
```

## Security Features

- **Rootless Container**: Runs as non-root user (UID 1000)
- **Multi-stage Build**: Minimizes image size and attack surface
- **Read-only Filesystem**: Uses read-only root with specific tmpfs mounts
- **Resource Limits**: CPU and memory constraints in docker-compose
- **Health Checks**: Built-in health monitoring for all services
- **Security Scanning**: Compatible with Trivy and other scanners
- **Minimal Dependencies**: Only essential runtime packages included

## REST API Endpoints

### Health Check
```
GET /health
```

### Collections Management
```
GET /collections/{collection_name}
POST /collections
{
  "name": "my_collection",
  "vector_size": 384,
  "distance": "cosine"
}
```

### Vector Operations
```
POST /vectors/upsert
{
  "collection": "claude_vectors",
  "points": [
    {
      "id": "unique-id",
      "content": "Text to embed",
      "payload": {
        "role": "user",
        "timestamp": "2024-01-01T00:00:00Z"
      }
    }
  ]
}

POST /vectors/search
{
  "query": "search query",
  "collection": "claude_vectors",
  "limit": 10,
  "score_threshold": 0.22
}
```

## MCP Server Tools

When connected as an MCP server, the following tools are available:

- **qdrant-store**: Store information with semantic search capability
- **qdrant-find**: Find relevant information using semantic search
- **qdrant-list-collections**: List all collections
- **qdrant-create-collection**: Create a new collection

### MCP HTTP Server Configuration

The MCP server runs on port 8001 and can be accessed via mcp-remote:

```bash
# Install mcp-remote if not already installed
npm install -g @modelcontextprotocol/server-mcp-remote

# Add to your Claude Code settings:
```

```json
{
  "mcpServers": {
    "qdrant-mcp": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-mcp-remote", "http://localhost:8001"]
    }
  }
}
```

Or use the stdio mode (requires container to be installed locally):

```json
{
  "mcpServers": {
    "qdrant-mcp": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "qdrant-mcp", "python3", "/app/server.py", "--mcp"]
    }
  }
}
```

## Configuration

The server supports both environment variables and configuration files (YAML/JSON).

### Configuration File

Create a `config/config.yaml` file to customize settings:

```yaml
qdrant:
  data_path: /custom/path/to/storage
  snapshots_path: /custom/path/to/snapshots
  
vector:
  collection_name: my_vectors
  embedding_model: all-MiniLM-L6-v2
  
api:
  port: 8080
  
security:
  api_key: your-secret-key
```

Mount the config file in Docker:
```bash
docker run -v $(pwd)/config/config.yaml:/app/config/config.yaml:ro qdrant-mcp
```

### Environment Variables

All settings can also be configured via environment variables:

- **Qdrant Configuration**:
  - `QDRANT_HOST`: Qdrant server host (default: localhost)
  - `QDRANT_PORT`: Qdrant server port (default: 6333)
  - `QDRANT_DATA_PATH`: Data storage path (default: /qdrant/storage)
  - `QDRANT_SNAPSHOTS_PATH`: Snapshots path (default: /qdrant/snapshots)
  - `QDRANT_TELEMETRY_DISABLED`: Disable telemetry (default: true)

- **API Configuration**:
  - `API_HOST`: API server host (default: 0.0.0.0)
  - `API_PORT`: API server port (default: 8000)
  - `MCP_PORT`: MCP HTTP server port (default: 8001)

- **Vector Configuration**:
  - `COLLECTION_NAME`: Default collection (default: claude_vectors)
  - `EMBEDDING_MODEL`: Model name (default: all-MiniLM-L6-v2)
  - `VECTOR_SIZE`: Vector dimensions (default: 384)
  - `MAX_TOKENS`: Max tokens before vectorization (default: 512)

- **Security Configuration**:
  - `API_KEY`: Optional API key for authentication
  - `ENABLE_TLS`: Enable HTTPS (default: false)

### Generate Configuration

Use the included script to generate configuration files:

```bash
# Generate default config
python generate_config.py

# Generate production config
python generate_config.py --production --api-key $(openssl rand -base64 32)

# Custom paths
python generate_config.py --data-path /data/qdrant --snapshots-path /data/snapshots
```

## Development

### Setting Up Development Environment

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter the repository
git clone https://github.com/qdrant/mcp-server-qdrant.git
cd mcp-server-qdrant

# Install all dependencies including dev tools
uv pip install --system -e ".[dev]"
# Or using Makefile
make install-dev
```

### Development Workflow

```bash
# Format code
uv run black .
uv run ruff check --fix .
# Or using Makefile
make format

# Run linting
uv run ruff check .
uv run black --check .
# Or using Makefile
make lint

# Type checking
uv run mypy .
# Or using Makefile
make type-check

# Run tests
uv run pytest -v
uv run pytest --cov=.
# Or using Makefile
make test

# Run servers locally
uv run python server.py                    # REST API server
uv run python mcp_server.py               # MCP HTTP server
# Or using Makefile
make run-server
make run-mcp
```

### Using the Makefile

The project includes a comprehensive Makefile for common tasks:

```bash
make help           # Show all available commands
make install        # Install production dependencies
make install-dev    # Install all dependencies including dev
make test          # Run tests
make format        # Format code
make lint          # Lint code
make type-check    # Type check with mypy
make docker-build  # Build Docker image
make docker-run    # Run Docker container
make clean         # Clean up cache files
```

### Running with Hydra Configuration

The project uses Hydra for configuration management:

```bash
# Run with default configuration
uv run python server.py

# Run with development configuration
uv run python server.py --config-name=config_development

# Override specific values
uv run python server.py qdrant.port=6334 api.port=8080

# Run in MCP stdio mode
uv run python server.py mcp.stdio_mode=true

# See CONFIG.md for full configuration documentation
```

## Claude Hooks Integration

This server is designed to work with Claude vector hooks. The hooks expect:

- Collection name: `claude_vectors`
- Embedding model: `all-MiniLM-L6-v2`
- Vector size: 384
- Distance metric: Cosine

The REST API endpoints are compatible with the operations performed by:
- `precompact_vectorize.py`: Stores vectors
- `retrieve_vectors.py`: Searches vectors

### API-Based Hooks

This repository includes API-based versions of the Claude vector hooks in the `hooks/` directory. These hooks communicate with the Qdrant MCP server via REST API instead of using a local Qdrant instance.

#### Installation

```bash
# Run the setup script
./hooks/setup.sh

# Or manually create symlinks
ln -sf "$(pwd)/hooks/precompact_vectorize.py" ~/.claude/hooks/precompact_vectorize_api.py
ln -sf "$(pwd)/hooks/retrieve_vectors.py" ~/.claude/hooks/retrieve_vectors_api.py
```

#### Configuration

Set the API endpoint (default: http://localhost:8000):
```bash
export QDRANT_MCP_API="http://your-server:8000"
```

#### Benefits

- **No local dependencies**: Works without local Qdrant or sentence-transformers
- **Centralized storage**: All vectors stored in the containerized Qdrant
- **Server-side processing**: Embedding generation handled by the server
- **Easy deployment**: Just point to your API endpoint

## Development

To run locally without Docker:

1. Install Qdrant locally
2. Install Python dependencies: `pip install -r requirements.txt`
3. Start Qdrant server
4. Run the API server: `python server.py`

### Running Tests

The project includes comprehensive unit tests with mocking for local development.

#### Install Test Dependencies
```bash
pip install -r requirements.txt  # Includes test dependencies
```

#### Run All Tests
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_rest_api.py

# Run with verbose output
pytest -v

# Run with test timing
pytest --durations=10
```

#### Test Structure
```
tests/
├── conftest.py           # Shared fixtures and mocks
├── unit/
│   ├── test_config.py    # Configuration tests
│   ├── test_mcp_handler.py  # MCP handler tests
│   ├── test_rest_api.py     # REST API endpoint tests
│   └── test_mcp_server.py   # MCP HTTP server tests
└── __init__.py
```

#### Key Features of Tests
- **No Docker/Qdrant Required**: All tests use mocks, so you can run them without Docker or Qdrant
- **Fast Execution**: Mocked dependencies make tests run quickly
- **Comprehensive Coverage**: Tests cover all major functionality
- **Async Support**: Tests properly handle async operations

#### Running Specific Test Categories
```bash
# Run only unit tests
pytest tests/unit/

# Run tests matching a pattern
pytest -k "test_store"

# Run tests with specific markers (when added)
pytest -m "unit"
```

#### Continuous Integration
Tests automatically run on GitHub Actions for:
- Multiple Python versions (3.10, 3.11, 3.12)
- Code formatting checks (black)
- Docker build verification
- Service health checks

## License

MIT