#!/usr/bin/env python
"""
Example script demonstrating how to use content filtering with ProductExtractor.

This example shows how to extract product data from e-commerce websites
using content filtering to improve extraction accuracy.
"""

import asyncio
import json
import logging
from pathlib import Path

from crawl4ai_llm.config import LLMConfig
from crawl4ai_llm.crawler import ContentFilter
from crawl4ai_llm.extraction import ProductExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def extract_products_with_filters():
    """Demonstrate product extraction with content filtering."""
    # URLs to extract from
    urls = [
        "https://www.amazon.com/PlayStation-5-Console-CFI-1000A-01/dp/B08FC5L3RG",
        "https://www.bestbuy.com/site/apple-airpods-pro-2nd-generation-white/4900964.p",
    ]

    # Example 1: Extract without any content filtering
    logger.info("Extracting products without content filtering...")
    extractor = ProductExtractor()

    no_filter_results = {}
    for url in urls:
        try:
            product = await extractor.extract(url, strategy="auto_schema")
            no_filter_results[url] = product.model_dump()
        except Exception as e:
            logger.error(f"Error extracting from {url}: {str(e)}")
            no_filter_results[url] = {"error": str(e)}

    # Example 2: Extract with BM25 content filtering
    logger.info("Extracting products with BM25 content filtering...")
    bm25_filter = ContentFilter(
        filter_type="bm25",
        query="product details specifications features price brand images",
        threshold=0.5,
    )

    extractor_with_filter = ProductExtractor(content_filters=[bm25_filter])

    bm25_filter_results = {}
    for url in urls:
        try:
            product = await extractor_with_filter.extract(url, strategy="auto_schema")
            bm25_filter_results[url] = product.model_dump()
        except Exception as e:
            logger.error(f"Error extracting from {url} with BM25 filter: {str(e)}")
            bm25_filter_results[url] = {"error": str(e)}

    # Example 3: Extract with one-time content filter
    logger.info("Extracting products with one-time pruning filter...")
    pruning_filter = ContentFilter(filter_type="pruning", threshold=0.4)

    one_time_filter_results = {}
    for url in urls:
        try:
            # Pass the filter as a parameter for one-time use
            product = await extractor.extract(
                url, strategy="auto_schema", content_filters=[pruning_filter]
            )
            one_time_filter_results[url] = product.model_dump()
        except Exception as e:
            logger.error(f"Error extracting from {url} with pruning filter: {str(e)}")
            one_time_filter_results[url] = {"error": str(e)}

    # Example 4: Extract with LLM extraction strategy and content filtering
    logger.info("Extracting products with LLM strategy and content filtering...")
    llm_with_filter_results = {}
    for url in urls:
        try:
            # Use LLM strategy with BM25 filter
            product = await extractor_with_filter.extract(url, strategy="llm")
            llm_with_filter_results[url] = product.model_dump()
        except Exception as e:
            logger.error(f"Error extracting from {url} with LLM strategy: {str(e)}")
            llm_with_filter_results[url] = {"error": str(e)}

    # Save results to output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "no_filter_results.json", "w") as f:
        json.dump(no_filter_results, f, indent=2, default=str)

    with open(output_dir / "bm25_filter_results.json", "w") as f:
        json.dump(bm25_filter_results, f, indent=2, default=str)

    with open(output_dir / "one_time_filter_results.json", "w") as f:
        json.dump(one_time_filter_results, f, indent=2, default=str)

    with open(output_dir / "llm_with_filter_results.json", "w") as f:
        json.dump(llm_with_filter_results, f, indent=2, default=str)

    # Compare the results
    logger.info(f"Results saved to {output_dir.absolute()}")
    logger.info("Comparing extraction results with different filtering strategies...")

    for url in urls:
        product_name_no_filter = no_filter_results[url].get("title", "Unknown")
        product_name_bm25 = bm25_filter_results[url].get("title", "Unknown")
        product_name_pruning = one_time_filter_results[url].get("title", "Unknown")
        product_name_llm = llm_with_filter_results[url].get("title", "Unknown")

        logger.info(f"\nProduct from {url}:")
        logger.info(f"  No filtering: {product_name_no_filter}")
        logger.info(f"  BM25 filter: {product_name_bm25}")
        logger.info(f"  Pruning filter: {product_name_pruning}")
        logger.info(f"  LLM with filtering: {product_name_llm}")


if __name__ == "__main__":
    asyncio.run(extract_products_with_filters())
