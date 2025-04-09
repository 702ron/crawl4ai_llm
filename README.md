# Crawl4AI LLM

A powerful e-commerce product extraction library that uses LLM-based techniques to extract structured product data from any e-commerce website.

## Features

- **Flexible Crawling**: Built-in crawler with session management and rate limiting
- **Content Filtering**: Intelligent filtering of web content using BM25, pruning, or LLM-based strategies
- **Automated Schema Generation**: Dynamically generates extraction schemas based on website content
- **LLM-Based Extraction**: Uses large language models to extract structured product data
- **Configurable Storage**: Support for multiple storage backends with batch operations
- **Command-Line Interface**: Extract products directly from the command line
- **Lightweight**: Minimal dependencies, focused on core functionality

## Installation

```bash
pip install crawl4ai_llm
```

Or from source:

```bash
git clone https://github.com/username/crawl4ai_llm.git
cd crawl4ai_llm
pip install -e .
```

## Quick Start

### Command-Line Usage

Extract product data from an e-commerce URL:

```bash
python -m crawl4ai_llm "https://example-shop.com/products/product-123" --output product.json
```

### Python API

```python
import asyncio
from crawl4ai_llm.extraction import ProductExtractor
from crawl4ai_llm.config import AppConfig, LLMConfig, CrawlerConfig, StorageConfig

async def extract_product():
    # Configure the extractor
    config = AppConfig(
        llm=LLMConfig(
            provider="openai",
            model_name="gpt-3.5-turbo",
            api_key="your-api-key"
        ),
        crawler=CrawlerConfig(
            user_agent="Mozilla/5.0",
            timeout=30,
            max_retries=3
        ),
        storage=StorageConfig(
            type="json",
            path="./data",
            use_uuid=True
        )
    )

    # Create extractor instance
    extractor = ProductExtractor(config=config)

    # Extract product data
    product_url = "https://example-shop.com/products/product-123"
    product_data = await extractor.extract(product_url)

    print(f"Extracted product: {product_data.title}")
    print(f"Price: {product_data.price.current} {product_data.price.currency}")
    print(f"Description: {product_data.description[:100]}...")

    # Save to storage
    product_id = await extractor.storage.save_product(product_data)
    print(f"Saved product with ID: {product_id}")

if __name__ == "__main__":
    asyncio.run(extract_product())
```

## Batch Storage Operations

The library supports batch operations for efficient handling of multiple products:

```python
import asyncio
from crawl4ai_llm.storage import get_storage
from crawl4ai_llm.config import StorageConfig

async def batch_operations_example():
    # Configure storage
    storage_config = StorageConfig(
        type="json",
        path="./data",
        use_uuid=True
    )
    storage = get_storage(storage_config)

    # Batch save multiple products
    products = [product1, product2, product3, product4, product5]
    product_ids = await storage.save_products(products)
    print(f"Saved {len(product_ids)} products with IDs: {product_ids}")

    # Batch retrieve multiple products
    products_dict = await storage.get_products(product_ids)
    print(f"Retrieved {len(products_dict)} products")

    # Batch update multiple products
    updates = {
        product_ids[0]: updated_product1,
        product_ids[1]: updated_product2
    }
    update_results = await storage.update_products(updates)
    print(f"Updated {sum(update_results.values())} products successfully")

    # Batch delete multiple products
    delete_results = await storage.delete_products(product_ids[2:4])
    print(f"Deleted {sum(delete_results.values())} products successfully")

    # List remaining products
    products_list, total_count = await storage.list_products()
    print(f"Remaining products: {total_count}")

if __name__ == "__main__":
    asyncio.run(batch_operations_example())
```

## Content Filtering

The library supports intelligent content filtering to improve extraction accuracy:

