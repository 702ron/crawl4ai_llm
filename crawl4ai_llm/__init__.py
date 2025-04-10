"""
Crawl4AI LLM Product Extraction package.

This package provides tools for extracting structured product data
from e-commerce websites using LLMs and automated schema generation.
"""

import logging
from typing import Optional

from .config import get_config
from .extraction import ProductExtractor
from .extraction.schema_generator import SchemaGenerator
from .models import ProductData

# Set up package logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Version
__version__ = "0.1.0"


async def extract_product(
    url: str,
    strategy: str = "auto_schema",
    fallback: bool = True,
    cache: bool = True,
    config_path: Optional[str] = None,
) -> ProductData:
    """
    Extract product data from a URL.

    Args:
        url: URL of the product page.
        strategy: Extraction strategy ("auto_schema" or "llm").
        fallback: Whether to fall back to LLM if auto schema fails.
        cache: Whether to use cached schemas.
        config_path: Path to config file (optional).

    Returns:
        ProductData object containing extracted product information.
    """
    # Load configuration
    if config_path:
        get_config(config_path)
    
    # Initialize extractor
    extractor = ProductExtractor()
    
    # Extract product data
    result = await extractor.extract(
        url=url, strategy=strategy, fallback=fallback, use_cache=cache
    )
    
    return result


__all__ = [
    "extract_product",
    "ProductData",
    "ProductExtractor",
    "SchemaGenerator",
    "get_config",
]

# API server CLI entrypoint
def api():
    """Command-line entry point for the API server."""
    from .api.cli import main
    main()

# If importing the module directly (e.g., python -m crawl4ai_llm)
if __name__ == "__main__":
    import sys
    from .__main__ import main
    sys.exit(main())
