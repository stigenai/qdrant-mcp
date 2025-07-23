"""Unit tests for MCP HTTP server."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from mcp.types import TextContent
import mcp_server
import config


class TestMCPServer:
    """Test MCP HTTP server functionality."""

    @pytest.fixture
    def client(self, mock_qdrant_client, mock_embedder):
        """Create test client with mocks."""
        # Patch the handler's dependencies
        with patch("mcp_server.qdrant_client", mock_qdrant_client):
            with patch("mcp_server.embedder", mock_embedder):
                # Create a new handler instance
                from mcp_server import app

                return TestClient(app)

    def test_mcp_initialize(self, client):
        """Test MCP initialize request."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
            "id": "1",
        }

        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "1"
        assert "result" in data
        assert data["result"]["protocolVersion"] == "2024-11-05"
        assert data["result"]["serverInfo"]["name"] == config.MCP_SERVER_NAME
        assert data["result"]["serverInfo"]["version"] == config.MCP_SERVER_VERSION

    def test_mcp_tools_list(self, client):
        """Test listing available tools."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": "2",
        }

        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "2"
        assert "result" in data
        assert "tools" in data["result"]

        # Check that all expected tools are listed
        tool_names = [tool["name"] for tool in data["result"]["tools"]]
        assert "store" in tool_names
        assert "find" in tool_names
        assert "list_collections" in tool_names
        assert "create_collection" in tool_names

    def test_mcp_tool_call_store(self, client, mock_qdrant_client, mock_embedder):
        """Test calling the store tool."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "store",
                "arguments": {
                    "content": "Test content to store",
                    "metadata": {"source": "test"},
                    "collection": "claude_vectors",
                },
            },
            "id": "3",
        }

        # Mock collection exists
        mock_qdrant_client.get_collection.return_value = Mock()

        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "3"
        assert "result" in data
        assert "content" in data["result"]
        assert len(data["result"]["content"]) > 0

        # Verify operations were called
        mock_embedder.encode.assert_called_with("Test content to store")
        mock_qdrant_client.upsert.assert_called_once()

    def test_mcp_tool_call_find(self, client, mock_qdrant_client, mock_embedder):
        """Test calling the find tool."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "find",
                "arguments": {
                    "query": "test query",
                    "limit": 5,
                    "collection": "claude_vectors",
                },
            },
            "id": "4",
        }

        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "4"
        assert "result" in data
        assert "content" in data["result"]

        # Verify operations were called
        mock_embedder.encode.assert_called_with("test query")
        mock_qdrant_client.search.assert_called_once()

    def test_mcp_tool_call_list_collections(self, client, mock_qdrant_client):
        """Test calling the list_collections tool."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "list_collections", "arguments": {}},
            "id": "5",
        }

        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "5"
        assert "result" in data

        # Verify operations were called
        mock_qdrant_client.get_collections.assert_called_once()

    def test_mcp_tool_call_invalid_tool(self, client):
        """Test calling a non-existent tool."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "invalid_tool", "arguments": {}},
            "id": "6",
        }

        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "6"
        assert "error" in data
        assert data["error"]["code"] == -32601
        assert "Unknown tool" in data["error"]["message"]

    def test_mcp_invalid_method(self, client):
        """Test calling an invalid method."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "invalid/method",
            "params": {},
            "id": "7",
        }

        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "7"
        assert "error" in data
        assert data["error"]["code"] == -32601
        assert "Method not found" in data["error"]["message"]

    def test_mcp_invalid_json(self, client):
        """Test sending invalid JSON."""
        response = client.post("/", data="invalid json")
        assert response.status_code == 400

    def test_mcp_missing_jsonrpc(self, client):
        """Test request missing jsonrpc field."""
        request_data = {"method": "initialize", "params": {}, "id": "8"}

        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == -32600
        assert "Invalid Request" in data["error"]["message"]

    def test_mcp_notification(self, client):
        """Test MCP notification (no id field)."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }

        response = client.post("/", json=request_data)
        # Notifications should be accepted but no response
        assert response.status_code == 200
        assert response.text == ""

    def test_mcp_batch_request(self, client):
        """Test batch JSON-RPC request."""
        request_data = [
            {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "batch-1"},
            {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "batch-2"},
        ]

        response = client.post("/", json=request_data)
        assert response.status_code == 200
        data = response.json()

        # Should return an array of responses
        assert isinstance(data, list)
        assert len(data) == 2
        assert all(r["jsonrpc"] == "2.0" for r in data)
        assert data[0]["id"] == "batch-1"
        assert data[1]["id"] == "batch-2"
