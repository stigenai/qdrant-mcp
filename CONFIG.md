# Configuration Guide

This project uses Hydra for configuration management, supporting configuration through config files, environment variables, and command-line arguments.

## Configuration Structure

The configuration is organized into modular components:

```
conf/
├── config.yaml              # Main configuration file
├── config_development.yaml  # Development environment config
├── config_production.yaml   # Production environment config
├── qdrant/
│   └── default.yaml        # Qdrant database settings
├── vector/
│   └── default.yaml        # Vector database settings
├── api/
│   └── default.yaml        # REST API settings
├── mcp/
│   └── default.yaml        # MCP server settings
├── logging/
│   └── default.yaml        # Logging settings
└── security/
    └── default.yaml        # Security settings
```

## Usage

### Default Configuration

Run with default configuration:
```bash
python server.py
```

### Using Different Config Files

Use development configuration:
```bash
python server.py --config-name=config_development
```

Use production configuration:
```bash
python server.py --config-name=config_production
```

### Command Line Arguments

Override any configuration value from the command line:

```bash
# Change Qdrant port
python server.py qdrant.port=6334

# Change API host and port
python server.py api.host=127.0.0.1 api.port=8080

# Change collection name
python server.py vector.collection_name=my_vectors

# Enable debug logging
python server.py logging.log_level=DEBUG

# Run in MCP stdio mode
python server.py mcp.stdio_mode=true
```

### Environment Variables

All configuration values can be set via environment variables:

```bash
# Qdrant settings
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export QDRANT_DATA_PATH=/var/lib/qdrant

# Vector settings
export COLLECTION_NAME=my_vectors
export EMBEDDING_MODEL=all-MiniLM-L6-v2
export TOP_K=20

# API settings
export API_HOST=0.0.0.0
export API_PORT=8000
export CORS_ORIGINS='["https://example.com"]'

# Security settings
export REQUIRE_API_KEY=true
export API_KEY=your-secret-key

# Run the server
python server.py
```

## Configuration Options

### Qdrant Configuration
- `host`: Qdrant server host (default: localhost)
- `port`: Qdrant server port (default: 6333)
- `grpc_port`: Qdrant gRPC port (default: 6334)
- `data_path`: Path for Qdrant data storage (default: /qdrant/storage)
- `snapshots_path`: Path for Qdrant snapshots (default: /qdrant/snapshots)
- `max_payload_size_mb`: Maximum payload size in MB (default: 1)
- `telemetry_disabled`: Disable telemetry (default: true)

### Vector Configuration
- `collection_name`: Default collection name (default: claude_vectors)
- `embedding_model`: Sentence transformer model (default: all-MiniLM-L6-v2)
- `vector_size`: Vector dimension size (default: 384)
- `distance_metric`: Distance metric (default: cosine)
- `max_tokens`: Maximum tokens for embedding (default: 512)
- `top_k`: Number of results to return (default: 10)
- `min_score`: Minimum similarity score (default: 0.22)
- `on_disk_payload`: Store payload on disk (default: false)
- `indexed_only`: Use indexed vectors only (default: true)

### API Configuration
- `host`: API server host (default: 0.0.0.0)
- `port`: API server port (default: 8000)
- `workers`: Number of workers (default: 1)
- `reload`: Auto-reload on code changes (default: false)
- `log_level`: Uvicorn log level (default: info)
- `cors_origins`: CORS allowed origins (default: ["*"])
- `max_request_size_mb`: Maximum request size in MB (default: 10)

### MCP Configuration
- `server_name`: MCP server name (default: qdrant-mcp)
- `server_version`: MCP server version (default: 1.0.0)
- `port`: MCP HTTP server port (default: 8001)
- `protocol_version`: MCP protocol version (default: 2024-11-05)
- `stdio_mode`: Run in stdio mode for Claude (default: false)

### Logging Configuration
- `log_path`: Path for log files (default: /var/log/supervisor)
- `log_level`: Logging level (default: INFO)
- `max_bytes`: Maximum log file size (default: 10485760)
- `backup_count`: Number of backup log files (default: 3)
- `format`: Log message format

### Security Configuration
- `require_api_key`: Require API key authentication (default: false)
- `api_key`: API key for authentication
- `enable_ssl`: Enable SSL/TLS (default: false)
- `ssl_certfile`: Path to SSL certificate file
- `ssl_keyfile`: Path to SSL key file
- `ssl_ca_certs`: Path to CA certificates
- `ssl_cert_reqs`: SSL certificate requirements (default: CERT_NONE)

## Examples

### Running with custom database path
```bash
python server.py qdrant.data_path=/my/custom/path vector.collection_name=my_collection
```

### Running MCP server with custom port
```bash
python mcp_server.py mcp.port=9001
```

### Production deployment with security
```bash
python server.py \
  --config-name=config_production \
  security.api_key=my-secret-key \
  security.ssl_certfile=/path/to/cert.pem \
  security.ssl_keyfile=/path/to/key.pem
```

### Development with debug logging
```bash
python server.py \
  --config-name=config_development \
  api.reload=true \
  logging.log_level=DEBUG
```