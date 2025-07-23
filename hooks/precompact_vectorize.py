#!/usr/bin/env python3
"""Replaces long transcript messages with vector stubs using Qdrant MCP API."""
import json
import os
import sys
import uuid
import pathlib
import tiktoken
import orjson
import requests
from typing import Optional

# Configuration
MAX_TOKENS = 512  # threshold to vectorise
COLLECTION = "claude_vectors"
API_ENDPOINT = os.environ.get("QDRANT_MCP_API", "http://localhost:8000")
VECTOR_SIZE = 384

# Initialize token counter
enc = tiktoken.encoding_for_model("gpt-3.5-turbo")  # claude-3-sonnet not available


def num_tokens(txt: str) -> int:
    """Count tokens in text."""
    return len(enc.encode(txt))


def ensure_collection_exists():
    """Ensure the collection exists in Qdrant."""
    try:
        # Check if collection exists
        response = requests.get(f"{API_ENDPOINT}/collections/{COLLECTION}")
        if response.status_code == 200:
            return True
    except Exception:
        pass

    # Create collection if it doesn't exist
    try:
        response = requests.post(
            f"{API_ENDPOINT}/collections",
            json={"name": COLLECTION, "vector_size": VECTOR_SIZE, "distance": "cosine"},
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Warning: Failed to create collection: {e}", file=sys.stderr)
        return False


def store_vector(content: str, role: str, timestamp: str = "") -> Optional[str]:
    """Store content as vector in Qdrant and return the ID."""
    uid = str(uuid.uuid4())

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
