#!/usr/bin/env python
"""
Example script demonstrating how to extract product data from an e-commerce website.
"""

import asyncio
import json
import argparse
import logging
import os
import sys

# Add parent directory to path to import crawl4ai_llm
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crawl4ai_llm.extraction import ProductExtractor
from crawl4ai_llm.config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def extract_product(url: str, strategy: str = "auto_schema", no_fallback: bool = False):
    """
    Extract product data from a URL.
    
    Args:
        url: URL of the product page.
        strategy: Extraction strategy to use ("auto_schema" or "llm").
        no_fallback: Disable fallback to LLM if auto schema fails.
    """
    extractor = ProductExtractor()
    
    logger.info(f"Extracting product data from {url} using {strategy} strategy")
    product_data = await extractor.extract(
        url=url,
        strategy=strategy,
        fallback=not no_fallback
    )
    
    # Print the extracted data as formatted JSON
    print(json.dumps(product_data.model_dump(exclude_none=True), indent=2))
    
    # Log extraction success
    if product_data.extraction_success:
        logger.info(f"Successfully extracted product: {product_data.title}")
    else:
        logger.warning(f"Extraction partially failed for: {product_data.title}")
    
    return product_data


def main():
    """Main function to parse arguments and run the extraction."""
    parser = argparse.ArgumentParser(description="Extract product data from an e-commerce website")
    parser.add_argument("url", help="URL of the product page")
    parser.add_argument(
        "--strategy", 
        choices=["auto_schema", "llm"], 
        default="auto_schema",
        help="Extraction strategy to use"
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback to LLM if auto schema fails"
    )
    
    args = parser.parse_args()
    
    # Run the extraction
    asyncio.run(extract_product(args.url, args.strategy, args.no_fallback))


if __name__ == "__main__":
    main() 