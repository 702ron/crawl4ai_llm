#!/usr/bin/env python
"""
Transaction Example

This example demonstrates how to use the crawl4ai_llm.storage module 
to perform atomic operations with transactions.

The example shows:
1. Creating a transaction
2. Performing operations within a transaction
3. Committing a transaction
4. Rolling back a transaction on error
5. Complex transactions with multiple operations
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Add the parent directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crawl4ai_llm.models import ProductData, ProductPrice
from crawl4ai_llm.storage import ProductStorage

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("transaction-example")

# Sample products for demonstration
SAMPLE_PRODUCTS = [
    ProductData(
        title="Sample Product 1",
        url="https://example.com/product1",
        price=ProductPrice(current_price=19.99, currency="USD"),
        source="example_store",
        extracted_at=datetime.now().isoformat(),
        metadata={"product_id": "sample-1"}
    ),
    ProductData(
        title="Sample Product 2",
        url="https://example.com/product2",
        price=ProductPrice(current_price=29.99, currency="USD"),
        source="example_store",
        extracted_at=datetime.now().isoformat(),
        metadata={"product_id": "sample-2"}
    ),
    ProductData(
        title="Sample Product 3",
        url="https://example.com/product3",
        price=ProductPrice(current_price=39.99, currency="USD"),
        source="example_store",
        extracted_at=datetime.now().isoformat(),
        metadata={"product_id": "sample-3"}
    )
]

async def basic_transaction_example(storage: ProductStorage):
    """Demonstrates a basic transaction with commit"""
    logger.info("Running basic transaction example...")
    
    # Start a new transaction
    async with storage.transaction() as txn:
        # Add products within the transaction
        for product in SAMPLE_PRODUCTS:
            await storage.add_product(product, transaction=txn)
            logger.info(f"Added product: {product.title}")
        
        # Transaction is automatically committed when exiting the context
    
    # Verify products were added
    count = await storage.count_products()
    logger.info(f"Total products after basic transaction: {count}")

async def transaction_rollback_example(storage: ProductStorage):
    """Demonstrates transaction rollback on error"""
    logger.info("Running transaction rollback example...")
    
    # Get current product count
    initial_count = await storage.count_products()
    logger.info(f"Initial product count: {initial_count}")
    
    try:
        async with storage.transaction() as txn:
            # Add a valid product
            await storage.add_product(SAMPLE_PRODUCTS[0], transaction=txn)
            logger.info(f"Added product: {SAMPLE_PRODUCTS[0].title}")
            
            # Simulate an error
            logger.info("Simulating an error within transaction...")
            raise ValueError("Simulated error to trigger rollback")
            
            # This code won't execute
            await storage.add_product(SAMPLE_PRODUCTS[1], transaction=txn)
    except ValueError as e:
        logger.info(f"Caught error: {e}")
        logger.info("Transaction should have been rolled back")
    
    # Verify product count hasn't changed
    final_count = await storage.count_products()
    logger.info(f"Final product count: {final_count}")
    logger.info(f"Transaction successfully rolled back: {final_count == initial_count}")

async def complex_transaction_example(storage: ProductStorage):
    """Demonstrates a complex transaction with multiple operations"""
    logger.info("Running complex transaction example...")
    
    # Start with a clean slate
    await storage.delete_all_products()
    logger.info("Deleted all products to start fresh")
    
    # Get a product ID to update later
    product_id = SAMPLE_PRODUCTS[0].metadata["product_id"]
    
    # Add all products first (outside of transaction for this example)
    for product in SAMPLE_PRODUCTS:
        await storage.add_product(product)
    logger.info(f"Added {len(SAMPLE_PRODUCTS)} products")
    
    async with storage.transaction() as txn:
        # Update one product
        updated_product = SAMPLE_PRODUCTS[0].copy(deep=True)
        updated_product.title = "Updated Product Title"
        updated_product.price.current_price = 24.99
        await storage.update_product(product_id, updated_product, transaction=txn)
        logger.info(f"Updated product {product_id}")
        
        # Delete one product
        await storage.delete_product(SAMPLE_PRODUCTS[2].metadata["product_id"], transaction=txn)
        logger.info(f"Deleted product {SAMPLE_PRODUCTS[2].metadata['product_id']}")
    
    # Verify final state
    all_products = await storage.get_all_products()
    logger.info(f"Final product count: {len(all_products)}")
    
    # Verify updated product
    updated = await storage.get_product(product_id)
    if updated:
        logger.info(f"Updated product title: {updated.title}")
        logger.info(f"Updated product price: {updated.price.current_price}")

async def cleanup(storage: ProductStorage):
    """Clean up by removing all products"""
    logger.info("Cleaning up...")
    await storage.delete_all_products()
    count = await storage.count_products()
    logger.info(f"Final product count after cleanup: {count}")

async def main():
    """Run all transaction examples"""
    logger.info("Starting transaction examples")
    
    # Create storage instance (using in-memory for this example)
    storage = ProductStorage(db_url="sqlite:///:memory:")
    await storage.initialize()
    
    try:
        # Run examples
        await basic_transaction_example(storage)
        await transaction_rollback_example(storage)
        await complex_transaction_example(storage)
    finally:
        # Always clean up
        await cleanup(storage)
        # Close the storage connection
        await storage.close()
    
    logger.info("Transaction examples completed")

if __name__ == "__main__":
    asyncio.run(main()) 