"""Unit tests for MCP handler."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import uuid
from mcp.types import TextContent
from mcp_handler import MCPHandler
import config


class TestMCPHandler:
    """Test MCP handler functionality."""

    @pytest.fixture
    def mcp_handler(self, mock_qdrant_client, mock_embedder):
        """Create MCP handler with mocks."""
        return MCPHandler(mock_qdrant_client, mock_embedder)

    @pytest.mark.asyncio
    async def test_handle_store_success(
        self, mcp_handler, mock_qdrant_client, mock_embedder
    ):
        """Test successful storage of content."""
        arguments = {
            "content": "Test content to store",
            "metadata": {"source": "test"},
            "collection": "test_collection",
        }

        # Mock collection doesn't exist
        mock_qdrant_client.get_collection.side_effect = Exception(
            "Collection not found"
        )

        with patch(
            "uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")
        ):
            result = await mcp_handler._handle_store(arguments)

        # Verify collection was created
        mock_qdrant_client.create_collection.assert_called_once()

        # Verify embedding was generated
        mock_embedder.encode.assert_called_once_with("Test content to store")

        # Verify upsert was called
        mock_qdrant_client.upsert.assert_called_once()

        # Check result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert (
            "Successfully stored content with ID: 12345678-1234-5678-1234-567812345678"
            in result[0].text
        )

    @pytest.mark.asyncio
    async def test_handle_store_no_content(self, mcp_handler):
        """Test storage with no content."""
        arguments = {"metadata": {"source": "test"}}

        result = await mcp_handler._handle_store(arguments)

        assert len(result) == 1
        assert "Error: No content provided" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_find_success(
        self, mcp_handler, mock_qdrant_client, mock_embedder
    ):
        """Test successful content search."""
        arguments = {
            "query": "test query",
            "limit": 5,
            "score_threshold": 0.5,
            "collection": "claude_vectors",
        }

        result = await mcp_handler._handle_find(arguments)

        # Verify embedding was generated for query
        mock_embedder.encode.assert_called_once_with("test query")

        # Verify search was called
        mock_qdrant_client.search.assert_called_once()

        # Check result formatting
        assert len(result) == 1
        assert "Found 2 results" in result[0].text
        assert "Test content 1" in result[0].text
        assert "Test content 2" in result[0].text
        assert "score: 0.950" in result[0].text
        assert "score: 0.850" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_find_no_query(self, mcp_handler):
        """Test search with no query."""
        arguments = {"limit": 5}

        result = await mcp_handler._handle_find(arguments)

        assert len(result) == 1
        assert "Error: No query provided" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_find_no_results(
        self, mcp_handler, mock_qdrant_client, mock_embedder
    ):
        """Test search with no results."""
        arguments = {"query": "test query"}

        # Mock empty search results
        mock_qdrant_client.search.return_value = []

        result = await mcp_handler._handle_find(arguments)

        assert len(result) == 1
        assert "No relevant results found" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_list_collections(self, mcp_handler, mock_qdrant_client):
        """Test listing collections."""
        result = await mcp_handler._handle_list_collections()

        mock_qdrant_client.get_collections.assert_called_once()

        assert len(result) == 1
        assert "Collections:" in result[0].text
        assert "- claude_vectors" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_list_collections_empty(self, mcp_handler, mock_qdrant_client):
        """Test listing collections when none exist."""
        mock_qdrant_client.get_collections.return_value = Mock(collections=[])

        result = await mcp_handler._handle_list_collections()

        assert len(result) == 1
        assert "No collections found" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_create_collection_success(
        self, mcp_handler, mock_qdrant_client
    ):
        """Test successful collection creation."""
        arguments = {"name": "new_collection", "vector_size": 512}

        result = await mcp_handler._handle_create_collection(arguments)

        mock_qdrant_client.create_collection.assert_called_once()
        call_args = mock_qdrant_client.create_collection.call_args
        assert call_args[1]["collection_name"] == "new_collection"
        assert call_args[1]["vectors_config"].size == 512

        assert len(result) == 1
        assert "Successfully created collection 'new_collection'" in result[0].text
        assert "vector size 512" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_create_collection_no_name(self, mcp_handler):
        """Test collection creation without name."""
        arguments = {"vector_size": 512}

        result = await mcp_handler._handle_create_collection(arguments)

        assert len(result) == 1
        assert "Error: No collection name provided" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_store_exception(
        self, mcp_handler, mock_qdrant_client, mock_embedder
    ):
        """Test error handling in store operation."""
        arguments = {"content": "Test content"}

        # Mock an exception
        mock_embedder.encode.side_effect = Exception("Embedding error")

        result = await mcp_handler._handle_store(arguments)

        assert len(result) == 1
        assert "Failed to store content: Embedding error" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_find_exception(
        self, mcp_handler, mock_qdrant_client, mock_embedder
    ):
        """Test error handling in find operation."""
        arguments = {"query": "test query"}

        # Mock an exception
        mock_qdrant_client.search.side_effect = Exception("Search error")

        result = await mcp_handler._handle_find(arguments)

        assert len(result) == 1
        assert "Failed to search: Search error" in result[0].text
