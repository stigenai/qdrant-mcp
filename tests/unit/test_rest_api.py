"""Unit tests for REST API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
import uuid
from qdrant_client import models
import server
import config


class TestRestAPI:
    """Test REST API endpoints."""

    @pytest.fixture
    def client(self, mock_qdrant_client, mock_embedder):
        """Create test client with mocks."""
        # Patch the global instances
        with patch.object(server, "qdrant_client", mock_qdrant_client):
            with patch.object(server, "embedder", mock_embedder):
                # Create client after patching
                from server import app

                return TestClient(app)

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == config.MCP_SERVER_VERSION
        assert "qdrant_connected" in data

    def test_get_collection_exists(self, client, mock_qdrant_client):
        """Test getting existing collection info."""
        response = client.get("/collections/claude_vectors")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "claude_vectors"
        assert data["vector_size"] == 384
        assert data["vectors_count"] == 0

        mock_qdrant_client.get_collection.assert_called_once_with("claude_vectors")

    def test_get_collection_not_found(self, client, mock_qdrant_client):
        """Test getting non-existent collection."""
        mock_qdrant_client.get_collection.side_effect = Exception(
            "Collection not found"
        )

        response = client.get("/collections/non_existent")
        assert response.status_code == 404
        assert "Collection not found" in response.json()["detail"]

    def test_create_collection_success(self, client, mock_qdrant_client):
        """Test creating a new collection."""
        request_data = {
            "name": "test_collection",
            "vector_size": 512,
            "distance": "cosine",
        }

        response = client.post("/collections", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["collection"] == "test_collection"

        mock_qdrant_client.create_collection.assert_called_once()

    def test_create_collection_already_exists(self, client, mock_qdrant_client):
        """Test creating collection that already exists."""
        # Mock collection already exists
        mock_qdrant_client.create_collection.side_effect = Exception(
            "Collection already exists"
        )

        request_data = {"name": "existing_collection"}

        response = client.post("/collections", json=request_data)
        assert response.status_code == 400
        assert "Failed to create collection" in response.json()["detail"]

    def test_upsert_vectors_with_content(
        self, client, mock_qdrant_client, mock_embedder
    ):
        """Test upserting vectors with content."""
        request_data = {
            "collection": "claude_vectors",
            "points": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "content": "Test content",
                    "payload": {"role": "user"},
                }
            ],
        }

        response = client.post("/vectors/upsert", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["upserted"] == 1
        assert len(data["ids"]) == 1

        # Verify embedding was generated
        mock_embedder.encode.assert_called_once_with("Test content")

        # Verify upsert was called
        mock_qdrant_client.upsert.assert_called_once()

    def test_upsert_vectors_with_vector(
        self, client, mock_qdrant_client, sample_vector
    ):
        """Test upserting vectors with pre-computed vector."""
        request_data = {
            "collection": "claude_vectors",
            "points": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "vector": sample_vector,
                    "payload": {"role": "user"},
                }
            ],
        }

        response = client.post("/vectors/upsert", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["upserted"] == 1

    def test_upsert_vectors_invalid_id(self, client):
        """Test upserting with invalid ID format."""
        request_data = {
            "collection": "claude_vectors",
            "points": [{"id": "invalid-id-format", "content": "Test content"}],
        }

        response = client.post("/vectors/upsert", json=request_data)
        assert response.status_code == 400
        assert "Invalid UUID format" in response.json()["detail"]

    def test_upsert_vectors_no_content_or_vector(self, client):
        """Test upserting without content or vector."""
        request_data = {
            "collection": "claude_vectors",
            "points": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "payload": {"role": "user"},
                }
            ],
        }

        response = client.post("/vectors/upsert", json=request_data)
        assert response.status_code == 400
        assert "Either 'content' or 'vector' is required" in response.json()["detail"]

    def test_search_vectors_success(self, client, mock_qdrant_client, mock_embedder):
        """Test successful vector search."""
        request_data = {
            "query": "test search query",
            "collection": "claude_vectors",
            "limit": 5,
            "score_threshold": 0.5,
        }

        response = client.post("/vectors/search", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test search query"
        assert len(data["hits"]) == 2
        assert data["total"] == 2

        # Verify first hit
        assert data["hits"][0]["id"] == "test-id-1"
        assert data["hits"][0]["score"] == 0.95
        assert data["hits"][0]["payload"]["content"] == "Test content 1"

        # Verify embedding was generated
        mock_embedder.encode.assert_called_once_with("test search query")

        # Verify search was called
        mock_qdrant_client.search.assert_called_once()

    def test_search_vectors_no_results(self, client, mock_qdrant_client, mock_embedder):
        """Test search with no results."""
        mock_qdrant_client.search.return_value = []

        request_data = {"query": "no results query", "collection": "claude_vectors"}

        response = client.post("/vectors/search", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["hits"]) == 0

    def test_search_vectors_error(self, client, mock_qdrant_client, mock_embedder):
        """Test search with error."""
        mock_qdrant_client.search.side_effect = Exception("Search failed")

        request_data = {"query": "error query", "collection": "claude_vectors"}

        response = client.post("/vectors/search", json=request_data)
        assert response.status_code == 500
        assert "Failed to search vectors" in response.json()["detail"]
