# Qdrant MCP API Hooks

These hooks are API-based versions of the standard Claude vector hooks that work with the Qdrant MCP server's REST API instead of a local Qdrant instance.

## Overview

The hooks provide the same functionality as the original Claude vector hooks but communicate with the Qdrant MCP server via HTTP API:

- **precompact_vectorize.py**: Replaces long transcript messages with vector stubs
- **retrieve_vectors.py**: Retrieves relevant vector content for RAG during tool use and user prompts

## Configuration

The hooks support flexible configuration through environment variables:

### Basic Configuration

```bash
# Option 1: Set complete API endpoint (auto-detects HTTPS from URL)
export QDRANT_MCP_API="https://your-qdrant-server:8443"

# Option 2: Set host and port separately
export QDRANT_MCP_HOST="your-qdrant-server"  # or "https://your-qdrant-server"
export QDRANT_MCP_PORT="8000"

# If not set, defaults to http://localhost:8000
```

### HTTPS Configuration

HTTPS is automatically enabled when:
- The API endpoint starts with `https://`
- The host starts with `https://`
- The port is set to `443`

```bash
# SSL/TLS Certificate Options
export QDRANT_MCP_VERIFY_SSL="true"              # Verify SSL certificates (default: true)
export QDRANT_MCP_SSL_CERT="/path/to/cert.pem"   # Path to SSL certificate file
export QDRANT_MCP_CA_BUNDLE="/path/to/ca.pem"    # Path to CA bundle file
export QDRANT_MCP_CA_CERTS_DIR="/path/to/certs"  # Directory containing CA certificates

# Disable SSL verification (not recommended for production)
export QDRANT_MCP_VERIFY_SSL="false"
```

### Example Configurations

```bash
# Local development (HTTP)
export QDRANT_MCP_API="http://localhost:8000"

# Production with HTTPS
export QDRANT_MCP_API="https://qdrant.example.com:8443"

# HTTPS with custom CA certificate
export QDRANT_MCP_API="https://qdrant.internal:8443"
export QDRANT_MCP_CA_BUNDLE="/etc/ssl/certs/company-ca.pem"

# HTTPS with self-signed certificate (development only)
export QDRANT_MCP_API="https://localhost:8443"
export QDRANT_MCP_VERIFY_SSL="false"
```

## Installation

1. Copy these hooks to your Claude hooks directory:
```bash
cp hooks/*.py ~/.claude/hooks/
```

2. Or create symlinks to use them directly from this repository:
```bash
ln -sf "$(pwd)/hooks/precompact_vectorize.py" ~/.claude/hooks/precompact_vectorize_api.py
ln -sf "$(pwd)/hooks/retrieve_vectors.py" ~/.claude/hooks/retrieve_vectors_api.py
```

3. Ensure the Qdrant MCP server is running:
```bash
docker run -p 8000:8000 -p 8001:8001 -p 6333:6333 -v qdrant-data:/qdrant/storage qdrant-mcp
```

## Usage

The hooks work exactly like the original Claude vector hooks but use the REST API:

### precompact_vectorize.py

This hook processes transcript files and replaces long messages (>512 tokens) with vector stubs:

```json
{
  "hook_event_name": "TranscriptProcess",
  "payload": {
    "transcript_path": "~/.claude/transcripts/transcript_123.jsonl"
  }
}
```

The hook will:
1. Read the transcript file
2. For messages with >512 tokens:
   - Store the content in Qdrant via API
   - Replace the content with `[[VEC:uuid]]` stub
3. Update the transcript file atomically

### retrieve_vectors.py

This hook retrieves relevant context during user prompts and tool use:

```json
{
  "hook_event_name": "UserPromptSubmit",
  "prompt": "How do I implement authentication?"
}
```

Or for tool use:
```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Read",
  "tool_input": {
    "file_path": "/path/to/file.py"
  }
}
```

The hook will:
1. Extract a query from the prompt or tool input
2. Search for relevant vectors via API
3. Return enriched context or block with relevant information

## Key Differences from Original Hooks

1. **No local dependencies**: No need for local Qdrant or sentence-transformers installation
2. **API-based**: All operations go through the REST API
3. **Server-side embeddings**: The server handles embedding generation
4. **Centralized storage**: Vectors are stored in the containerized Qdrant instance

## Error Handling

Both hooks are designed to fail gracefully:
- If the API is unavailable, hooks will log warnings but allow operations to continue
- Missing collections are automatically created
- Failed vectorization doesn't block transcript processing

## Performance Considerations

- The hooks add network latency compared to local operations
- Batch operations are used where possible to minimize API calls
- The server handles embedding generation, which may be faster/slower depending on hardware

## Debugging

To see detailed output, redirect stderr:
```bash
python hooks/precompact_vectorize.py 2>debug.log
```

Check API connectivity:
```bash
curl http://localhost:8000/health
```