import asyncio
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import hydra
import tiktoken
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from omegaconf import DictConfig
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from mcp_handler import MCPHandler

# Configure logging
logger = logging.getLogger(__name__)

# Global instances
qdrant_client: QdrantClient | None = None
embedder: SentenceTransformer | None = None
tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
mcp_handler: MCPHandler | None = None
cfg: DictConfig | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global embedder, mcp_handler
    # Startup
    logger.info("Starting up API server...")
    # Wait for Qdrant to be ready
    if cfg is None:
        raise RuntimeError("Configuration not loaded")
    if not await wait_for_qdrant():
        logger.error("Failed to connect to Qdrant, exiting...")
        sys.exit(1)
    # Initialize sentence transformer
    if cfg is None:
        raise RuntimeError("Configuration not loaded")
    logger.info(f"Loading embedding model: {cfg.vector.embedding_model}")
    embedder = SentenceTransformer(cfg.vector.embedding_model)
    # Initialize MCP handler
    if qdrant_client is None or embedder is None:
        raise RuntimeError("Dependencies not initialized")
    mcp_handler = MCPHandler(qdrant_client, embedder, cfg)
    # Ensure default collection exists
    await ensure_default_collection()
    logger.info("API server startup complete")

    yield

    # Shutdown
    logger.info("Shutting down API server...")


# Initialize FastAPI app
app = FastAPI(title="Qdrant MCP Server", lifespan=lifespan)


# Pydantic models
class VectorPoint(BaseModel):
    id: str
    vector: list[float] | None = None
    content: str | None = None
    payload: dict[str, Any] = {}


class VectorSearchRequest(BaseModel):
    query: str
    collection: str | None = None
    limit: int | None = None
    score_threshold: float | None = None

    def __init__(self, **data):
        super().__init__(**data)
        if cfg is not None:
            if self.collection is None:
                self.collection = cfg.vector.collection_name
            if self.limit is None:
                self.limit = cfg.vector.top_k
            if self.score_threshold is None:
                self.score_threshold = cfg.vector.min_score


class VectorUpsertRequest(BaseModel):
    collection: str | None = None
    points: list[VectorPoint]

    def __init__(self, **data):
        super().__init__(**data)
        if cfg is not None and self.collection is None:
            self.collection = cfg.vector.collection_name


class CollectionInfo(BaseModel):
    name: str
    vector_size: int | None = None
    distance: str = "cosine"

    def __init__(self, **data):
        super().__init__(**data)
        if cfg is not None and self.vector_size is None:
            self.vector_size = cfg.vector.vector_size


# Helper functions
def count_tokens(text: str) -> int:
    """Count tokens in text."""
    return len(tokenizer.encode(text))


async def wait_for_qdrant(max_retries: int = 30, delay: int = 1):
    """Wait for Qdrant to be ready."""
    global qdrant_client

    if cfg is None:
        raise RuntimeError("Configuration not loaded")

    for i in range(max_retries):
        try:
            qdrant_client = QdrantClient(host=cfg.qdrant.host, port=cfg.qdrant.port)
            # Try to list collections to verify connection
            qdrant_client.get_collections()
            logger.info("Successfully connected to Qdrant")
            return True
        except Exception as e:
            if i < max_retries - 1:
                logger.info(f"Waiting for Qdrant to start... ({i+1}/{max_retries})")
                time.sleep(delay)
            else:
                logger.error(
                    f"Failed to connect to Qdrant after {max_retries} attempts: {e}"
                )
                return False
    return False


async def ensure_default_collection():
    """Ensure the default collection exists."""
    try:
        qdrant_client.get_collection(cfg.vector.collection_name)
        logger.info(f"Collection '{cfg.vector.collection_name}' already exists")
    except Exception:
        logger.info(f"Creating collection '{cfg.vector.collection_name}'")
        distance_map = {
            "cosine": models.Distance.COSINE,
            "euclidean": models.Distance.EUCLID,
            "dot": models.Distance.DOT,
        }
        if qdrant_client is None:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        qdrant_client.create_collection(
            collection_name=cfg.vector.collection_name,
            vectors_config=models.VectorParams(
                size=cfg.vector.vector_size,
                distance=distance_map.get(
                    cfg.vector.distance_metric, models.Distance.COSINE
                ),
            ),
        )


# REST API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": cfg.mcp.server_version,
        "qdrant_connected": qdrant_client is not None,
    }


