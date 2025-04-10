#!/usr/bin/env python
"""
Example script demonstrating how to use the DataProcessor and JSONStorage together.

This script:
1. Extracts product data from a URL
2. Processes the data to clean and normalize it
3. Stores the processed data in a JSON storage
4. Retrieves and displays the stored data
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime

from crawl4ai_llm.config import Config
from crawl4ai_llm.extraction import ProductExtractor
from crawl4ai_llm.processing import DataProcessor
from crawl4ai_llm.storage import JSONStorage


async def main(
    url: str, output_dir: str, extraction_strategy: str = "auto", cleanup: bool = False
):
    """
    Extract, process, and store product data from a URL.

    Args:
        url: URL of the product page to extract from
        output_dir: Directory to store extracted products
        extraction_strategy: Strategy to use for extraction ('auto', 'llm', or 'schema')
        cleanup: Whether to clean up the output directory before starting
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Processing product at URL: {url}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Clean up output directory if requested
    if cleanup and os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            file_path = os.path.join(output_dir, f)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        logger.info(f"Cleaned up output directory: {output_dir}")

    # Initialize components
    config = Config.load_from_env()
    extractor = ProductExtractor(config.crawler, config.llm)
    processor = DataProcessor()
    storage = JSONStorage(output_dir)

    # Extract product data
    logger.info(f"Extracting product data using strategy: {extraction_strategy}")
    try:
        product_data = await extractor.extract(url, strategy=extraction_strategy)
        logger.info(f"Successfully extracted product data: {product_data.title}")
    except Exception as e:
        logger.error(f"Failed to extract product data: {e}")
        return

    # Process the product data
    logger.info("Processing product data")
    try:
        processed_data = processor.process_product_data(product_data)
        logger.info(f"Successfully processed product data")
    except Exception as e:
        logger.error(f"Failed to process product data: {e}")
        return

    # Store the processed data
    logger.info("Storing processed product data")
    try:
        product_id = await storage.save_product(processed_data)
        logger.info(f"Successfully stored product data with ID: {product_id}")
    except Exception as e:
        logger.error(f"Failed to store product data: {e}")
        return

    # Retrieve the stored data
    logger.info(f"Retrieving stored product data with ID: {product_id}")
    try:
        retrieved_data = await storage.get_product(product_id)
        logger.info(f"Successfully retrieved product data")

        # Print summary of product data
        print("\n" + "=" * 50)
        print(f"PRODUCT SUMMARY")
        print("=" * 50)
        print(f"Title: {retrieved_data.title}")
        print(f"Brand: {retrieved_data.brand}")
        print(f"URL: {retrieved_data.url}")

        if retrieved_data.prices:
            print(f"\nPrices:")
            for price in retrieved_data.prices:
                print(f"  - {price.amount} {price.currency}")

        if retrieved_data.attributes:
            print(f"\nAttributes:")
            for attr in retrieved_data.attributes:
                print(f"  - {attr.name}: {attr.value}")
                if hasattr(attr, "standardized_value") and attr.standardized_value:
                    std = attr.standardized_value
                    print(f"    (Standardized: {std.get('value')} {std.get('unit')})")

        # Write a JSON summary to a file
        summary_path = os.path.join(output_dir, f"{product_id}_summary.json")
        with open(summary_path, "w") as f:
            json.dump(
                {
                    "product_id": product_id,
                    "title": retrieved_data.title,
                    "brand": retrieved_data.brand,
                    "url": retrieved_data.url,
                    "extracted_at": retrieved_data.metadata.get("extracted_at"),
                    "processed_at": retrieved_data.metadata.get("processed_at"),
                    "stored_at": retrieved_data.metadata.get("saved_at"),
                },
                f,
                indent=2,
            )

        logger.info(f"Saved summary to {summary_path}")

    except Exception as e:
        logger.error(f"Failed to retrieve product data: {e}")
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract, process, and store product data"
    )
    parser.add_argument("url", help="URL of the product page to extract from")
    parser.add_argument(
        "--output-dir",
        "-o",
        default="./data",
        help="Directory to store extracted products",
    )
    parser.add_argument(
        "--strategy",
        "-s",
        default="auto",
        choices=["auto", "llm", "schema"],
        help="Extraction strategy",
    )
    parser.add_argument(
        "--cleanup",
        "-c",
        action="store_true",
        help="Clean up output directory before starting",
    )

    args = parser.parse_args()

    asyncio.run(main(args.url, args.output_dir, args.strategy, args.cleanup))
