import json
import logging
import sys
import uuid
from typing import Any

from mcp.server import Server
from mcp.types import (
    TextContent,
    Tool,
)
from omegaconf import DictConfig
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class MCPHandler:
    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedder: SentenceTransformer,
        config: DictConfig | None = None,
    ):
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        self.config = config
        self.server = Server(config.mcp.server_name if config else "qdrant-mcp")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP protocol handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available MCP tools."""
            return [
                Tool(
                    name="qdrant-store",
                    description="Store information in Qdrant vector database with semantic search capability",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The content to store",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata to store with the content",
                                "additionalProperties": True,
                            },
                            "collection": {
                                "type": "string",
                                "description": f"Collection name (default: {self.config.vector.collection_name if self.config else 'claude_vectors'})",
                                "default": (
                                    self.config.vector.collection_name
                                    if self.config
                                    else "claude_vectors"
                                ),
                            },
                        },
                        "required": ["content"],
                    },
                ),
                Tool(
                    name="qdrant-find",
                    description="Find relevant information using semantic search in Qdrant",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query",
                            },
                            "limit": {
                                "type": "integer",
                                "description": f"Number of results to return (default: {self.config.vector.top_k if self.config else 10})",
                                "default": (
                                    self.config.vector.top_k if self.config else 10
                                ),
                            },
                            "score_threshold": {
                                "type": "number",
                                "description": f"Minimum similarity score (default: {self.config.vector.min_score if self.config else 0.22})",
                                "default": (
                                    self.config.vector.min_score
                                    if self.config
                                    else 0.22
                                ),
                            },
                            "collection": {
                                "type": "string",
                                "description": f"Collection name (default: {self.config.vector.collection_name if self.config else 'claude_vectors'})",
                                "default": (
                                    self.config.vector.collection_name
                                    if self.config
                                    else "claude_vectors"
                                ),
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="qdrant-list-collections",
                    description="List all collections in Qdrant database",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="qdrant-create-collection",
                    description="Create a new collection in Qdrant",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Collection name",
                            },
                            "vector_size": {
                                "type": "integer",
                                "description": f"Vector dimension size (default: {self.config.vector.vector_size if self.config else 384})",
                                "default": (
                                    self.config.vector.vector_size
                                    if self.config
                                    else 384
                                ),
                            },
                        },
                        "required": ["name"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "qdrant-store":
                    return await self._handle_store(arguments)
                elif name == "qdrant-find":
                    return await self._handle_find(arguments)
                elif name == "qdrant-list-collections":
                    return await self._handle_list_collections()
                elif name == "qdrant-create-collection":
                    return await self._handle_create_collection(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Tool {name} failed: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_store(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle qdrant-store tool."""
        content = arguments.get("content", "")
        metadata = arguments.get("metadata", {})
        collection = arguments.get(
            "collection",
            self.config.vector.collection_name if self.config else "claude_vectors",
        )

        if not content:
            return [TextContent(type="text", text="Error: No content provided")]

        try:
            # Generate embedding
            vector = self.embedder.encode(content).tolist()

            # Create point
            point_id = str(uuid.uuid4())
            payload = {"content": content, **metadata}

            # Ensure collection exists
            try:
                self.qdrant_client.get_collection(collection)
            except Exception:
                # Create collection if it doesn't exist
                self.qdrant_client.create_collection(
                    collection_name=collection,
                    vectors_config=models.VectorParams(
                        size=self.config.vector.vector_size if self.config else 384,
                        distance=models.Distance.COSINE,
                    ),
                )

            # Upsert point
            self.qdrant_client.upsert(
                collection_name=collection,
                points=[
                    models.PointStruct(id=point_id, vector=vector, payload=payload)
                ],
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully stored content with ID: {point_id} in collection: {collection}",
                )
            ]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to store content: {str(e)}")]

    async def _handle_find(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle qdrant-find tool."""
        query = arguments.get("query", "")
        limit = arguments.get("limit", self.config.vector.top_k if self.config else 10)
        score_threshold = arguments.get(
            "score_threshold", self.config.vector.min_score if self.config else 0.22
        )
        collection = arguments.get(
            "collection",
            self.config.vector.collection_name if self.config else "claude_vectors",
        )

        if not query:
            return [TextContent(type="text", text="Error: No query provided")]

        try:
            # Generate query embedding
            query_vector = self.embedder.encode(query).tolist()

            # Search
            results = self.qdrant_client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            if not results:
                return [TextContent(type="text", text="No relevant results found")]

            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                payload = result.payload or {}
                content = payload.get("content", "")
                score = result.score
                metadata = {k: v for k, v in payload.items() if k != "content"}

                result_text = f"Result {i} (score: {score:.3f}):\n{content}"
                if metadata:
                    result_text += f"\nMetadata: {json.dumps(metadata, indent=2)}"
                formatted_results.append(result_text)

            return [
                TextContent(
                    type="text",
                    text=f"Found {len(results)} results:\n\n"
                    + "\n\n---\n\n".join(formatted_results),
                )
            ]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to search: {str(e)}")]

    async def _handle_list_collections(self) -> list[TextContent]:
        """Handle qdrant-list-collections tool."""
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if not collection_names:
                return [TextContent(type="text", text="No collections found")]

            return [
                TextContent(
                    type="text",
                    text="Collections:\n"
                    + "\n".join(f"- {c}" for c in collection_names),
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Failed to list collections: {str(e)}")
            ]

    async def _handle_create_collection(
        self, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle qdrant-create-collection tool."""
        name = arguments.get("name", "")
        vector_size = arguments.get(
            "vector_size", self.config.vector.vector_size if self.config else 384
        )

        if not name:
            return [TextContent(type="text", text="Error: No collection name provided")]

        try:
            self.qdrant_client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
            )
            return [
                TextContent(
                    type="text",
                    text=f"Successfully created collection '{name}' with vector size {vector_size}",
                )
            ]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Failed to create collection: {str(e)}")
            ]

    async def run_stdio(self) -> None:
        """Run MCP server in stdio mode."""
        logger.info("Starting MCP server in stdio mode...")
        await self.server.run(
            read_stream=sys.stdin.buffer,  # type: ignore
            write_stream=sys.stdout.buffer,  # type: ignore
            initialization_options=None,  # type: ignore
        )

    async def handle_request(self, request: dict) -> dict:
        """Handle MCP request (for HTTP mode)."""
        # This would need to be implemented based on MCP HTTP protocol
        # For now, we focus on stdio mode
        raise NotImplementedError("HTTP mode not yet implemented")
