#!/bin/bash

# Example usage of the Hydra-based configuration system

echo "=== Qdrant MCP Server Configuration Examples ==="
echo

echo "1. Running with default configuration:"
echo "   python server.py"
echo

echo "2. Running with development configuration:"
echo "   python server.py --config-name=config_development"
echo

echo "3. Running with production configuration:"
echo "   python server.py --config-name=config_production"
echo

echo "4. Overriding specific values:"
echo "   python server.py qdrant.port=6334 api.port=8080"
echo

echo "5. Running MCP in stdio mode (for Claude):"
echo "   python server.py mcp.stdio_mode=true"
echo

echo "6. Running with custom database paths:"
echo "   python server.py qdrant.data_path=/my/data qdrant.snapshots_path=/my/snapshots"
echo

echo "7. Running with security enabled:"
echo "   python server.py security.require_api_key=true security.api_key=mysecret"
echo

echo "8. Running MCP HTTP server separately:"
echo "   python mcp_server.py mcp.port=9001"
echo

echo "9. Combining environment variables and CLI args:"
echo "   export QDRANT_HOST=192.168.1.100"
echo "   export API_KEY=mysecretkey"
echo "   python server.py --config-name=config_production api.port=8888"
echo

echo "10. Debug mode with verbose logging:"
echo "    python server.py logging.log_level=DEBUG api.log_level=debug"