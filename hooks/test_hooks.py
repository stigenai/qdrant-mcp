#!/usr/bin/env python3
"""Test script for API-based hooks."""

import json
import subprocess
import tempfile
import os
import sys
from pathlib import Path

# Configuration
API_ENDPOINT = os.environ.get("QDRANT_MCP_API", "http://localhost:8000")


def test_api_connectivity():
    """Test if the API is accessible."""
    import requests

    print("Testing API connectivity...")
    try:
        response = requests.get(f"{API_ENDPOINT}/health")
        if response.status_code == 200:
            print(f"✓ API is accessible at {API_ENDPOINT}")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Failed to connect to API: {e}")
        return False


def test_precompact_hook():
    """Test the precompact_vectorize hook."""
    print("\nTesting precompact_vectorize.py hook...")

    # Create a test transcript
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Write some test messages
        messages = [
            {
                "role": "user",
                "content": "Short message",
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "role": "assistant",
                "content": "This is a very long message that should be vectorized. "
                * 100,  # Make it long
                "timestamp": "2024-01-01T00:01:00Z",
            },
            {
                "role": "user",
                "content": "Another long message for testing vectorization. " * 100,
                "timestamp": "2024-01-01T00:02:00Z",
            },
        ]

        for msg in messages:
            f.write(json.dumps(msg) + "\n")

        transcript_path = f.name

    try:
        # Prepare hook input
        hook_input = json.dumps(
            {
                "hook_event_name": "TranscriptProcess",
                "payload": {"transcript_path": transcript_path},
            }
        )

        # Run the hook
        script_dir = Path(__file__).parent
        hook_path = script_dir / "precompact_vectorize.py"

        result = subprocess.run(
            [sys.executable, str(hook_path)],
            input=hook_input,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            output = json.loads(result.stdout)
            print(f"✓ Hook completed successfully")
            print(f"  - Vectorized: {output.get('vectorized', 0)} messages")
            print(f"  - Total messages: {output.get('total_messages', 0)}")

            # Check if transcript was modified
            with open(transcript_path, "r") as f:
                modified_content = f.read()
                if "[[VEC:" in modified_content:
                    print("✓ Vector stubs created in transcript")
                else:
                    print("✗ No vector stubs found in transcript")

            return True
        else:
            print(f"✗ Hook failed with return code {result.returncode}")
            print(f"  Error: {result.stderr}")
            return False

    finally:
        # Clean up
        os.unlink(transcript_path)


def test_retrieve_hook():
    """Test the retrieve_vectors hook."""
    print("\nTesting retrieve_vectors.py hook...")

    # Test with UserPromptSubmit event
    hook_input = json.dumps(
        {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Tell me about machine learning and AI",
        }
    )

    # Run the hook
    script_dir = Path(__file__).parent
    hook_path = script_dir / "retrieve_vectors.py"

    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=hook_input,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        try:
            output = json.loads(result.stdout)
            if "prompt" in output:
                print("✓ Hook enriched the prompt with context")
                if "Retrieved Context from Vector Store" in output["prompt"]:
                    print("✓ Context was successfully retrieved")
                else:
                    print(
                        "  - No relevant context found (this is normal if no vectors match)"
                    )
            elif output.get("decision") == "approve":
                print("✓ Hook approved (no relevant context found)")
            else:
                print(f"  Unexpected output: {output}")
            return True
        except json.JSONDecodeError:
            print(f"✗ Failed to parse hook output: {result.stdout}")
            return False
    else:
        print(f"✗ Hook failed with return code {result.returncode}")
        print(f"  Error: {result.stderr}")
        return False


def main():
    """Run all tests."""
    print("Qdrant MCP API Hooks Test Suite")
    print("===============================")
    print(f"API Endpoint: {API_ENDPOINT}")
    print()

    # Check if hooks exist
    script_dir = Path(__file__).parent
    hooks = ["precompact_vectorize.py", "retrieve_vectors.py"]

    for hook in hooks:
        hook_path = script_dir / hook
        if not hook_path.exists():
            print(f"✗ Hook not found: {hook}")
            sys.exit(1)

    print("✓ All hooks found")

    # Run tests
    tests_passed = 0
    total_tests = 3

    if test_api_connectivity():
        tests_passed += 1

    if test_precompact_hook():
        tests_passed += 1

    if test_retrieve_hook():
        tests_passed += 1

    # Summary
    print(f"\nTest Summary: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
