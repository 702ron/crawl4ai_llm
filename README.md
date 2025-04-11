# Crawl4AI LLM

A Python library for extracting structured product data from e-commerce websites using Large Language Models (LLMs).

## Features

- **🔍 Smart Product Extraction**: Extract product data from any e-commerce website using hybrid extraction techniques
- **🤖 LLM-Powered**: Leverages LLMs for accurate extraction and schema generation
- **🏗️ Flexible Extraction Strategies**: Schema-based, LLM-based, or hybrid approaches
- **🔄 Content Filtering**: Advanced content filtering for targeted extraction
- **💾 Storage Layer**: Built-in storage system with JSON file storage
- **🔌 REST API**: Full-featured REST API for integration with other systems
- **📦 SDK/Client Library**: Python client library for easy integration
- **⚡ Batch Processing**: Efficient batch extraction and storage operations
- **🧪 Validation & Cleaning**: Built-in data validation and cleaning pipelines
- **🎯 Multiple Extraction Methods**: CSS selectors, XPath expressions, and hybrid approaches for precise data extraction
- **🌐 JavaScript Rendering**: Support for JavaScript-rendered content using Playwright
- **🔁 Retry Mechanism**: Robust retry with exponential backoff for handling transient failures

## Installation

```bash
pip install crawl4ai-llm
```

## Quick Start

```python
import asyncio
from crawl4ai_llm import extract_product

async def main():
    product = await extract_product("https://www.amazon.com/dp/B08F7CJQZ3")
    print(f"Extracted: {product.title}")
    print(f"Price: {product.price.value} {product.price.currency}")
    print(f"Brand: {product.brand}")

asyncio.run(main())
```

## Extraction Strategies

The library supports multiple extraction strategies:

- **Schema-based**: Generate and use extraction schemas
- **LLM-based**: Direct extraction using LLM capabilities
- **CSS-based**: Extract data using CSS selectors
- **XPath-based**: Extract data using XPath expressions
- **Hybrid**: Combine multiple extraction methods with intelligent fallbacks

```python
from crawl4ai_llm import ProductExtractor, CSSExtractor, XPathExtractor, HybridExtractor

# Schema-based extraction
product_extractor = ProductExtractor()
product = await product_extractor.extract(url, strategy="schema")

# CSS selector extraction
css_extractor = CSSExtractor()
css_selectors = {
    "title": {"selector": "h1.product-title", "attribute": "text"},
    "price": {"selector": ".product-price", "attribute": "text"},
    "description": {"selector": ".product-description", "attribute": "text"},
}
product = await css_extractor.extract_with_css(url, selectors=css_selectors)

# XPath extraction
xpath_extractor = XPathExtractor()
xpath_expressions = {
    "title": {"xpath": "//h1"},
    "price": {"xpath": "//*[contains(@class, 'price')]"},
    "description": {"xpath": "//*[contains(@class, 'description')]"},
}
product = await xpath_extractor.extract_with_xpath(url, xpath_expressions=xpath_expressions)

# Hybrid extraction (combines CSS, XPath, auto-schema, and LLM)
hybrid_extractor = HybridExtractor()
product = await hybrid_extractor.extract_with_hybrid(
    url,
    css_selectors=css_selectors,
    xpath_expressions=xpath_expressions,
    use_auto_schema=True,
    use_fallback_llm=True
)
```

## Storage

The library includes a storage layer for product data:

```python
from crawl4ai_llm.storage import get_storage

# Get the storage instance
storage = get_storage()

# Save a product
product_id = await storage.save_product(product_data)

# Get a product
product = await storage.get_product(product_id)

# Batch operations
product_ids = await storage.save_products([product1, product2, product3])
```

## Batch Operations

For efficient processing of multiple products:

```python
# Batch extraction
urls = ["https://example.com/product1", "https://example.com/product2"]
results = await extractor.batch_extract(urls, concurrency=2)

# Batch storage
storage = get_storage()
with await storage.transaction():
    for product in products:
        await storage.save_product(product)
```

## Content Filtering

Advanced content filtering for targeted extraction:

```python
from crawl4ai_llm.extraction.content_filter import CSSFilter, XPathFilter

# CSS selector filtering
css_filter = CSSFilter(selector="div.product-details")
product_details = css_filter.apply(html_content)

# XPath filtering
xpath_filter = XPathFilter(xpath="//div[@class='product-specs']/ul/li")
specs = xpath_filter.apply(html_content)

# Chain filters
filtered_content = (
    CSSFilter(selector="div.product-details")
    .chain(XPathFilter(xpath="//div[@class='specs']"))
    .apply(html_content)
)
```

## REST API

The library includes a REST API for integration with other systems:

```bash
# Start the API server
python -m crawl4ai_llm.api --port 8000
```

Use the API to extract products:

```bash
curl -X POST http://localhost:8000/extract \
    -H "Authorization: Bearer your_api_key" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://www.amazon.com/dp/B08F7CJQZ3", "strategy": "auto"}'
```

## SDK/Client Library

The library includes a Python client for easy integration:

```python
from crawl4ai_llm.client import Crawl4AIClient, ExtractionRequest

# Asynchronous API
async def extract_product():
    client = Crawl4AIClient(api_key="your_api_key")

    request = ExtractionRequest(
        url="https://www.amazon.com/dp/B08F7CJQZ3",
        extraction_method="hybrid"
    )

    result = await client.extract_product(request)

    if result.success:
        print(f"Title: {result.product.title}")
        print(f"Price: {result.product.price.current} {result.product.price.currency}")

    await client.close()

# Synchronous API
def extract_product_sync():
    client = Crawl4AIClient(api_key="your_api_key")

    request = ExtractionRequest(url="https://www.amazon.com/dp/B08F7CJQZ3")
    result = client.extract_product_sync(request)

    if result.success:
        print(f"Title: {result.product.title}")

    client.close_sync()
```

The SDK provides comprehensive functionality:

- Product extraction (single and batch)
- Product management (get, update, delete)
- Search and filtering
- Data export (JSON, CSV)
- Schema generation

## Examples

Check the `examples` directory for more usage examples:

- `basic_extraction_example.py`: Simple product extraction
- `batch_extraction_example.py`: Extract multiple products
- `storage_example.py`: Working with the storage layer
- `content_filter_example.py`: Content filtering examples
- `sdk_client_example.py`: Using the SDK/client library
- `transaction_example.py`: Using transactions for atomic operations
- `js_rendering_example.py`: Demonstrating JavaScript rendering capabilities
- `retry_mechanism_example.py`: Handling failed requests with retry mechanism

## Configuration

Configure the library using environment variables or a config file:

```python
from crawl4ai_llm.config import get_config

config = get_config()
print(f"Storage type: {config.storage.type}")
print(f"LLM provider: {config.llm.provider}")
```

Environment variables:

```bash
export CRAWL4AI_LLM_PROVIDER=openai
export CRAWL4AI_OPENAI_API_KEY=your_api_key
export CRAWL4AI_STORAGE_TYPE=json
export CRAWL4AI_STORAGE_PATH=/path/to/storage
```

## Documentation

### Core Components

- **Extractor**: Primary interface for extracting product data
- **Schema**: Define data extraction format and rules
- **Storage**: Store extracted data with validation
- **Content Filter**: Filter content for targeted extraction
- **Client**: SDK for integration with other systems
- **REST API**: HTTP interface for the library
- **Batch Processor**: Batch operations for efficiency
- **Renderer**: JavaScript rendering for dynamic sites
- **Retry Handler**: Robust request retry mechanism with backoff

For detailed documentation, refer to the [docs](docs/) directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
