import json
import logging

import hydra
import uvicorn
from fastapi import FastAPI, Request, Response
from omegaconf import DictConfig
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from mcp_handler import MCPHandler

# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app for MCP
app = FastAPI(title="Qdrant MCP HTTP Server")

# Global instances
mcp_handler = None
cfg: DictConfig | None = None


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize MCP handler on startup."""
    global mcp_handler

    # Initialize Qdrant client
    if cfg is None:
        raise RuntimeError("Configuration not loaded")
    qdrant_client = QdrantClient(
        host=cfg.qdrant.host,
        port=cfg.qdrant.port,
    )

    # Initialize embedder
    logger.info(f"Loading embedding model: {cfg.vector.embedding_model}")
    embedder = SentenceTransformer(cfg.vector.embedding_model)

    # Initialize MCP handler
    mcp_handler = MCPHandler(qdrant_client, embedder, cfg)
    logger.info("MCP HTTP server initialized")


@app.post("/")
async def handle_mcp_request(request: Request) -> Response:
    """Handle MCP JSON-RPC requests."""
    if cfg is None:
        return Response(
            content=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": "Configuration not loaded"},
                    "id": None,
                }
            ),
            media_type="application/json",
        )
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
            if cfg is None:
                raise RuntimeError("Configuration not loaded")
            response = {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": cfg.mcp.protocol_version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": cfg.mcp.server_name,
                        "version": cfg.mcp.server_version,
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
                                "description": f"Collection name (default: {cfg.vector.collection_name})",
                                "default": cfg.vector.collection_name,
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
                                "description": f"Number of results to return (default: {cfg.vector.top_k})",
                                "default": cfg.vector.top_k,
                            },
                            "score_threshold": {
                                "type": "number",
                                "description": f"Minimum similarity score (default: {cfg.vector.min_score})",
                                "default": cfg.vector.min_score,
                            },
                            "collection": {
                                "type": "string",
                                "description": f"Collection name (default: {cfg.vector.collection_name})",
                                "default": cfg.vector.collection_name,
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
                                "description": f"Vector dimension size (default: {cfg.vector.vector_size})",
                                "default": cfg.vector.vector_size,
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
            if mcp_handler is None:
                return Response(
                    content=json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": "MCP handler not initialized",
                            },
                            "id": request_id,
                        }
                    ),
                    media_type="application/json",
                )

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

                results = [TextContent(type="text", text=f"Unknown tool: {tool_name}")]

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


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(config: DictConfig) -> None:
    """Main entry point."""
    global cfg
    cfg = config

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.logging.log_level.upper()),
        format=config.logging.format,
    )

    # Run MCP HTTP server
    uvicorn.run(
        app, host="0.0.0.0", port=config.mcp.port, log_level=config.api.log_level
    )


if __name__ == "__main__":
    main()
