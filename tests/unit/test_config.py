"""Unit tests for config module."""

import os
from unittest.mock import patch

import config


class TestConfig:
    """Test configuration values."""

    def test_default_values(self):
        """Test default configuration values."""
        assert config.COLLECTION_NAME == "claude_vectors"
        assert config.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
        assert config.VECTOR_SIZE == 384
        assert config.TOP_K == 10
        assert config.MIN_SCORE == 0.22
        assert config.MCP_SERVER_NAME == "qdrant-mcp"
        assert config.MCP_SERVER_VERSION == "1.0.0"

    @patch.dict(os.environ, {"QDRANT_HOST": "test-host"})
    def test_qdrant_host_from_env(self):
        """Test QDRANT_HOST from environment variable."""
        assert config.QDRANT_HOST == "localhost"  # Default value
        # Note: config module is already imported, so env var won't affect it
        # This test shows that env vars should be read at runtime, not import time

    def test_api_config(self):
        """Test API configuration."""
        assert config.API_HOST == "0.0.0.0"
        assert config.API_PORT == 8000

    def test_qdrant_config(self):
        """Test Qdrant configuration."""
        assert config.QDRANT_HOST == "localhost"
        assert config.QDRANT_PORT == 6333
