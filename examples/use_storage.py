#!/usr/bin/env python
"""
Example of using the storage layer to save and retrieve product data.

This example demonstrates:
1. Getting a storage instance
2. Saving a product
3. Retrieving a product
4. Updating a product
5. Listing products
6. Deleting a product
"""

import asyncio
import logging
from pprint import pprint
from datetime import datetime
from typing import Dict, Any

from crawl4ai_llm import (
    ProductData, ProductPrice, ProductImage, get_storage, get_config
)
from crawl4ai_llm.storage import StorageConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_sample_product(title: str) -> ProductData:
    """Create a sample product for demonstration."""
    return ProductData(
        title=title,
        description="This is a sample product for storage demonstration",
        brand="Sample Brand",
        price=ProductPrice(
            current_price=99.99,
            currency="USD",
            original_price=129.99,
            discount_percentage=23.08
        ),
        images=[
            ProductImage(
                url="https://example.com/sample-product.jpg",
                alt_text="Sample Product Image"
            )
        ],
        sku=f"SAMPLE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        availability="In Stock",
        url="https://example.com/products/sample",
        rating=4.5,
        review_count=100,
        extracted_at=datetime.now().isoformat(),
        source="example.com"
    )


async def storage_demo() -> None:
    """Run the storage demonstration."""
    # Create a custom storage configuration
    storage_config = StorageConfig(
        type="json",
        path="./demo_data",
        use_uuid=True
    )
    
    # Get a storage instance using the factory
    storage = get_storage(storage_config)
    logger.info(f"Initialized storage at {storage_config.path}")
    
    # Create and save a product
    product1 = await create_sample_product("Storage Demo Product")
    product_id = await storage.save_product(product1)
    logger.info(f"Saved product with ID: {product_id}")
    
    # Retrieve the product
    retrieved_product = await storage.get_product(product_id)
    logger.info(f"Retrieved product: {retrieved_product.title}")
    logger.info(f"Product price: {retrieved_product.price.current_price} {retrieved_product.price.currency}")
    
    # Update the product
    retrieved_product.price.current_price = 89.99
    retrieved_product.availability = "Limited Stock"
    success = await storage.update_product(product_id, retrieved_product)
    logger.info(f"Updated product: {success}")
    
    # Save another product
    product2 = await create_sample_product("Another Demo Product")
    product_id2 = await storage.save_product(product2)
    logger.info(f"Saved second product with ID: {product_id2}")
    
    # List all products
    products, total_count = await storage.list_products()
    logger.info(f"Found {total_count} products in storage")
    
    for i, product in enumerate(products, 1):
        logger.info(f"Product {i}: {product.title} - ${product.price.current_price}")
    
    # Filter products
    # Note: Filtering depends on what's stored in the index
    filtered_products, filtered_count = await storage.list_products(
        filters={"title": "Another"}
    )
    logger.info(f"Found {filtered_count} products matching filter")
    
    # Delete a product
    await storage.delete_product(product_id2)
    logger.info(f"Deleted product with ID: {product_id2}")
    
    # List again to confirm deletion
    remaining_products, remaining_count = await storage.list_products()
    logger.info(f"Found {remaining_count} products after deletion")


if __name__ == "__main__":
    """Run the demonstration."""
    asyncio.run(storage_demo()) 