# crawl4ai_llm

An e-commerce product extraction system with efficient storage capabilities.

## Overview

crawl4ai_llm is a package that provides tools for extracting product data from e-commerce websites and storing it efficiently. The system uses a combination of crawling, extraction strategies, and storage mechanisms to collect and manage product information.

## Features

- Multiple extraction strategies including CSS selectors, XPath, and LLM-based approaches
- Schema generation for automated extraction
- Efficient product data storage with JSON file-based implementation
- Filtering, pagination, and sorting capabilities
- Concurrent operation support with proper locking mechanisms
- Error handling for various scenarios

## Installation

```bash
pip install crawl4ai_llm
```

## Quick Start

```python
import asyncio
from crawl4ai_llm.config import StorageConfig
from crawl4ai_llm.storage import get_storage
from crawl4ai_llm.models import ProductData, ProductPrice

async def main():
    # Initialize storage
    config = StorageConfig(type="json", path="./data")
    storage = get_storage(config)
    
    # Create a product
    product = ProductData(
        title="Test Product",
        url="https://example.com/product",
        brand="Test Brand",
        prices=[ProductPrice(amount="99.99", currency="USD")]
    )
    
    # Save the product
    product_id = await storage.save_product(product)
    print(f"Saved product with ID: {product_id}")
    
    # Retrieve the product
    retrieved = await storage.get_product(product_id)
    print(f"Retrieved product: {retrieved.title}")
    
    # List products with filtering
    products, count = await storage.list_products(filters={"brand": "Test Brand"})
    print(f"Found {count} products")

if __name__ == "__main__":
    asyncio.run(main())
```

## Storage Performance

The storage system is designed for performance and reliability:

- File-based JSON storage with index for fast lookups
- Concurrent operation support with file locking
- Efficient filtering and sorting
- Resilience against file corruption and storage directory issues

See `TASKS.md` for planned performance enhancements.

## Development

### Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest tests/`

### Contributing

Contributions are welcome! Please check the `TASKS.md` file for planned features and improvements.

## License

MIT