import os
from pathlib import Path

# Qdrant configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Vector configuration (matching Claude hooks)
COLLECTION_NAME = "claude_vectors"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384
MAX_TOKENS = 512
TOP_K = 10
MIN_SCORE = 0.22

# Server configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# MCP configuration
MCP_SERVER_NAME = "qdrant-mcp"
MCP_SERVER_VERSION = "1.0.0"
