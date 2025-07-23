#!/usr/bin/env python3
"""Replaces long transcript messages with vector stubs using Qdrant MCP API."""
import json
import os
import pathlib
import sys
import uuid
import warnings

import orjson
import requests
import tiktoken
import urllib3

# Configuration
MAX_TOKENS = 512  # threshold to vectorise
COLLECTION = "claude_vectors"
VECTOR_SIZE = 384

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

# Initialize token counter
enc = tiktoken.encoding_for_model("gpt-3.5-turbo")  # claude-3-sonnet not available


def num_tokens(txt: str) -> int:
    """Count tokens in text."""
    return len(enc.encode(txt))


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


def ensure_collection_exists():
    """Ensure the collection exists in Qdrant."""
    verify = get_ssl_config()

    try:
        # Check if collection exists
        response = requests.get(
            f"{API_ENDPOINT}/collections/{COLLECTION}", verify=verify
        )
        if response.status_code == 200:
            return True
    except Exception:
        pass

    # Create collection if it doesn't exist
    try:
        response = requests.post(
            f"{API_ENDPOINT}/collections",
            json={"name": COLLECTION, "vector_size": VECTOR_SIZE, "distance": "cosine"},
            verify=verify,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Warning: Failed to create collection: {e}", file=sys.stderr)
        return False


def store_vector(content: str, role: str, timestamp: str = "") -> str | None:
    """Store content as vector in Qdrant and return the ID."""
    uid = str(uuid.uuid4())
    verify = get_ssl_config()

    try:
        response = requests.post(
            f"{API_ENDPOINT}/vectors/upsert",
            json={
                "collection": COLLECTION,
                "points": [
                    {
                        "id": uid,
                        "content": content,
                        "payload": {
                            "role": role,
                            "content": content,
                            "tokens": num_tokens(content),
                            "timestamp": timestamp,
                        },
                    }
                ],
            },
            verify=verify,
        )

        if response.status_code == 200:
            return uid
        else:
            print(f"Warning: Failed to store vector: {response.text}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"Warning: Failed to store vector: {e}", file=sys.stderr)
        return None


def main():
    try:
        # Read hook input
        raw_input = sys.stdin.read()
        if not raw_input:
            print(json.dumps({"error": "No input received"}), file=sys.stderr)
            sys.exit(1)

        try:
            hook = json.loads(raw_input)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON input: {e}"}), file=sys.stderr)
            sys.exit(1)

        # Handle both direct and nested payload formats
        if "payload" in hook:
            payload = hook["payload"]
            transcript_path = payload.get("transcript_path")
        else:
            transcript_path = hook.get("transcript_path")

        if not transcript_path:
            print(json.dumps({"error": "No transcript_path provided"}), file=sys.stderr)
            sys.exit(1)

        path = pathlib.Path(os.path.expanduser(transcript_path))

        if not path.exists():
            print(
                json.dumps({"error": f"Transcript path not found: {path}"}),
                file=sys.stderr,
            )
            sys.exit(1)

        # Ensure collection exists
        if not ensure_collection_exists():
            print(
                json.dumps({"error": "Failed to ensure collection exists"}),
                file=sys.stderr,
            )
            sys.exit(1)

        updated = []
        vectorized_count = 0

        # Process transcript
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    msg = orjson.loads(line)
                except Exception as e:
                    print(f"Warning: Failed to parse line: {e}", file=sys.stderr)
                    updated.append(line.rstrip())
                    continue

                # Check if message should be vectorized
                if (
                    msg.get("role") in ("user", "assistant")
                    and msg.get("content")
                    and num_tokens(str(msg["content"])) > MAX_TOKENS
                ):
                    content = str(msg["content"])

                    # Store in vector DB via API
                    uid = store_vector(content, msg["role"], msg.get("timestamp", ""))

                    if uid:
                        # Replace content with stub
                        msg["content"] = f"[[VEC:{uid}]]"
                        msg["original_tokens"] = num_tokens(content)
                        vectorized_count += 1

                updated.append(orjson.dumps(msg).decode())

        # Atomic write
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
        temp_path.replace(path)

        # Return success
        print(
            json.dumps(
                {
                    "status": "success",
                    "vectorized": vectorized_count,
                    "total_messages": len(updated),
                }
            )
        )

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
