#!/bin/bash

# Setup script for Qdrant MCP API hooks

echo "Qdrant MCP API Hooks Setup"
echo "=========================="
echo

# Check if Claude hooks directory exists
HOOKS_DIR="$HOME/.claude/hooks"
if [ ! -d "$HOOKS_DIR" ]; then
    echo "Error: Claude hooks directory not found at $HOOKS_DIR"
    echo "Please ensure Claude Code is installed and configured."
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to create symlink with backup
create_symlink() {
    local source="$1"
    local target="$2"
    local name="$3"
    
    if [ -e "$target" ]; then
        if [ -L "$target" ]; then
            echo "  - Removing existing symlink: $target"
            rm "$target"
        else
            echo "  - Backing up existing file: $target -> ${target}.backup"
            mv "$target" "${target}.backup"
        fi
    fi
    
    ln -sf "$source" "$target"
    echo "  ✓ Created symlink for $name"
}

echo "Setting up API-based hooks..."
echo

# Option to use different names to avoid conflicts
read -p "Use '_api' suffix for hook names to avoid conflicts? (y/n) [y]: " use_suffix
use_suffix=${use_suffix:-y}

if [ "$use_suffix" = "y" ] || [ "$use_suffix" = "Y" ]; then
    create_symlink "$SCRIPT_DIR/precompact_vectorize.py" "$HOOKS_DIR/precompact_vectorize_api.py" "precompact_vectorize_api.py"
    create_symlink "$SCRIPT_DIR/retrieve_vectors.py" "$HOOKS_DIR/retrieve_vectors_api.py" "retrieve_vectors_api.py"
    echo
    echo "Hooks installed with '_api' suffix to avoid conflicts with existing hooks."
else
    create_symlink "$SCRIPT_DIR/precompact_vectorize.py" "$HOOKS_DIR/precompact_vectorize.py" "precompact_vectorize.py"
    create_symlink "$SCRIPT_DIR/retrieve_vectors.py" "$HOOKS_DIR/retrieve_vectors.py" "retrieve_vectors.py"
    echo
    echo "Hooks installed, replacing any existing hooks."
fi

echo
echo "Configuration:"
echo "=============="
echo
echo "The hooks use the QDRANT_MCP_API environment variable for the API endpoint."
echo "Default: http://localhost:8000"
echo
echo "To use a different endpoint, set the environment variable:"
echo "  export QDRANT_MCP_API=\"http://your-server:8000\""
echo
echo "You can add this to your shell profile (~/.bashrc, ~/.zshrc, etc.)"
echo

# Check if API is accessible
API_ENDPOINT="${QDRANT_MCP_API:-http://localhost:8000}"
echo "Checking API connectivity at $API_ENDPOINT..."
if curl -s -f "$API_ENDPOINT/health" > /dev/null 2>&1; then
    echo "✓ API is accessible"
else
    echo "✗ API is not accessible. Please ensure the Qdrant MCP server is running:"
    echo "  docker run -p 8000:8000 -p 8001:8001 -p 6333:6333 -v qdrant-data:/qdrant/storage qdrant-mcp"
fi

echo
echo "Setup complete!"