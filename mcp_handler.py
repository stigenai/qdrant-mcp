import asyncio
import json
import logging
import sys
import uuid
from typing import Any, Dict, List, Optional

import mcp.server as mcp
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ListToolsResult,
)
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

import config

logger = logging.getLogger(__name__)


class MCPHandler:
    def __init__(self, qdrant_client: QdrantClient, embedder: SentenceTransformer):
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        self.server = Server(config.MCP_SERVER_NAME)
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP protocol handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
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
                                "description": f"Collection name (default: {config.COLLECTION_NAME})",
                                "default": config.COLLECTION_NAME,
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
                                "description": f"Number of results to return (default: {config.TOP_K})",
                                "default": config.TOP_K,
                            },
                            "score_threshold": {
                                "type": "number",
                                "description": f"Minimum similarity score (default: {config.MIN_SCORE})",
                                "default": config.MIN_SCORE,
                            },
                            "collection": {
                                "type": "string",
                                "description": f"Collection name (default: {config.COLLECTION_NAME})",
                                "default": config.COLLECTION_NAME,
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
                                "description": f"Vector dimension size (default: {config.VECTOR_SIZE})",
                                "default": config.VECTOR_SIZE,
                            },
                        },
                        "required": ["name"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
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
                    return [TextContent(text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Tool {name} failed: {e}")
                return [TextContent(text=f"Error: {str(e)}")]

    async def _handle_store(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle qdrant-store tool."""
        content = arguments.get("content", "")
        metadata = arguments.get("metadata", {})
        collection = arguments.get("collection", config.COLLECTION_NAME)

        if not content:
            return [TextContent(text="Error: No content provided")]

        try:
            # Generate embedding
            vector = self.embedder.encode(content).tolist()

            # Create point
            point_id = str(uuid.uuid4())
            payload = {"content": content, **metadata}

            # Ensure collection exists
            try:
                self.qdrant_client.get_collection(collection)
            except:
                # Create collection if it doesn't exist
                self.qdrant_client.create_collection(
                    collection_name=collection,
                    vectors_config=models.VectorParams(
                        size=config.VECTOR_SIZE, distance=models.Distance.COSINE
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
                    text=f"Successfully stored content with ID: {point_id} in collection: {collection}"
                )
            ]
        except Exception as e:
            return [TextContent(text=f"Failed to store content: {str(e)}")]

    async def _handle_find(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle qdrant-find tool."""
        query = arguments.get("query", "")
        limit = arguments.get("limit", config.TOP_K)
        score_threshold = arguments.get("score_threshold", config.MIN_SCORE)
        collection = arguments.get("collection", config.COLLECTION_NAME)

        if not query:
            return [TextContent(text="Error: No query provided")]

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
                return [TextContent(text="No relevant results found")]

            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                content = result.payload.get("content", "")
                score = result.score
                metadata = {k: v for k, v in result.payload.items() if k != "content"}

                result_text = f"Result {i} (score: {score:.3f}):\n{content}"
                if metadata:
                    result_text += f"\nMetadata: {json.dumps(metadata, indent=2)}"
                formatted_results.append(result_text)

            return [
                TextContent(
                    text=f"Found {len(results)} results:\n\n"
                    + "\n\n---\n\n".join(formatted_results)
                )
            ]
        except Exception as e:
            return [TextContent(text=f"Failed to search: {str(e)}")]

    async def _handle_list_collections(self) -> List[TextContent]:
        """Handle qdrant-list-collections tool."""
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if not collection_names:
                return [TextContent(text="No collections found")]

            return [
                TextContent(
                    text=f"Collections:\n"
                    + "\n".join(f"- {c}" for c in collection_names)
                )
            ]
        except Exception as e:
            return [TextContent(text=f"Failed to list collections: {str(e)}")]

    async def _handle_create_collection(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle qdrant-create-collection tool."""
        name = arguments.get("name", "")
        vector_size = arguments.get("vector_size", config.VECTOR_SIZE)

        if not name:
            return [TextContent(text="Error: No collection name provided")]

        try:
            self.qdrant_client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
            )
            return [
                TextContent(
                    text=f"Successfully created collection '{name}' with vector size {vector_size}"
                )
            ]
        except Exception as e:
            return [TextContent(text=f"Failed to create collection: {str(e)}")]

    async def run_stdio(self):
        """Run MCP server in stdio mode."""
        logger.info("Starting MCP server in stdio mode...")
        await self.server.run(
            read_stream=sys.stdin.buffer,
            write_stream=sys.stdout.buffer,
            initialization_options=None,
        )

    async def handle_request(self, request: dict) -> dict:
        """Handle MCP request (for HTTP mode)."""
        # This would need to be implemented based on MCP HTTP protocol
        # For now, we focus on stdio mode
        raise NotImplementedError("HTTP mode not yet implemented")
