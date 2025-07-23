# Qdrant MCP Server

A unified Docker container that runs both a Qdrant vector database server and provides REST API + MCP (Model Context Protocol) interfaces for vector operations. This server is designed to be compatible with Claude vector hooks.

## Features

- **Single Docker Container**: Runs Qdrant server, REST API, and MCP HTTP server in one container
- **REST API**: Compatible with Claude vector hooks for storing and searching vectors (port 8000)
- **MCP HTTP Server**: Accessible via mcp-remote for semantic memory capabilities (port 8001)
- **Auto-embedding**: Automatically generates embeddings using sentence-transformers
- **Claude Hooks Compatible**: Works with existing Claude vector hooks in `~/.claude/hooks/`

## Quick Start

### Build the Docker Image

```bash
docker build -t qdrant-mcp .
```

### Run the Container

```bash
# Run with default settings
docker run -p 8000:8000 -p 8001:8001 -p 6333:6333 -v qdrant-data:/qdrant/storage qdrant-mcp

# Run with custom settings
docker run -p 8000:8000 -p 8001:8001 -p 6333:6333 \
  -v qdrant-data:/qdrant/storage \
  -e API_PORT=8000 \
  -e MCP_PORT=8001 \
  qdrant-mcp
```

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

## Environment Variables

- `QDRANT_HOST`: Qdrant server host (default: localhost)
- `QDRANT_PORT`: Qdrant server port (default: 6333)
- `API_HOST`: API server host (default: 0.0.0.0)
- `API_PORT`: API server port (default: 8000)
- `MCP_PORT`: MCP HTTP server port (default: 8001)

## Claude Hooks Integration

This server is designed to work with Claude vector hooks. The hooks expect:

- Collection name: `claude_vectors`
- Embedding model: `all-MiniLM-L6-v2`
- Vector size: 384
- Distance metric: Cosine

The REST API endpoints are compatible with the operations performed by:
- `precompact_vectorize.py`: Stores vectors
- `retrieve_vectors.py`: Searches vectors

## Development

To run locally without Docker:

1. Install Qdrant locally
2. Install Python dependencies: `pip install -r requirements.txt`
3. Start Qdrant server
4. Run the API server: `python server.py`

## License

MIT