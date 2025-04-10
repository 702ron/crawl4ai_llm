# Crawl4AI LLM Client Library

This library provides a Python interface to interact with the Crawl4AI LLM API for product extraction, management, and data export operations.

## Installation

```bash
pip install crawl4ai_llm
```

## Features

- **Product Extraction**: Extract structured product data from e-commerce websites
- **Batch Processing**: Extract data from multiple URLs simultaneously
- **Product Management**: Get, update, and delete products
- **Search and Filtering**: Search for products with customizable filters
- **Data Export**: Export products in JSON or CSV formats
- **Schema Generation**: Generate extraction schemas for websites
- **Dual APIs**: Both asynchronous and synchronous interfaces

## Quick Start

### Asynchronous API

```python
import asyncio
from crawl4ai_llm.client import Crawl4AIClient, ExtractionRequest

async def extract_product():
    # Initialize the client
    client = Crawl4AIClient(api_key="your_api_key")

    # Create extraction request
    request = ExtractionRequest(
        url="https://www.amazon.com/dp/B08F7CJQZ3",
        extraction_method="hybrid"
    )

    # Extract product
    result = await client.extract_product(request)

    # Process the result
    if result.success:
        print(f"Extracted: {result.product.title}")
        print(f"Price: {result.product.price.current_price} {result.product.price.currency}")
    else:
        print(f"Extraction failed: {result.error}")

    # Close the client when done
    await client.close()

# Run the async function
asyncio.run(extract_product())
```

### Synchronous API

```python
from crawl4ai_llm.client import Crawl4AIClient, ExtractionRequest

# Initialize the client
client = Crawl4AIClient(api_key="your_api_key")

# Create extraction request
request = ExtractionRequest(url="https://www.amazon.com/dp/B08F7CJQZ3")

# Extract product (synchronously)
result = client.extract_product_sync(request)

# Process the result
if result.success:
    print(f"Extracted: {result.product.title}")
    print(f"Price: {result.product.price.current_price} {result.product.price.currency}")
else:
    print(f"Extraction failed: {result.error}")

# Close the client when done
client.close_sync()
```

## Product Extraction

Extract structured product data from e-commerce URLs:

```python
# Async API
async def extract_product():
    client = Crawl4AIClient(api_key="your_api_key")

    request = ExtractionRequest(
        url="https://www.amazon.com/dp/B08F7CJQZ3",
        extraction_method="hybrid",  # Options: "auto", "schema", "llm", "hybrid"
        use_fallback=True,           # Use fallback method if primary fails
        store_result=True,           # Store extracted product in database
        metadata={"source": "example"}  # Custom metadata
    )

    result = await client.extract_product(request)

    if result.success:
        print(f"Product ID: {result.product_id}")
        print(f"Title: {result.product.title}")
        print(f"Brand: {result.product.brand}")
        print(f"Price: {result.product.price.current_price} {result.product.price.currency}")
        print(f"Extraction time: {result.extraction_time}ms")

    await client.close()

# Sync API
def extract_product_sync():
    client = Crawl4AIClient(api_key="your_api_key")

    request = ExtractionRequest(
        url="https://www.amazon.com/dp/B08F7CJQZ3",
        extraction_method="hybrid"
    )

    result = client.extract_product_sync(request)

    if result.success:
        print(f"Product ID: {result.product_id}")
        print(f"Title: {result.product.title}")

    client.close_sync()
```

## Batch Extraction

Extract product data from multiple URLs simultaneously:

```python
# Async API
async def batch_extract():
    client = Crawl4AIClient(api_key="your_api_key")

    urls = [
        "https://www.amazon.com/dp/B08F7CJQZ3",
        "https://www.bestbuy.com/site/apple-airpods-pro-white/5706659.p",
        "https://www.walmart.com/ip/Apple-AirPods-with-Charging-Case/715570211"
    ]

    requests = [ExtractionRequest(url=url, store_result=True) for url in urls]

    # Extract with concurrency limit
    result = await client.batch_extract_products(requests, concurrency=3)

    print(f"Successfully extracted {result.successful_count} out of {len(urls)} products")
    print(f"Failed extractions: {result.failed_count}")

    # Access individual results
    for item in result.results:
        if item.success:
            print(f"Extracted: {item.product.title}")
        else:
            print(f"Failed to extract from {item.url}: {item.error}")

    await client.close()

# Sync API
def batch_extract_sync():
    client = Crawl4AIClient(api_key="your_api_key")

    urls = [
        "https://www.amazon.com/dp/B08F7CJQZ3",
        "https://www.bestbuy.com/site/apple-airpods-pro-white/5706659.p"
    ]

    requests = [ExtractionRequest(url=url) for url in urls]

    # Extract with concurrency limit
    result = client.batch_extract_products_sync(requests, concurrency=2)

    print(f"Successfully extracted {result.successful_count} products")

    client.close_sync()
```

## Product Management

Manage extracted products:

