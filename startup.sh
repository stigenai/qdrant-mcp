#!/bin/bash

# Check if running in MCP mode
if [ "$1" = "python3" ] && [ "$2" = "/app/server.py" ] && [ "$3" = "--mcp" ]; then
    # MCP mode - run Python server directly without supervisor
    exec python3 /app/server.py --mcp
else
    # Normal mode - run supervisor to start both services
    exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
fi