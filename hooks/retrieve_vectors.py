#!/usr/bin/env python3
"""Retrieves relevant vector content for RAG during tool use and user prompts using Qdrant MCP API."""

import json
import os
import sys
import warnings
from typing import Any

import requests
import urllib3

# Configuration
COLLECTION = "claude_vectors"
TOP_K = 10  # Number of relevant chunks to retrieve
MIN_SCORE = 0.22  # Minimum similarity score

# API endpoint configuration
API_HOST = os.environ.get("QDRANT_MCP_HOST", "localhost")
API_PORT = os.environ.get("QDRANT_MCP_PORT", "8000")
API_ENDPOINT = os.environ.get("QDRANT_MCP_API", None)

# Build endpoint if not explicitly provided
if not API_ENDPOINT:
    # Auto-detect HTTPS based on port or explicit HTTPS in host
    if API_HOST.startswith("https://") or API_PORT == "443":
        API_ENDPOINT = (
            f"{API_HOST}:{API_PORT}" if not API_HOST.startswith("http") else API_HOST
        )
    else:
        scheme = "https" if API_HOST.startswith("https://") else "http"
        host = API_HOST.replace("https://", "").replace("http://", "")
        API_ENDPOINT = f"{scheme}://{host}:{API_PORT}"
else:
    # Ensure API_ENDPOINT has a scheme
    if not API_ENDPOINT.startswith(("http://", "https://")):
        API_ENDPOINT = f"http://{API_ENDPOINT}"

# HTTPS configuration
IS_HTTPS = API_ENDPOINT.startswith("https://")
VERIFY_SSL = os.environ.get("QDRANT_MCP_VERIFY_SSL", "true").lower() == "true"
SSL_CERT_PATH = os.environ.get("QDRANT_MCP_SSL_CERT", None)
CA_BUNDLE_PATH = os.environ.get("QDRANT_MCP_CA_BUNDLE", None)
CA_CERTS_DIR = os.environ.get("QDRANT_MCP_CA_CERTS_DIR", None)

# Disable SSL warnings if HTTPS is used and verification is disabled
if IS_HTTPS and not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")


def get_ssl_config():
    """Get SSL configuration for requests."""
    # If not HTTPS, no SSL config needed
    if not IS_HTTPS:
        return True

    # If SSL verification is disabled
    if not VERIFY_SSL:
        return False

    # Check for specific certificate configurations
    if SSL_CERT_PATH and os.path.exists(SSL_CERT_PATH):
        return SSL_CERT_PATH

    if CA_BUNDLE_PATH and os.path.exists(CA_BUNDLE_PATH):
        return CA_BUNDLE_PATH

    # For CA certificates directory, requests expects REQUESTS_CA_BUNDLE env var
    if CA_CERTS_DIR and os.path.exists(CA_CERTS_DIR):
        # Set the environment variable that requests uses
        os.environ["REQUESTS_CA_BUNDLE"] = CA_CERTS_DIR

    return True


def search_vectors(query: str) -> list[dict[str, Any]]:
    """Search for relevant vectors using the API."""
    verify = get_ssl_config()

    try:
        response = requests.post(
            f"{API_ENDPOINT}/vectors/search",
            json={
                "query": query,
                "collection": COLLECTION,
                "limit": TOP_K,
                "score_threshold": MIN_SCORE,
            },
            verify=verify,
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("hits", [])
        else:
            print(f"Warning: Search failed: {response.text}", file=sys.stderr)
            return []

    except Exception as e:
        print(f"Warning: Failed to search vectors: {e}", file=sys.stderr)
        return []


def check_collection_exists() -> bool:
    """Check if the collection exists."""
    verify = get_ssl_config()

    try:
        response = requests.get(
            f"{API_ENDPOINT}/collections/{COLLECTION}", verify=verify
        )
        return response.status_code == 200
    except Exception:
        return False


def main():
    try:
        # Read hook input
        raw_input = sys.stdin.read()
        if not raw_input:
            print(json.dumps({"decision": "approve"}))
            return

        try:
            hook_data = json.loads(raw_input)
        except json.JSONDecodeError:
            print(json.dumps({"decision": "approve"}))
            return

        # Determine hook event type
        hook_event_name = hook_data.get("hook_event_name", "")
        query = ""

        if hook_event_name == "UserPromptSubmit":
            # Extract query from user prompt
            query = hook_data.get("prompt", "")
        elif hook_event_name == "PreToolUse":
            # Extract query from tool input
            tool_input = hook_data.get("tool_input", {})

            # Try to extract meaningful query from tool input
            if isinstance(tool_input, dict):
                # Common fields across different tools
                query = (
                    tool_input.get("content")
                    or tool_input.get("query")
                    or tool_input.get("prompt")
                    or tool_input.get("description")
                    or tool_input.get("command")  # For Bash tool
                    or tool_input.get("pattern")  # For Grep tool
                    or ""
                )
            elif isinstance(tool_input, str):
                query = tool_input

        if not query:
            # No query to search for
            print(json.dumps({"decision": "approve"}))
            return

        # Check if collection exists
        if not check_collection_exists():
            # No vectors stored yet
            print(json.dumps({"decision": "approve"}))
            return

        # Search for relevant vectors via API
        hits = search_vectors(query)

        if not hits:
            # No relevant content found
            print(json.dumps({"decision": "approve"}))
            return

        # Build context from hits
        context_parts = []
        for i, hit in enumerate(hits, 1):
            payload = hit.get("payload", {})
            role = payload.get("role", "unknown")
            content = payload.get("content", "")
            score = hit.get("score", 0.0)

            if content:
                context_parts.append(
                    f"[Context {i} - {role} message (similarity: {score:.2f})]:\n{content}"
                )

        if context_parts:
            context = "\n\n---\n\n".join(context_parts)

            if hook_event_name == "UserPromptSubmit":
                # For UserPromptSubmit, inject context into the prompt
                enriched_prompt = (
                    f"{query}\n\n## Retrieved Context from Vector Store:\n\n{context}"
                )
                print(json.dumps({"prompt": enriched_prompt}))
            else:
                # For PreToolUse and other events, use decision/reason format
                print(
                    json.dumps(
                        {
                            "decision": "block",
                            "reason": f"Retrieved {len(hits)} relevant context(s) from vector store:\n\n{context}\n\nContinue with the task using this additional context.",
                        }
                    )
                )
        else:
            # No relevant context found, approve without modification
            print(json.dumps({"decision": "approve"}))

    except Exception as e:
        # Log error but approve continuation
        print(f"Error in retrieve_vectors: {e}", file=sys.stderr)
        print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
