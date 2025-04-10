# Crawl4AI SDK

A Python SDK for extracting, managing, and searching product data using the Crawl4AI product extraction service.

## Installation

```bash
pip install crawl4ai
```

## Quick Start

```python
import asyncio
from crawl4ai import Crawl4AIClient, ExtractionRequest

async def main():
    # Initialize client with your API key
    client = Crawl4AIClient(
        api_key="your_api_key_here",
        base_url="https://api.crawl4ai.com"  # or your custom API endpoint
    )

    try:
        # Extract product data from a URL
        request = ExtractionRequest(
            url="https://www.amazon.com/dp/B08F7CJQZ3",
            extraction_method="auto",
            use_fallback=True
        )

        result = await client.extract_product(request)

        if result.success and result.product:
            print(f"Product: {result.product.title}")
            if result.product.price:
                print(f"Price: {result.product.price.current} {result.product.price.currency}")
            print(f"Description length: {len(result.product.description or '')}")

        else:
            print(f"Extraction failed: {result.error}")

    finally:
        # Always close the client when done
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Features

- **Product Extraction**: Extract product data from any e-commerce website
- **Batch Extraction**: Process multiple URLs concurrently
- **Product Management**: Save, retrieve, update, and delete products
- **Search & Filtering**: Find products based on various criteria
- **Data Export**: Export product data to JSON or CSV formats
- **Schema Generation**: Automatically generate extraction schemas

## Usage Examples

### Batch Extraction

```python
import asyncio
from crawl4ai import Crawl4AIClient, ExtractionRequest

async def batch_extract(urls):
    client = Crawl4AIClient(api_key="your_api_key_here")

    try:
        # Create extraction requests for each URL
        requests = [
            ExtractionRequest(url=url, extraction_method="auto")
            for url in urls
        ]

        # Extract products in parallel (5 at a time)
        batch_result = await client.batch_extract_products(
            requests=requests,
            concurrency=5
        )

        print(f"Successfully extracted: {batch_result.successful_count}/{len(requests)}")
        print(f"Total time: {batch_result.total_time:.2f} seconds")

        # Process the results
        for result in batch_result.results:
            if result.success and result.product:
                print(f"Extracted: {result.product.title}")

    finally:
        await client.close()

# Example usage
urls = [
    "https://www.amazon.com/dp/B08F7CJQZ3",
    "https://www.walmart.com/ip/123456789",
    "https://www.bestbuy.com/site/12345"
]

asyncio.run(batch_extract(urls))
```

### Searching Products

```python
import asyncio
from datetime import datetime, timedelta
from crawl4ai import Crawl4AIClient, ProductFilter

async def search_products():
    client = Crawl4AIClient(api_key="your_api_key_here")

    try:
        # Create a filter for products
        product_filter = ProductFilter(
            price_min=100,
            price_max=500,
            created_after=datetime.now() - timedelta(days=7),
            metadata_filter={"category": "electronics"}
        )

        # Search for products
        results = await client.search_products(
            filter=product_filter,
            limit=10,
            sort_by="price",
            sort_order="asc"
        )

        print(f"Found {results.total} products")

        # Process search results
        for product in results.products:
            price_str = f"{product.price.current} {product.price.currency}" if product.price else "N/A"
            print(f"{product.title} - {price_str}")

    finally:
        await client.close()

asyncio.run(search_products())
```

### Exporting Products

```python
import asyncio
import json
from crawl4ai import Crawl4AIClient, ExportFormat, ProductFilter

async def export_products():
    client = Crawl4AIClient(api_key="your_api_key_here")

    try:
        # Export products to JSON
        json_data = await client.export_products(
            filter=ProductFilter(brand="Apple"),
            format=ExportFormat.JSON,
            include_metadata=True
        )

        # Save to file
        with open("products.json", "w") as f:
            json.dump(json_data, f, indent=2)

        # Export products to CSV with flattened structure
        csv_data = await client.export_products(
            filter=ProductFilter(brand="Apple"),
            format=ExportFormat.CSV,
            flatten=True
        )

        # Save to file
        with open("products.csv", "w") as f:
            f.write(csv_data)

    finally:
        await client.close()

asyncio.run(export_products())
```

## API Reference

For detailed API documentation, please visit [https://docs.crawl4ai.com/sdk](https://docs.crawl4ai.com/sdk).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
