import asyncio
import json
import logging
import os
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request, Response
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

import config
from mcp_handler import MCPHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app for MCP
app = FastAPI(title="Qdrant MCP HTTP Server")

# Global MCP handler instance
mcp_handler = None


@app.on_event("startup")
async def startup_event():
    """Initialize MCP handler on startup."""
    global mcp_handler

    # Initialize Qdrant client
    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )

    # Initialize embedder
    logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
    embedder = SentenceTransformer(config.EMBEDDING_MODEL)

    # Initialize MCP handler
    mcp_handler = MCPHandler(qdrant_client, embedder)
    logger.info("MCP HTTP server initialized")


@app.post("/")
async def handle_mcp_request(request: Request) -> Response:
    """Handle MCP JSON-RPC requests."""
    try:
        # Get request body
        body = await request.body()

        # Parse JSON-RPC request
        try:
            rpc_request = json.loads(body)
        except json.JSONDecodeError:
            return Response(
                content=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                        "id": None,
                    }
                ),
                media_type="application/json",
            )

        # Handle the request based on method
        method = rpc_request.get("method")
        params = rpc_request.get("params", {})
        request_id = rpc_request.get("id")

        # Route to appropriate handler
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": config.MCP_SERVER_NAME,
                        "version": config.MCP_SERVER_VERSION,
                    },
                },
                "id": request_id,
            }
        elif method == "tools/list":
            # Get tools list
            tools = [
                {
                    "name": "qdrant-store",
                    "description": "Store information in Qdrant vector database with semantic search capability",
                    "inputSchema": {
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
                },
                {
                    "name": "qdrant-find",
                    "description": "Find relevant information using semantic search in Qdrant",
                    "inputSchema": {
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
                },
                {
                    "name": "qdrant-list-collections",
                    "description": "List all collections in Qdrant database",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "qdrant-create-collection",
                    "description": "Create a new collection in Qdrant",
                    "inputSchema": {
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
                },
            ]

            response = {"jsonrpc": "2.0", "result": {"tools": tools}, "id": request_id}
        elif method == "tools/call":
            # Call tool through MCP handler
            tool_name = params.get("name")
            tool_arguments = params.get("arguments", {})

            # Call the appropriate handler method
            if tool_name == "qdrant-store":
                results = await mcp_handler._handle_store(tool_arguments)
            elif tool_name == "qdrant-find":
                results = await mcp_handler._handle_find(tool_arguments)
            elif tool_name == "qdrant-list-collections":
                results = await mcp_handler._handle_list_collections()
            elif tool_name == "qdrant-create-collection":
                results = await mcp_handler._handle_create_collection(tool_arguments)
            else:
                from mcp.types import TextContent

                results = [TextContent(text=f"Unknown tool: {tool_name}")]

            response = {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {"type": "text", "text": result.text} for result in results
                    ]
                },
                "id": request_id,
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": request_id,
            }

        return Response(content=json.dumps(response), media_type="application/json")

    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return Response(
            content=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                    "id": request_id if "request_id" in locals() else None,
                }
            ),
            media_type="application/json",
        )


if __name__ == "__main__":
    # Run MCP HTTP server on port 8001
    mcp_port = int(os.getenv("MCP_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=mcp_port, log_level="info")