@app.get("/collections/{collection_name}")
async def get_collection(collection_name: str):
    """Get collection information."""
    try:
        if qdrant_client is None:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        collection = qdrant_client.get_collection(collection_name)
        return {
            "name": collection_name,
            "vectors_count": collection.vectors_count,
            "points_count": collection.points_count,
            "config": collection.config.dict(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Collection not found: {str(e)}"
        ) from e


@app.post("/collections")
async def create_collection(collection: CollectionInfo):
    """Create a new collection."""
    try:
        distance_map = {
            "cosine": models.Distance.COSINE,
            "euclidean": models.Distance.EUCLID,
            "dot": models.Distance.DOT,
        }

        if qdrant_client is None:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        qdrant_client.create_collection(
            collection_name=collection.name,
            vectors_config=models.VectorParams(
                size=collection.vector_size,
                distance=distance_map.get(
                    collection.distance.lower(), models.Distance.COSINE
                ),
            ),
        )
        return {"status": "created", "collection": collection.name}
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to create collection: {str(e)}"
        ) from e


@app.post("/vectors/upsert")
async def upsert_vectors(request: VectorUpsertRequest):
    """Upsert vectors to collection."""
    try:
        points = []
        for point in request.points:
            # Generate embedding if content is provided but vector is not
            if point.content and not point.vector:
                if embedder is None:
                    raise HTTPException(
                        status_code=500, detail="Embedder not initialized"
                    )
                point.vector = embedder.encode(point.content).tolist()

            # Create Qdrant point
            qdrant_point = models.PointStruct(
                id=point.id or str(uuid.uuid4()),
                vector=point.vector,
                payload=point.payload,
            )

            # Add content to payload if provided
            if point.content:
                qdrant_point.payload["content"] = point.content
                qdrant_point.payload["tokens"] = count_tokens(point.content)

            points.append(qdrant_point)

        # Upsert to Qdrant
        if qdrant_client is None:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        qdrant_client.upsert(collection_name=request.collection, points=points)

        return {
            "status": "success",
            "upserted": len(points),
            "ids": [p.id for p in points],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upsert vectors: {str(e)}"
        ) from e


@app.post("/vectors/search")
async def search_vectors(request: VectorSearchRequest):
    """Search for similar vectors."""
    try:
        # Generate query embedding
        query_vector = embedder.encode(request.query).tolist()

        # Search in Qdrant
        if qdrant_client is None:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        if embedder is None:
            raise HTTPException(status_code=500, detail="Embedder not initialized")
        results = qdrant_client.search(
            collection_name=request.collection,
            query_vector=query_vector,
            limit=request.limit,
            score_threshold=request.score_threshold,
        )

        # Format results
        hits = []
        for result in results:
            hit = {"id": result.id, "score": result.score, "payload": result.payload}
            hits.append(hit)

        return {"query": request.query, "hits": hits, "total": len(hits)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to search vectors: {str(e)}"
        ) from e


# MCP endpoint (when running as MCP server)
@app.post("/mcp")
async def handle_mcp_request(request: dict):
    """Handle MCP protocol requests."""
    if not mcp_handler:
        raise HTTPException(status_code=503, detail="MCP handler not initialized")

    try:
        response = await mcp_handler.handle_request(request)
        return response
    except Exception as e:
        logger.error(f"MCP request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def run_mcp_mode():
    """Run in MCP mode."""
    global qdrant_client, embedder, mcp_handler

    # Initialize Qdrant client
    qdrant_client = QdrantClient(host=cfg.qdrant.host, port=cfg.qdrant.port)

    # Initialize embedder
    if cfg is None:
        raise RuntimeError("Configuration not loaded")
    embedder = SentenceTransformer(cfg.vector.embedding_model)

    # Initialize MCP handler
    if qdrant_client is None or embedder is None:
        raise RuntimeError("Dependencies not initialized")
    mcp_handler = MCPHandler(qdrant_client, embedder, cfg)

    # Run MCP server
    await mcp_handler.run_stdio()


def setup_app(config: DictConfig):
    """Setup FastAPI app with configuration."""
    global cfg
    cfg = config

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.logging.log_level.upper()),
        format=config.logging.format,
    )

    return app


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(config: DictConfig) -> None:
    """Main entry point."""
    global cfg
    cfg = config

    # Check if running as MCP server (stdio mode)
    if config.mcp.get("stdio_mode", False):
        # Run in MCP mode
        asyncio.run(run_mcp_mode())
    else:
        # Setup app
        setup_app(config)

        # Run as REST API server
        uvicorn.run(
            app,
            host=config.api.host,
            port=config.api.port,
            log_level=config.api.log_level,
        )


if __name__ == "__main__":
    main()
