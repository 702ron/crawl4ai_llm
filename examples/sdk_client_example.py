#!/usr/bin/env python
"""
Example script demonstrating how to use the Crawl4AI LLM Python SDK/client library.

This example shows how to integrate with the Crawl4AI LLM API using the client library
for various operations including product extraction, management, and data export.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path to import from crawl4ai_llm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the client library
from crawl4ai_llm.client import Crawl4AIClient
from crawl4ai_llm.client.models import ExtractionRequest, ProductFilter, ExportFormat


async def extract_product_example(client: Crawl4AIClient) -> str:
    """
    Example of extracting product data from a URL.
    
    Args:
        client: Initialized Crawl4AI client
        
    Returns:
        Product ID of the extracted product
    """
    print("\n=== Extracting Product Data ===\n")
    
    # Create an extraction request
    request = ExtractionRequest(
        url="https://www.amazon.com/dp/B08F7CJQZ3",
        extraction_method="auto",  # Use auto schema generation
        use_fallback=True,  # Fall back to LLM extraction if schema fails
        store_result=True,  # Store the result in the database
        metadata={
            "source": "sdk_example",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Extract the product
    result = await client.extract_product(request)
    
    # Print the result
    print(f"Extraction successful: {result.success}")
    print(f"Product ID: {result.product_id}")
    
    if result.product:
        print(f"Title: {result.product.title}")
        if result.product.price:
            print(f"Price: {result.product.price.current} {result.product.price.currency}")
        print(f"Description length: {len(result.product.description) if result.product.description else 0} chars")
        print(f"Number of images: {len(result.product.images) if result.product.images else 0}")
    
    if result.messages:
        print("\nExtraction messages:")
        for msg in result.messages:
            print(f"- {msg}")
    
    return result.product_id


async def batch_extract_example(client: Crawl4AIClient) -> List[str]:
    """
    Example of batch extracting products from multiple URLs.
    
    Args:
        client: Initialized Crawl4AI client
        
    Returns:
        List of product IDs that were successfully extracted
    """
    print("\n=== Batch Extracting Products ===\n")
    
    # Load URLs from a file
    urls_file = os.path.join(os.path.dirname(__file__), "example_urls.txt")
    
    with open(urls_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"Loaded {len(urls)} URLs for batch extraction")
    
    # Create extraction requests
    requests = [
        ExtractionRequest(
            url=url,
            extraction_method="auto",
            use_fallback=True,
            store_result=True,
            metadata={"source": "batch_example", "timestamp": datetime.now().isoformat()}
        )
        for url in urls
    ]
    
    # Extract products in batch
    results = await client.batch_extract_products(
        requests=requests,
        concurrency=3,  # Process 3 URLs at a time
        fail_fast=False  # Continue on individual failures
    )
    
    # Print results
    successful_ids = []
    print("\nBatch extraction results:")
    for i, result in enumerate(results):
        url = urls[i] if i < len(urls) else "Unknown URL"
        status = "✅ Success" if result.success else "❌ Failed"
        print(f"{status}: {url}")
        
        if result.success and result.product_id:
            successful_ids.append(result.product_id)
    
    print(f"\nSuccessfully extracted {len(successful_ids)} out of {len(urls)} products")
    return successful_ids


async def product_management_example(client: Crawl4AIClient, product_id: str) -> None:
    """
    Example of product management operations (get, update, delete).
    
    Args:
        client: Initialized Crawl4AI client
        product_id: ID of a product to work with
    """
    print("\n=== Product Management Example ===\n")
    
    # Get the product
    print(f"Getting product {product_id}...")
    product = await client.get_product(product_id)
    
    if not product:
        print(f"Product {product_id} not found")
        return
    
    print(f"Retrieved product: {product.title}")
    
    # Update the product (add a tag)
    print("\nUpdating product...")
    current_tags = product.metadata.get("tags", []) if product.metadata else []
    
    if not product.metadata:
        product.metadata = {}
    
    product.metadata["tags"] = list(set(current_tags + ["sdk_example"]))
    product.metadata["last_updated"] = datetime.now().isoformat()
    
    update_success = await client.update_product(product_id, product)
    print(f"Update {'successful' if update_success else 'failed'}")
    
    # Get the updated product
    updated_product = await client.get_product(product_id)
    if updated_product and updated_product.metadata:
        print(f"Updated tags: {updated_product.metadata.get('tags')}")
    
    # We won't delete the product in this example, but here's how you would do it
    # print("\nDeleting product...")
    # delete_success = await client.delete_product(product_id)
    # print(f"Deletion {'successful' if delete_success else 'failed'}")


async def product_search_example(client: Crawl4AIClient) -> None:
    """
    Example of searching and filtering products.
    
    Args:
        client: Initialized Crawl4AI client
    """
    print("\n=== Product Search Example ===\n")
    
    # Create a filter for products
    product_filter = ProductFilter(
        price_min=100,  # Minimum price
        price_max=2000,  # Maximum price
        created_after=datetime.now().replace(year=datetime.now().year - 1),  # Created in the last year
        metadata_filter={"source": "sdk_example"}  # With specific metadata
    )
    
    # Search for products
    search_results = await client.search_products(
        filter=product_filter,
        limit=5,  # Return up to 5 products
        offset=0,  # Start from the beginning
        sort_by="price",  # Sort by price
        sort_order="asc"  # In ascending order
    )
    
    # Print results
    print(f"Found {search_results.total} products matching the filter")
    print(f"Returning {len(search_results.products)} products")
    
    for i, product in enumerate(search_results.products):
        price_str = f"{product.price.current} {product.price.currency}" if product.price else "N/A"
        print(f"{i+1}. {product.title} - {price_str}")


async def export_example(client: Crawl4AIClient, product_ids: List[str]) -> None:
    """
    Example of exporting products to different formats.
    
    Args:
        client: Initialized Crawl4AI client
        product_ids: List of product IDs to export
    """
    print("\n=== Export Example ===\n")
    
    # Export to JSON
    print("Exporting to JSON...")
    json_data = await client.export_products(
        product_ids=product_ids,
        format=ExportFormat.JSON,
        include_metadata=True
    )
    
    json_file = "exported_products.json"
    with open(json_file, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"Exported {len(json_data)} products to {json_file}")
    
    # Export to CSV
    print("\nExporting to CSV...")
    csv_data = await client.export_products(
        product_ids=product_ids,
        format=ExportFormat.CSV,
        flatten=True  # Flatten nested structures for CSV
    )
    
    csv_file = "exported_products.csv"
    with open(csv_file, "w") as f:
        f.write(csv_data)
    print(f"Exported products to {csv_file}")


async def main():
    """Main function to run the examples."""
    # Get API key from environment variable or use a default for demonstration
    api_key = os.environ.get("CRAWL4AI_API_KEY", "your_api_key_here")
    api_url = os.environ.get("CRAWL4AI_API_URL", "http://localhost:8000")
    
    # Initialize the client
    client = Crawl4AIClient(
        api_key=api_key,
        base_url=api_url,
        timeout=60,  # 60 second timeout for API calls
        max_retries=3  # Retry failed API calls up to 3 times
    )
    
    try:
        # Run extract product example
        product_id = await extract_product_example(client)
        
        # Run product management example
        await product_management_example(client, product_id)
        
        # Run batch extract example
        product_ids = await batch_extract_example(client)
        
        # Run product search example
        await product_search_example(client)
        
        # Run export example
        if product_ids:
            await export_example(client, product_ids)
            
    except Exception as e:
        print(f"Error during SDK example: {e}")
    finally:
        # Close the client when done
        await client.close()
        print("\nExamples completed and client closed")


if __name__ == "__main__":
    # Check if the client module exists
    try:
        from crawl4ai_llm.client import Crawl4AIClient
        asyncio.run(main())
    except ImportError:
        print("Error: crawl4ai_llm.client module not found.")
        print("This example requires the SDK/client library to be implemented.")
        print("Please implement the SDK client library as described in the TASK.md file.")
        sys.exit(1) 