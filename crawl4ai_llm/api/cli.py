"""
Command-line interface for the Crawl4AI LLM API server.
"""

import argparse
import logging
import os
import sys
from typing import List, Optional

import secrets

from .app import start_server
from .auth import User, UserRole, USERS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start the Crawl4AI LLM API server")

    # Server configuration
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("CRAWL4AI_API_HOST", "0.0.0.0"),
        help="Host to bind the server to (default: 0.0.0.0 or CRAWL4AI_API_HOST env var)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("CRAWL4AI_API_PORT", "8000")),
        help="Port to bind the server to (default: 8000 or CRAWL4AI_API_PORT env var)",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("CRAWL4AI_LOG_LEVEL", "INFO"),
        help="Set the logging level (default: INFO or CRAWL4AI_LOG_LEVEL env var)",
    )

    # Authentication subcommands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create admin user command
    create_admin = subparsers.add_parser("create-admin", help="Create an admin user")
    create_admin.add_argument(
        "--username",
        type=str,
        default="admin",
        help="Username for the admin (default: admin)",
    )
    create_admin.add_argument(
        "--rate-limit",
        type=int,
        default=120,
        help="Rate limit for the admin user (default: 120 requests per minute)",
    )
    create_admin.add_argument(
        "--api-key",
        type=str,
        help="Custom API key for the admin (default: auto-generated)",
    )

    return parser.parse_args(args)


def create_admin_user(username: str, rate_limit: int, api_key: Optional[str] = None) -> str:
    """Create an admin user with the given parameters and return the API key."""
    # Generate an API key if none was provided
    if not api_key:
        api_key = secrets.token_hex(16)
    
    # Create the admin user
    USERS[api_key] = User(
        username=username,
        api_key=api_key,
        roles=[UserRole.ADMIN],
        rate_limit=rate_limit,
    )
    
    return api_key


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    parsed_args = parse_args(args)

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, parsed_args.log_level))

    # Handle subcommands
    if parsed_args.command == "create-admin":
        api_key = create_admin_user(
            username=parsed_args.username,
            rate_limit=parsed_args.rate_limit,
            api_key=parsed_args.api_key,
        )
        
        logger.info(f"Created admin user '{parsed_args.username}' with API key: {api_key}")
        logger.info("Use this API key to authenticate with the API")
        logger.info("Store it securely as you won't be able to retrieve it later")
        
        # Setting the API key in the environment for the current session
        os.environ["ADMIN_API_KEY"] = api_key
        
        return 0

    # Start the server
    logger.info(
        f"Starting Crawl4AI LLM API server on {parsed_args.host}:{parsed_args.port}"
    )

    try:
        # Start the server
        start_server(
            host=parsed_args.host, port=parsed_args.port, reload=parsed_args.reload
        )
        return 0
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
