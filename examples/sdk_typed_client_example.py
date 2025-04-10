#!/usr/bin/env python
"""
Example script demonstrating how to use the Crawl4AI SDK with proper type hints.

This example shows how to integrate with the Crawl4AI SDK using static typing
to improve code quality and IDE auto-completion.
"""

import asyncio
import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import sys
# Add parent directory to path to import the SDK
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai_sdk.crawl4ai import (
    Crawl4AIClient, 
    ExtractionRequest, 
    ExtractionMethod, 
    ProductFilter,
    ExportFormat,
    ProductData
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def extract_single_product(client: Crawl4AIClient, url: str) -> Optional[ProductData]:
    """
    Extract a single product from a URL.
    
    Args:
        client: Initialized Crawl4AI client
        url: URL of the product to extract
        
    Returns:
        Extracted ProductData if successful, None otherwise
    """
    logger.info(f"Extracting product from: {url}")
    
    # Create an extraction request
    request = ExtractionRequest(
        url=url,
        extraction_method=ExtractionMethod.AUTO,
        use_fallback=True,
        store_result=True,
        metadata={
            "source": "sdk_typed_example",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Extract the product
    result = await client.extract_product(request)
    
    if result.success and result.product:
        logger.info(f"Successfully extracted: {result.product.title}")
        return result.product
    else:
        logger.error(f"Extraction failed: {result.error}")
        return None


async def batch_extract(client: Crawl4AIClient, urls: List[str]) -> List[ProductData]:
    """
    Extract multiple products in batch.
    
    Args:
        client: Initialized Crawl4AI client
        urls: List of URLs to extract
        
    Returns:
        List of successfully extracted products
    """
    logger.info(f"Batch extracting {len(urls)} products")
    
    # Create extraction requests
    requests = [
        ExtractionRequest(
            url=url,
            extraction_method=ExtractionMethod.AUTO,
            use_fallback=True,
            store_result=True,
            metadata={"source": "sdk_typed_batch_example"}
        )
        for url in urls
    ]
    
    # Extract products in batch
    result = await client.batch_extract_products(
        requests=requests,
        concurrency=3,  # Process 3 URLs at a time
        fail_fast=False  # Continue on individual failures
    )
    
    logger.info(f"Batch extraction completed in {result.total_time:.2f}s")
    logger.info(f"Successful: {result.successful_count}, Failed: {result.failed_count}")
    
    # Return successful extractions
    return [
        r.product for r in result.results 
        if r.success and r.product is not None
    ]


async def search_products_example(client: Crawl4AIClient) -> None:
    """
    Demonstrate product search functionality.
    
    Args:
        client: Initialized Crawl4AI client
    """
    logger.info("Searching for products")
    
    # Create filter for products created in the last week
    one_week_ago = datetime.now() - timedelta(days=7)
    
    product_filter = ProductFilter(
        price_min=50.0,  # Minimum price
        price_max=500.0,  # Maximum price
        created_after=one_week_ago,
        brand="Apple",  # Filter by brand
        metadata_filter={"source": "sdk_typed_example"}  # Filter by metadata
    )
    
    # Search for products
    search_results = await client.search_products(
        filter=product_filter,
        limit=10,
        offset=0,
        sort_by="price",  # Sort by price
        sort_order="asc"  # In ascending order
    )
    
    logger.info(f"Found {search_results.total} matching products")
    
    # Display results
    for i, product in enumerate(search_results.products):
        price_str = f"{product.price.current} {product.price.currency}" if product.price else "N/A"
        logger.info(f"{i+1}. {product.title} - {price_str}")


async def export_products_example(client: Crawl4AIClient, products: List[ProductData]) -> None:
    """
    Demonstrate product export functionality.
    
    Args:
        client: Initialized Crawl4AI client
        products: List of products to export
    """
    if not products:
        logger.warning("No products to export")
        return
    
    logger.info(f"Exporting {len(products)} products")
    
    # Get product IDs if available
    product_ids = [p.metadata.get("product_id") for p in products if p.metadata and "product_id" in p.metadata]
    
    # Export to JSON
    if product_ids:
        json_data = await client.export_products(
            product_ids=product_ids,
            format=ExportFormat.JSON,
            include_metadata=True
        )
        
        output_file = "exported_products.json"
        with open(output_file, "w") as f:
            json.dump(json_data, f, indent=2)
        
        logger.info(f"Exported {len(json_data)} products to {output_file}")
    
    # Export to CSV (all products from the last week)
    one_week_ago = datetime.now() - timedelta(days=7)
    
    csv_data = await client.export_products(
        filter=ProductFilter(created_after=one_week_ago),
        format=ExportFormat.CSV,
        flatten=True  # Flatten nested structures for CSV
    )
    
    output_file = "exported_products.csv"
    with open(output_file, "w") as f:
        f.write(csv_data)
    
    logger.info(f"Exported recent products to {output_file}")


async def main() -> None:
    """Main function to run the examples."""
    # Get API key from environment variable or use a default for demonstration
    api_key = os.environ.get("CRAWL4AI_API_KEY", "your_api_key_here")
    api_url = os.environ.get("CRAWL4AI_API_URL", "http://localhost:8000")
    
    logger.info("Initializing Crawl4AI SDK client")
    
    # Initialize the client with type hints
    client = Crawl4AIClient(
        api_key=api_key,
        base_url=api_url,
        timeout=60.0,
        max_retries=3
    )
    
    try:
        # Example URLs to process
        test_url = "https://www.amazon.com/dp/B08F7CJQZ3"
        batch_urls = [
            "https://www.amazon.com/dp/B08XVYZ1Y5",
            "https://www.amazon.com/dp/B08XY3R124",
            "https://www.walmart.com/ip/443574645",
        ]
        
        # Extract single product
        product = await extract_single_product(client, test_url)
        
        # Extract batch of products
        products = await batch_extract(client, batch_urls)
        
        # Search for products
        await search_products_example(client)
        
        # Export products
        all_products = []
        if product:
            all_products.append(product)
        all_products.extend(products)
        
        await export_products_example(client, all_products)
        
    except Exception as e:
        logger.exception(f"Error during SDK example: {e}")
    finally:
        # Always close the client when done
        await client.close()
        logger.info("Client closed")


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main()) 