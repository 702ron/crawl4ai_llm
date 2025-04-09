"""
Command-line interface for the Crawl4AI LLM API server.
"""

import argparse
import logging
import os
import sys
from typing import List, Optional

from .app import start_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Start the Crawl4AI LLM API server"
    )
    
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
    
    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    parsed_args = parse_args(args)
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, parsed_args.log_level))
    
    logger.info(f"Starting Crawl4AI LLM API server on {parsed_args.host}:{parsed_args.port}")
    
    try:
        # Start the server
        start_server(
            host=parsed_args.host,
            port=parsed_args.port,
            reload=parsed_args.reload
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