```python
from crawl4ai_llm.crawler import BaseCrawler, ContentFilter
from crawl4ai_llm.config import LLMConfig

# BM25-based filtering (keyword-based relevance)
bm25_filter = ContentFilter(
    filter_type="bm25",
    query="product details specifications features price",
    threshold=0.5  # Minimum relevance score
)

# Pruning-based filtering (structural and semantic analysis)
pruning_filter = ContentFilter(
    filter_type="pruning",
    threshold=0.4  # Minimum content quality score
)

# LLM-based filtering (high-quality content extraction)
llm_config = LLMConfig(
    provider="openai",
    api_token="your-api-key",
    model="gpt-3.5-turbo"
)
llm_filter = ContentFilter(
    filter_type="llm",
    llm_config=llm_config,
    instruction="Extract the main product information, including name, price, features, and specifications."
)

# CSS Selector filtering (DOM-based content extraction)
css_filter = ContentFilter(
    filter_type="css",
    selector="#product-details .price",  # CSS selector
    extract_text=True  # Extract text only (True) or HTML (False)
)

# XPath filtering (XML path-based content extraction)
xpath_filter = ContentFilter(
    filter_type="xpath",
    selector="//div[@id='product-details']/span[@class='price']",  # XPath expression
    extract_text=True  # Extract text only (True) or HTML (False)
)

# Regex filtering (pattern-based content extraction)
regex_filter = ContentFilter(
    filter_type="regex",
    pattern=r"Price: \$(\d+\.\d+)",  # Regular expression pattern
    replacement=None  # Optional replacement string (returns matches if None)
)

# Regex with replacement (pattern-based content transformation)
regex_replace_filter = ContentFilter(
    filter_type="regex",
    pattern=r"Price: \$(\d+\.\d+)",  # Regular expression pattern
    replacement=r"Product costs: $\1"  # Replacement with capture groups
)

# Use filters with the crawler
crawler = BaseCrawler(
    content_filters=[bm25_filter, css_filter]  # Can combine multiple filters
)

# Crawl with content filtering
result = await crawler.crawl("https://example-shop.com/products/product-123")
```

### Filter Type Comparison

| Filter Type | Use Case                                        | Pros                            | Cons                                     |
| ----------- | ----------------------------------------------- | ------------------------------- | ---------------------------------------- |
| `bm25`      | Finding relevant text blocks based on keywords  | Fast, works with any content    | Less precise than DOM-based methods      |
| `pruning`   | Removing boilerplate content                    | Improves signal-to-noise ratio  | May remove some relevant content         |
| `llm`       | Advanced semantic filtering                     | Highly intelligent extraction   | Slower, requires API calls               |
| `css`       | Extracting specific elements with CSS selectors | Precise targeting, fast         | Requires knowledge of page structure     |
| `xpath`     | Extracting specific elements with XPath         | Very flexible element selection | More complex syntax than CSS             |
| `regex`     | Pattern matching and text transformation        | Works on any text content       | Can be brittle if HTML structure changes |

## Configuration

The library uses Pydantic models for configuration:

```python
from crawl4ai_llm.config import AppConfig, LLMConfig, CrawlerConfig, StorageConfig

config = AppConfig(
    llm=LLMConfig(
        provider="openai",  # Currently supports "openai"
        model_name="gpt-3.5-turbo",  # Model to use for extraction
        api_key="your-api-key",
        temperature=0.2,
        max_tokens=2000
    ),
    crawler=CrawlerConfig(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        timeout=30,  # Request timeout in seconds
        max_retries=3,  # Max retry attempts
        retry_delay=2,  # Delay between retries in seconds
        rate_limit=1  # Requests per second
    ),
    storage=StorageConfig(
        type="json",  # Currently supports "json"
        path="./data",  # Storage directory
        use_uuid=True  # Use UUIDs for product IDs
    )
)
```

You can also load configuration from YAML or JSON:

```bash
python examples/validate_config.py -c config.yaml
```

## Extraction Strategies

The library supports multiple extraction strategies:

- **auto**: Dynamically generates a schema for the website and extracts data
- **llm**: Uses a direct LLM prompt to extract product data
- **fallback**: A simplified extraction approach when other methods fail

```python
# Use automatic schema generation (default)
product_data = await extractor.extract(url, strategy="auto")

# Use direct LLM extraction
product_data = await extractor.extract(url, strategy="llm")
```

## Performance Considerations

- **Batch Operations**: Use batch operations when working with multiple products for better performance
- **Caching**: The library automatically caches crawl results to avoid redundant requests
- **Content Filtering**: Use appropriate content filters to reduce the amount of data processed by LLMs

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
