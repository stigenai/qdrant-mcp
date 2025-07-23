"""Shared pytest fixtures and configuration."""

import os
import sys
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_qdrant_client():
    """Mock QdrantClient for testing."""
    client = Mock(spec=QdrantClient)

    # Mock methods
    client.get_collections = Mock(
        return_value=models.CollectionsResponse(
            collections=[models.CollectionDescription(name="claude_vectors")]
        )
    )

    client.get_collection = Mock(
        return_value=models.CollectionInfo(
            status=models.CollectionStatus.GREEN,
            optimizer_status=models.OptimizersStatusOneOf(ok=True),
            vectors_count=0,
            indexed_vectors_count=0,
            points_count=0,
            segments_count=1,
            config=models.CollectionConfig(
                params=models.CollectionParams(
                    vectors=models.VectorParams(
                        size=384, distance=models.Distance.COSINE
                    )
                )
            ),
        )
    )

    client.create_collection = Mock(return_value=True)
    client.upsert = Mock(
        return_value=models.UpdateResult(
            operation_id=0, status=models.UpdateStatus.COMPLETED
        )
    )

    # Mock search to return sample results
    client.search = Mock(
        return_value=[
            models.ScoredPoint(
                id="test-id-1",
                version=0,
                score=0.95,
                payload={
                    "content": "Test content 1",
                    "role": "user",
                    "timestamp": "2025-01-01T00:00:00Z",
                },
            ),
            models.ScoredPoint(
                id="test-id-2",
                version=0,
                score=0.85,
                payload={
                    "content": "Test content 2",
                    "role": "assistant",
                    "timestamp": "2025-01-01T00:01:00Z",
                },
            ),
        ]
    )

    return client


@pytest.fixture
def mock_embedder():
    """Mock SentenceTransformer for testing."""
    embedder = Mock(spec=SentenceTransformer)

    # Return consistent 384-dimensional vectors
    def mock_encode(text):
        if isinstance(text, str):
            # Generate a deterministic vector based on text hash
            np.random.seed(hash(text) % 2**32)
            return np.random.randn(384).astype(np.float32)
        else:
            # Handle list of texts
            vectors = []
            for t in text:
                np.random.seed(hash(t) % 2**32)
                vectors.append(np.random.randn(384).astype(np.float32))
            return np.array(vectors)

    embedder.encode = Mock(side_effect=mock_encode)
    return embedder


@pytest.fixture
def sample_vector():
    """Sample 384-dimensional vector."""
    np.random.seed(42)
    return np.random.randn(384).astype(np.float32).tolist()


@pytest.fixture
def sample_points():
    """Sample data points for testing."""
    return [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "This is a test document about machine learning and AI",
            "payload": {"role": "user", "timestamp": "2025-01-01T00:00:00Z"},
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "content": "Python is a great programming language for data science",
            "payload": {"role": "assistant", "timestamp": "2025-01-01T00:01:00Z"},
        },
    ]


@pytest.fixture
async def async_mock_qdrant_client(mock_qdrant_client):
    """Async version of mock QdrantClient."""
    # Convert sync mocks to async where needed
    async_client = AsyncMock(spec=QdrantClient)

    # Copy attributes from sync mock
    for attr in dir(mock_qdrant_client):
        if not attr.startswith("_"):
            setattr(async_client, attr, getattr(mock_qdrant_client, attr))

    return async_client
