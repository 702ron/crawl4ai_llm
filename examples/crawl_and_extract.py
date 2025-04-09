#!/usr/bin/env python
"""
Example script demonstrating the full crawl-extract-store workflow.

This script:
1. Crawls an e-commerce product page
2. Extracts product information using the configured extraction strategy
3. Stores the extracted data using the configured storage backend
4. Prints a summary of the results
"""
import asyncio
import logging
import json
import argparse
import sys
from datetime import datetime
from pathlib import Path

from crawl4ai_llm.config import Config, CrawlerConfig, LLMConfig, StorageConfig
from crawl4ai_llm.crawler.base import BaseCrawler
from crawl4ai_llm.extraction.product_extractor import ProductExtractor, ExtractionStrategy
from crawl4ai_llm.storage.factory import get_storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("crawl_and_extract")

async def crawl_and_extract(url, extraction_strategy, storage_path, use_fallback=False):
    """
    Crawl a product page, extract data, and store the results.
    
    Args:
        url: URL of the product page to crawl
        extraction_strategy: Strategy to use for extraction (auto, schema, llm)
        storage_path: Path to store extracted data
        use_fallback: Whether to use fallback extraction if the primary method fails
        
    Returns:
        The ID of the stored product data
    """
    start_time = datetime.now()
    logger.info(f"Starting extraction for {url}")
    
    # Initialize configuration
    config = Config(
        crawler=CrawlerConfig(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            timeout=30,
            retry_count=2,
            rate_limit=1.0
        ),
        llm=LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key=None,  # Will use environment variable OPENAI_API_KEY
            temperature=0.0,
            max_tokens=2000
        ),
        storage=StorageConfig(
            type="json",
            path=storage_path,
            use_uuid=True
        )
    )
    
    # Create components
    crawler = BaseCrawler(config=config.crawler)
    extractor = ProductExtractor(config=config)
    storage = get_storage(config.storage)
    
    try:
        # Crawl the page
        logger.info(f"Crawling {url}")
        content = await crawler.fetch_page(url)
        if not content:
            logger.error(f"Failed to fetch content from {url}")
            return None

        # Extract product data
        logger.info(f"Extracting product data using {extraction_strategy} strategy")
        strategy = ExtractionStrategy(extraction_strategy)
        product_data = await extractor.extract(url, content, strategy, fallback=use_fallback)
        
        if not product_data:
            logger.error("Failed to extract product data")
            return None
            
        # Store the data
        logger.info("Storing extracted product data")
        product_id = storage.save_product(product_data)
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Extraction completed successfully in {execution_time:.2f} seconds")
        logger.info(f"Product ID: {product_id}")
        
        # Print a summary
        summary = {
            "url": url,
            "product_id": product_id,
            "title": product_data.title,
            "extraction_strategy": extraction_strategy,
            "extraction_time": execution_time,
            "price": f"{product_data.price.amount} {product_data.price.currency}" if product_data.price else "N/A",
            "images_count": len(product_data.images) if product_data.images else 0,
            "storage_path": str(Path(config.storage.path) / f"{product_id}.json")
        }
        
        logger.info(f"Summary:\n{json.dumps(summary, indent=2)}")
        return product_id
        
    except Exception as e:
        logger.error(f"Error during crawl and extract process: {str(e)}", exc_info=True)
        return None


def main():
    """Parse command line arguments and run the crawl_and_extract function."""
    parser = argparse.ArgumentParser(description="Crawl and extract product data from e-commerce websites")
    parser.add_argument("url", help="URL of the product page to extract")
    parser.add_argument(
        "--strategy", 
        choices=["auto", "schema", "llm"], 
        default="auto", 
        help="Extraction strategy (default: auto)"
    )
    parser.add_argument(
        "--storage", 
        default="./data",
        help="Path to store extracted data (default: ./data)"
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Use fallback extraction if the primary method fails"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create storage directory if it doesn't exist
        Path(args.storage).mkdir(parents=True, exist_ok=True)
        
        # Run the main function
        product_id = asyncio.run(crawl_and_extract(
            url=args.url,
            extraction_strategy=args.strategy,
            storage_path=args.storage,
            use_fallback=args.fallback
        ))
        
        if not product_id:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 