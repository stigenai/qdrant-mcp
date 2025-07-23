#!/usr/bin/env python3
"""Generate configuration file for Qdrant MCP."""

import argparse
import sys
from pathlib import Path
from config import Config


def main():
    parser = argparse.ArgumentParser(
        description="Generate Qdrant MCP configuration file"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="config/config.yaml",
        help="Output configuration file path (default: config/config.yaml)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["yaml", "json"],
        default="yaml",
        help="Configuration file format (default: yaml)",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Generate production-ready configuration with secure defaults",
    )
    parser.add_argument("--data-path", help="Path for Qdrant data storage")
    parser.add_argument("--snapshots-path", help="Path for Qdrant snapshots")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--api-host", help="API server host")
    parser.add_argument("--api-port", type=int, help="API server port")

    args = parser.parse_args()

    # Create base configuration
    if args.production:
        # Production defaults
        config = Config(
            qdrant=Config.qdrant.__class__(
                data_path=args.data_path or "/data/qdrant/storage",
                snapshots_path=args.snapshots_path or "/data/qdrant/snapshots",
                max_payload_size_mb=5,
            ),
            vector=Config.vector.__class__(
                on_disk_payload=True, top_k=20, min_score=0.3
            ),
            api=Config.api.__class__(
                host=args.api_host or "127.0.0.1",
                port=args.api_port or 8000,
                workers=4,
                log_level="warning",
                cors_origins=["https://your-domain.com"],
            ),
            logging=Config.logging.__class__(
                log_level="WARNING", max_bytes=52428800, backup_count=10  # 50MB
            ),
            security=Config.security.__class__(
                api_key=args.api_key or "CHANGE_ME_IN_PRODUCTION",
                rate_limit_per_minute=100,
            ),
        )
    else:
        # Development defaults
        config = Config()

        # Apply custom paths if provided
        if args.data_path:
            config.qdrant.data_path = args.data_path
        if args.snapshots_path:
            config.qdrant.snapshots_path = args.snapshots_path
        if args.api_key:
            config.security.api_key = args.api_key
        if args.api_host:
            config.api.host = args.api_host
        if args.api_port:
            config.api.port = args.api_port

    # Save configuration
    try:
        config.save_to_file(args.output, format=args.format)
        print(f"Configuration saved to: {args.output}")

        if args.production and args.api_key == "CHANGE_ME_IN_PRODUCTION":
            print("\nWARNING: Remember to set a secure API key in production!")
            print("Generate one with: openssl rand -base64 32")

    except Exception as e:
        print(f"Error saving configuration: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