```python
# Async API
async def manage_products():
    client = Crawl4AIClient(api_key="your_api_key")

    # Get a product by ID
    product = await client.get_product("product_id_here")

    if product:
        print(f"Retrieved product: {product.title}")

        # Update product data
        product.metadata = {"updated": True, "timestamp": "2023-05-15T14:30:00Z"}
        update_success = await client.update_product("product_id_here", product)

        if update_success:
            print("Product updated successfully")

        # Delete a product
        delete_success = await client.delete_product("product_id_here")

        if delete_success:
            print("Product deleted successfully")

    await client.close()

# Sync API
def manage_products_sync():
    client = Crawl4AIClient(api_key="your_api_key")

    # Get a product by ID
    product = client.get_product_sync("product_id_here")

    if product:
        print(f"Retrieved product: {product.title}")

        # Update product data
        product.metadata = {"updated": True}
        update_success = client.update_product_sync("product_id_here", product)

        # Delete a product
        delete_success = client.delete_product_sync("product_id_here")

    client.close_sync()
```

## Searching Products

Search for products using filters:

```python
# Async API
async def search_products():
    client = Crawl4AIClient(api_key="your_api_key")

    # Create search filter
    filter = {
        "brand": "Apple",
        "price_min": 100,
        "price_max": 500,
        "created_after": "2023-01-01T00:00:00Z",
        "metadata_filter": {"source": "example"}
    }

    # Search with pagination and sorting
    search_result = await client.search_products(
        filter=filter,
        limit=10,
        offset=0,
        sort_by="price",
        sort_order="asc"
    )

    print(f"Found {search_result.total} matching products")

    # Display products
    for product in search_result.products:
        print(f"{product.title} - ${product.price.current_price}")

    await client.close()

# Sync API
def search_products_sync():
    client = Crawl4AIClient(api_key="your_api_key")

    # Create search filter
    filter = {"brand": "Apple", "price_min": 100}

    # Search with pagination
    search_result = client.search_products_sync(filter=filter, limit=10)

    print(f"Found {search_result.total} matching products")

    client.close_sync()
```

## Exporting Products

Export products in different formats:

```python
# Async API
async def export_products():
    client = Crawl4AIClient(api_key="your_api_key")

    # Export to JSON
    json_data = await client.export_products(
        format="json",
        filter={"brand": "Apple"},
        pretty=True,
        include_metadata=True
    )

    # Save to file
    with open("products.json", "w") as f:
        f.write(json_data)

    # Export to CSV
    csv_data = await client.export_products(
        format="csv",
        product_ids=["id1", "id2", "id3"],
        flatten=True
    )

    # Save to file
    with open("products.csv", "w") as f:
        f.write(csv_data)

    await client.close()

# Sync API
def export_products_sync():
    client = Crawl4AIClient(api_key="your_api_key")

    # Export to JSON
    json_data = client.export_products_sync(
        format="json",
        filter={"brand": "Apple"}
    )

    # Export to CSV
    csv_data = client.export_products_sync(
        format="csv",
        product_ids=["id1", "id2"]
    )

    client.close_sync()
```

## Schema Generation

Generate extraction schemas for websites:

```python
# Async API
async def generate_schema():
    client = Crawl4AIClient(api_key="your_api_key")

    # Generate schema for a website
    schema = await client.generate_schema("https://www.amazon.com/dp/B08F7CJQZ3")

    print("Generated Schema:")
    print(schema)

    await client.close()

# Sync API
def generate_schema_sync():
    client = Crawl4AIClient(api_key="your_api_key")

    # Generate schema for a website
    schema = client.generate_schema_sync("https://www.amazon.com/dp/B08F7CJQZ3")

    print("Generated Schema:")
    print(schema)

    client.close_sync()
```

## Error Handling

Handle API errors:

```python
from crawl4ai_llm.client.exceptions import APIError, RequestError

async def error_handling():
    client = Crawl4AIClient(api_key="your_api_key")

    try:
        result = await client.extract_product(
            ExtractionRequest(url="https://invalid-url.example")
        )

        if not result.success:
            print(f"Extraction failed: {result.error}")

    except APIError as e:
        print(f"API Error: {e.status} - {e.message}")

    except RequestError as e:
        print(f"Request Error: {e}")

    finally:
        await client.close()
```

## Configuration Options

The client can be configured with various options:

```python
client = Crawl4AIClient(
    api_key="your_api_key",          # Required
    base_url="https://api.crawl4ai.com",  # Custom API URL (optional)
    timeout=60,                       # Request timeout in seconds
    max_retries=3,                    # Max retry attempts on failures
    retry_delay=2                     # Delay between retries in seconds
)
```

## Using with Context Managers

For better resource management, use the client as an async context manager:

```python
async def with_context_manager():
    async with Crawl4AIClient(api_key="your_api_key") as client:
        request = ExtractionRequest(url="https://www.amazon.com/dp/B08F7CJQZ3")
        result = await client.extract_product(request)

        if result.success:
            print(f"Extracted: {result.product.title}")
```

## Support

For issues, feature requests, or questions, please file an issue on GitHub:
https://github.com/your-username/crawl4ai_llm/issues
