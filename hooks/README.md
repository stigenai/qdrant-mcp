# Qdrant MCP API Hooks

These hooks are API-based versions of the standard Claude vector hooks that work with the Qdrant MCP server's REST API instead of a local Qdrant instance.

## Overview

The hooks provide the same functionality as the original Claude vector hooks but communicate with the Qdrant MCP server via HTTP API:

- **precompact_vectorize.py**: Replaces long transcript messages with vector stubs
- **retrieve_vectors.py**: Retrieves relevant vector content for RAG during tool use and user prompts

## Configuration

Both hooks use the `QDRANT_MCP_API` environment variable to specify the API endpoint. The default is `http://localhost:8000`.

```bash
# Set custom API endpoint
export QDRANT_MCP_API="http://your-qdrant-server:8000"
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