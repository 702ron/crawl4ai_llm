#!/usr/bin/env python
"""
Example demonstrating the data versioning functionality in Crawl4AI.

This example shows how to:
1. Create a product with an initial version
2. Update the product multiple times to create new versions
3. List all available versions of a product
4. Retrieve a specific version of a product
"""

import asyncio
import os
import json
from datetime import datetime
import sys

# Add the parent directory to the path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai_llm.models import ProductData, ProductPrice, ProductAttribute
from crawl4ai_llm.storage import get_storage
from crawl4ai_llm.config import StorageConfig

async def main():
    # Create a temporary directory for this example
    storage_dir = "./temp_version_example"
    os.makedirs(storage_dir, exist_ok=True)
    
    # Configure storage with versioning enabled
    storage_config = StorageConfig(
        type="json",
        path=storage_dir,
        use_uuid=False,  # Use deterministic IDs for this example
        versioning_enabled=True,
    )
    
    # Get storage instance
    storage = get_storage(storage_config)
    
    # Create an initial product (version 1)
    print("Creating initial product (version 1)...")
    initial_product = ProductData(
        title="Smartphone X",
        brand="TechBrand",
        price=ProductPrice(
            current_price=499.99,
            currency="USD"
        ),
        url="https://example.com/products/smartphone-x",
        description="A powerful smartphone with amazing features.",
        attributes=[
            ProductAttribute(name="color", value="Black"),
            ProductAttribute(name="storage", value="128GB"),
            ProductAttribute(name="battery", value="4000mAh"),
        ],
        sku="PHONE-X-128",
        extracted_at=datetime.now().isoformat(),
    )
    
    # Save the initial product
    product_id = await storage.save_product(initial_product)
    print(f"Saved initial product with ID: {product_id}")
    
    # Retrieve and display the initial product
    product = await storage.get_product(product_id)
    print(f"Product version: {product.version}")
    print(f"Product data: {json.dumps(product.model_dump(), indent=2)[:200]}...")
    
    # Update the product to create version 2
    print("\nUpdating product to create version 2...")
    print(f"Current version before update: {product.version}")
    product.price.current_price = 479.99  # Price reduction
    product.attributes.append(ProductAttribute(name="promotion", value="Spring Sale"))
    await storage.update_product(product_id, product)
    
    # Retrieve and display the updated product
    product = await storage.get_product(product_id)
    print(f"Product version after update: {product.version}")
    print(f"Product data: {json.dumps(product.model_dump(), indent=2)[:200]}...")
    
    # Update the product again to create version 3
    print("\nUpdating product to create version 3...")
    print(f"Current version before update: {product.version}")
    # Reset version to 1 to force proper incrementing
    product.version = 1
    # Update the color attribute
    for attr in product.attributes:
        if attr.name == "color":
            attr.value = "Black, White, Blue"
        elif attr.name == "storage":
            attr.value = "128GB, 256GB"
    await storage.update_product(product_id, product)
    
    # Retrieve and display the updated product again
    product = await storage.get_product(product_id)
    print(f"Product version after update: {product.version}")
    print(f"Product data: {json.dumps(product.model_dump(), indent=2)[:200]}...")
    
    # List all versions of the product
    print("\nListing all versions of the product:")
    versions = await storage.list_product_versions(product_id)
    print(f"Available versions: {versions}")
    
    # Retrieve a specific version (version 1 - the original)
    print("\nRetrieving version 1 (original):")
    original_product = await storage.get_product_version(product_id, 1)
    print(f"Original product details: {json.dumps(original_product.model_dump(), indent=2)[:200]}...")
    
    # Retrieve a specific version (version 3 - latest)
    print("\nRetrieving version 3 (latest):")
    latest_product = await storage.get_product_version(product_id, 3)
    print(f"Latest product details: {json.dumps(latest_product.model_dump(), indent=2)[:200]}...")
    
    # Clean up
    if os.path.exists(storage_dir):
        import shutil
        shutil.rmtree(storage_dir)
        print(f"\nRemoved temporary directory: {storage_dir}")
    
    print("\nData versioning example completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 