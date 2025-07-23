# Multi-stage build for smaller final image
# Stage 1: Build stage with full dependencies
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock* .

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Stage 2: Qdrant base image
FROM qdrant/qdrant:latest AS qdrant-base

# Stage 3: Final minimal runtime image
FROM python:3.11-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/*

# Copy Qdrant binary from qdrant-base
COPY --from=qdrant-base /qdrant /qdrant

# Create non-root user and group
RUN groupadd -r qdrant --gid=1000 && \
    useradd -r -g qdrant --uid=1000 --home-dir=/app --shell=/bin/bash qdrant

# Create necessary directories with correct permissions
RUN mkdir -p /app /app/config /qdrant/storage /qdrant/snapshots /var/log/supervisor /var/run && \
    chown -R qdrant:qdrant /app /qdrant /var/log/supervisor /var/run

# Copy Python packages from builder
COPY --from=builder --chown=qdrant:qdrant /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=qdrant:qdrant /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR /app

# Copy application code as non-root user
COPY --chown=qdrant:qdrant . .

# Copy configuration files with correct permissions
COPY --chown=qdrant:qdrant supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY --chown=qdrant:qdrant startup.sh /app/startup.sh

# Make scripts executable
RUN chmod +x /app/startup.sh

# Environment variables
ENV QDRANT_DATA_PATH="/qdrant/storage" \
    QDRANT_SNAPSHOTS_PATH="/qdrant/snapshots" \
    QDRANT_TELEMETRY_DISABLED="true" \
    QDRANT_MCP_CONFIG="/app/config/config.yaml" \
    UV_SYSTEM_PYTHON=1

# Security: Don't run as root
USER qdrant

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:6333/health && \
        curl -f http://localhost:8000/health && \
        curl -f http://localhost:8001/ || exit 1

# Expose ports (as non-root, must be > 1024 or use capabilities)
EXPOSE 8000 8001 6333

# Set security labels
LABEL security.scan="true" \
      security.nonroot="true" \
      maintainer="qdrant-mcp"

# Use exec form to ensure proper signal handling
ENTRYPOINT ["/app/startup.sh"]