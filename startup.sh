#!/bin/bash
set -e

# Security: Don't expose sensitive information
set +x

# Ensure directories exist with correct permissions
# These should already be created in Dockerfile, but double-check
for dir in /var/log/supervisor /var/run /qdrant/storage /qdrant/snapshots; do
    if [ ! -d "$dir" ]; then
        echo "Error: Required directory $dir does not exist"
        exit 1
    fi
done

# Check if running in MCP mode
if [ "$1" = "python3" ] && [ "$2" = "/app/server.py" ] && [ "$3" = "--mcp" ]; then
    # MCP mode - run Python server directly without supervisor
    exec python3 /app/server.py --mcp
else
    # Normal mode - run supervisor to start all services
    # Use exec to replace shell process for proper signal handling
    exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
fi