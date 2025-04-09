#!/usr/bin/env python
"""
Example script demonstrating product extraction with content filtering.

This example shows how to use content filters to improve extraction quality
by filtering out irrelevant content before processing.
"""

import asyncio
import json
import logging
from datetime import datetime

from crawl4ai_llm.extraction.product_extractor import ProductExtractor
from crawl4ai_llm.crawler.content_filter import ContentFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    # Example product URLs
    urls = [
        "https://www.example.com/product1",  # Replace with actual product URLs
        "https://www.example.com/product2",
    ]
    
    # Create content filters for extraction
    # BM25 filter to focus on product-related content
    product_filter = ContentFilter(
        filter_type="bm25",
        query="product details price specifications features",
        threshold=0.3
    )
    
    # Optional LLM filter for more precise filtering
    llm_filter = ContentFilter(
        filter_type="llm",
        instruction="Extract only the main product information including title, price, description, and specifications. Ignore navigation, footer, and unrelated content.",
        threshold=0.5
    )
    
    # Create product extractor with content filters
    extractor = ProductExtractor(content_filters=[product_filter])
    
    # Extract products with different strategies
    results = []
    
    for url in urls:
        logger.info(f"Extracting product from {url}")
        
        # Method 1: Using auto schema with content filtering
        logger.info("Method 1: Auto schema extraction with content filtering")
        result1 = await extractor.extract(url, strategy="auto_schema")
        logger.info(f"Result: {'Success' if result1.extraction_success else 'Failed'}")
        results.append({
            "url": url,
            "method": "auto_schema_with_filtering",
            "result": json.loads(result1.model_dump_json())
        })
        
        # Method 2: Using LLM extraction with content filtering
        logger.info("Method 2: LLM extraction with content filtering")
        result2 = await extractor.extract(url, strategy="llm")
        logger.info(f"Result: {'Success' if result2.extraction_success else 'Failed'}")
        results.append({
            "url": url,
            "method": "llm_with_filtering",
            "result": json.loads(result2.model_dump_json())
        })
        
        # Method 3: Using auto schema with additional LLM filtering for this specific extraction
        logger.info("Method 3: Auto schema with additional LLM filtering")
        result3 = await extractor.extract(
            url, 
            strategy="auto_schema",
            content_filters=[product_filter, llm_filter]
        )
        logger.info(f"Result: {'Success' if result3.extraction_success else 'Failed'}")
        results.append({
            "url": url,
            "method": "auto_schema_with_additional_filtering",
            "result": json.loads(result3.model_dump_json())
        })
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"extraction_results_{timestamp}.json"
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main()) 