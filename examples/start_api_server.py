#!/usr/bin/env python
"""
Helper script to start the Crawl4AI LLM API server and manage admin users.

This script provides a simplified interface to:
1. Start the API server with custom host/port
2. Create admin users with API keys
3. View active API keys

Usage:
    # Start the API server
    python start_api_server.py start --host 0.0.0.0 --port 8000
    
    # Create an admin user
    python start_api_server.py create-admin --username admin --rate-limit 120
"""

import argparse
import os
import subprocess
import sys


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Crawl4AI LLM API Server Helper")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Start server command
    start_parser = subparsers.add_parser("start", help="Start the API server")
    start_parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    start_parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind to (default: 8000)"
    )
    start_parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    start_parser.add_argument(
        "--log-level", default="INFO", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)"
    )
    
    # Create admin command
    admin_parser = subparsers.add_parser("create-admin", help="Create an admin user")
    admin_parser.add_argument(
        "--username", default="admin", help="Username for the admin (default: admin)"
    )
    admin_parser.add_argument(
        "--rate-limit", type=int, default=120,
        help="Rate limit for the admin user (default: 120 requests per minute)"
    )
    admin_parser.add_argument(
        "--api-key", help="Custom API key for the admin (default: auto-generated)"
    )
    
    return parser.parse_args()


def run_command(command):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(command)}")
        print(f"Exit code: {e.returncode}")
        print(f"Error output: {e.stderr}")
        sys.exit(e.returncode)


def start_server(args):
    """Start the API server with the given arguments."""
    print(f"Starting Crawl4AI LLM API server on {args.host}:{args.port}...")
    
    command = [
        sys.executable, "-m", "crawl4ai_llm.api.cli",
        "--host", args.host,
        "--port", str(args.port),
        "--log-level", args.log_level
    ]
    
    if args.reload:
        command.append("--reload")
    
    # This will run in the foreground and block until terminated
    try:
        subprocess.run(command, check=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"Server exited with error: {e.returncode}")
        print(e.stderr)
        sys.exit(e.returncode)


def create_admin(args):
    """Create an admin user with the given arguments."""
    print(f"Creating admin user '{args.username}'...")
    
    command = [
        sys.executable, "-m", "crawl4ai_llm.api.cli",
        "create-admin",
        "--username", args.username,
        "--rate-limit", str(args.rate_limit)
    ]
    
    if args.api_key:
        command.extend(["--api-key", args.api_key])
    
    output = run_command(command)
    print(output)
    
    # Extract the API key from the output
    for line in output.splitlines():
        if "API key:" in line:
            api_key = line.split("API key:")[1].strip()
            print("\nKeep this API key in a secure location!")
            print(f"To use it, include the following header in your HTTP requests:")
            print(f'X-API-Key: {api_key}')
            
            # Example curl commands
            print("\nExample API usage:")
            print(f'curl -H "X-API-Key: {api_key}" http://localhost:8000/')
            print(f'curl -H "X-API-Key: {api_key}" http://localhost:8000/api-key')
            break


def main():
    """Main entry point."""
    args = parse_args()
    
    if not args.command:
        print("Error: No command specified. Use --help for usage information.")
        sys.exit(1)
    
    if args.command == "start":
        start_server(args)
    elif args.command == "create-admin":
        create_admin(args)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main() 