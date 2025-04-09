"""
Command-line interface for crawl4ai_llm.
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime

from .extraction import ProductExtractor

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
    
    # Create output with metadata
    output = product_data.model_dump(exclude_none=True)
    output["_meta"] = {
        "timestamp": datetime.now().isoformat(),
        "strategy_used": strategy,
        "fallback_enabled": not no_fallback,
        "url": url
    }
    
    # Output as JSON
    print(json.dumps(output, indent=2))
    
    # Log extraction success
    if product_data.extraction_success:
        logger.info(f"Successfully extracted product: {product_data.title}")
    else:
        logger.warning(f"Extraction partially failed for: {product_data.title}")
    
    return product_data


def main():
    """Main function to parse arguments and run the extraction."""
    parser = argparse.ArgumentParser(
        description="Extract product data from e-commerce websites"
    )
    parser.add_argument(
        "url", 
        help="URL of the product page to extract data from"
    )
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
    parser.add_argument(
        "--output",
        help="Output file path (default: print to stdout)"
    )
    
    args = parser.parse_args()
    
    # Run the extraction
    result = asyncio.run(extract_product(args.url, args.strategy, args.no_fallback))
    
    # Save to file if specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result.model_dump(exclude_none=True), f, indent=2)
        logger.info(f"Saved output to {args.output}")


if __name__ == "__main__":
    main() 