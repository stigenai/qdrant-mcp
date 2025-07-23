import json
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, validator

# Default paths
DEFAULT_CONFIG_PATH = os.getenv("QDRANT_MCP_CONFIG", "/app/config/config.yaml")
DEFAULT_DATA_PATH = os.getenv("QDRANT_DATA_PATH", "/qdrant/storage")
DEFAULT_SNAPSHOTS_PATH = os.getenv("QDRANT_SNAPSHOTS_PATH", "/qdrant/snapshots")
DEFAULT_LOG_PATH = os.getenv("QDRANT_LOG_PATH", "/var/log/supervisor")


class QdrantConfig(BaseModel):
    """Qdrant database configuration."""

    host: str = Field(default="localhost", description="Qdrant server host")
    port: int = Field(default=6333, description="Qdrant server port")
    grpc_port: int = Field(default=6334, description="Qdrant gRPC port")
    data_path: str = Field(
        default=DEFAULT_DATA_PATH, description="Path for Qdrant data storage"
    )
    snapshots_path: str = Field(
        default=DEFAULT_SNAPSHOTS_PATH, description="Path for Qdrant snapshots"
    )
    max_payload_size_mb: int = Field(
        default=1, description="Maximum payload size in MB"
    )
    telemetry_disabled: bool = Field(default=True, description="Disable telemetry")

    @validator("data_path", "snapshots_path")
    def validate_paths(cls, v):
        path = Path(v)
        if not path.is_absolute():
            raise ValueError(f"Path must be absolute: {v}")
        return str(path)


class VectorConfig(BaseModel):
    """Vector database configuration."""

    collection_name: str = Field(
        default="claude_vectors", description="Default collection name"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence transformer model"
    )
    vector_size: int = Field(default=384, description="Vector dimension size")
    distance_metric: str = Field(
        default="cosine", description="Distance metric for similarity"
    )
    max_tokens: int = Field(
        default=512, description="Maximum tokens before vectorization"
    )
    top_k: int = Field(default=10, description="Number of results to return")
    min_score: float = Field(default=0.22, description="Minimum similarity score")
    on_disk_payload: bool = Field(default=False, description="Store payload on disk")
    indexed_only: bool = Field(default=True, description="Use indexed vectors only")


class APIConfig(BaseModel):
    """REST API configuration."""

    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, description="API server port")
    workers: int = Field(default=1, description="Number of worker processes")
    reload: bool = Field(default=False, description="Enable auto-reload")
    log_level: str = Field(default="info", description="Logging level")
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")
    max_request_size_mb: int = Field(
        default=10, description="Maximum request size in MB"
    )


class MCPConfig(BaseModel):
    """MCP server configuration."""

    server_name: str = Field(default="qdrant-mcp", description="MCP server name")
    server_version: str = Field(default="1.0.0", description="MCP server version")
    port: int = Field(default=8001, description="MCP HTTP server port")
    protocol_version: str = Field(
        default="2024-11-05", description="MCP protocol version"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    log_path: str = Field(
        default=DEFAULT_LOG_PATH, description="Base path for log files"
    )
    log_level: str = Field(default="INFO", description="Default log level")
    max_bytes: int = Field(default=10485760, description="Max log file size (10MB)")
    backup_count: int = Field(default=3, description="Number of log backups to keep")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )


class SecurityConfig(BaseModel):
    """Security configuration."""

    api_key: str | None = Field(
        default=None, description="Optional API key for authentication"
    )
    enable_tls: bool = Field(default=False, description="Enable TLS/HTTPS")
    tls_cert_path: str | None = Field(
        default=None, description="Path to TLS certificate"
    )
    tls_key_path: str | None = Field(
        default=None, description="Path to TLS private key"
    )
    allowed_ips: list[str] | None = Field(
        default=None, description="Whitelist of allowed IPs"
    )
    rate_limit_per_minute: int = Field(
        default=60, description="Rate limit per IP per minute"
    )


class Config(BaseModel):
    """Main configuration class."""

    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    vector: VectorConfig = Field(default_factory=VectorConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    @classmethod
    def load_from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML or JSON file."""
        path = Path(config_path)
        if not path.exists():
            print(f"Config file not found at {config_path}, using defaults")
            return cls()

        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            elif path.suffix == ".json":
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {path.suffix}")

        return cls.parse_obj(data or {})

    @classmethod
    def load_from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            qdrant=QdrantConfig(
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", "6333")),
                grpc_port=int(os.getenv("QDRANT_GRPC_PORT", "6334")),
                data_path=os.getenv("QDRANT_DATA_PATH", DEFAULT_DATA_PATH),
                snapshots_path=os.getenv(
                    "QDRANT_SNAPSHOTS_PATH", DEFAULT_SNAPSHOTS_PATH
                ),
                telemetry_disabled=os.getenv(
                    "QDRANT_TELEMETRY_DISABLED", "true"
                ).lower()
                == "true",
            ),
            vector=VectorConfig(
                collection_name=os.getenv("COLLECTION_NAME", "claude_vectors"),
                embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
                vector_size=int(os.getenv("VECTOR_SIZE", "384")),
                max_tokens=int(os.getenv("MAX_TOKENS", "512")),
                top_k=int(os.getenv("TOP_K", "10")),
                min_score=float(os.getenv("MIN_SCORE", "0.22")),
            ),
            api=APIConfig(
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", "8000")),
                log_level=os.getenv("API_LOG_LEVEL", "info"),
            ),
            mcp=MCPConfig(
                port=int(os.getenv("MCP_PORT", "8001")),
                server_name=os.getenv("MCP_SERVER_NAME", "qdrant-mcp"),
                server_version=os.getenv("MCP_SERVER_VERSION", "1.0.0"),
            ),
            logging=LoggingConfig(
                log_path=os.getenv("LOG_PATH", DEFAULT_LOG_PATH),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
            ),
            security=SecurityConfig(
                api_key=os.getenv("API_KEY", None),
                enable_tls=os.getenv("ENABLE_TLS", "false").lower() == "true",
            ),
        )

    def save_to_file(self, config_path: str, format: str = "yaml"):
        """Save configuration to file."""
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = self.dict(exclude_unset=True)

        with open(path, "w") as f:
            if format == "yaml":
                yaml.dump(data, f, default_flow_style=False)
            elif format == "json":
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")


# Load configuration
def load_config() -> Config:
    """Load configuration from file or environment."""
    config_path = Path(DEFAULT_CONFIG_PATH)

    if config_path.exists():
        return Config.load_from_file(str(config_path))
    else:
        return Config.load_from_env()


# Global configuration instance
config = load_config()

# Backward compatibility exports
QDRANT_HOST = config.qdrant.host
QDRANT_PORT = config.qdrant.port
COLLECTION_NAME = config.vector.collection_name
EMBEDDING_MODEL = config.vector.embedding_model
VECTOR_SIZE = config.vector.vector_size
MAX_TOKENS = config.vector.max_tokens
TOP_K = config.vector.top_k
MIN_SCORE = config.vector.min_score
API_HOST = config.api.host
API_PORT = config.api.port
MCP_SERVER_NAME = config.mcp.server_name
MCP_SERVER_VERSION = config.mcp.server_version
