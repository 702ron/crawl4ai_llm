#!/usr/bin/env python3
"""
Example of using transactions with the Crawl4AI LLM SDK.

This example demonstrates how to use transactions with the SDK to ensure
atomicity of operations when working with product data.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add parent directory to path to import from crawl4ai_llm
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai_llm.models import ProductData, ProductPrice
from crawl4ai_llm.storage import Transaction, JSONStorage, get_storage
from crawl4ai_llm.extraction import ProductExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("transaction_sdk_example")


async def basic_transaction_example():
    """
    Demonstrates a basic transaction for adding products.

    Shows how to:
    1. Create a transaction
    2. Add products to it
    3. Commit the transaction
    """
    logger.info("Running basic transaction example")

    # Create a temporary storage for this example
    storage_path = os.path.join(os.path.dirname(__file__), "temp_transaction_storage")
    os.makedirs(storage_path, exist_ok=True)
    storage = get_storage("json", base_path=storage_path)

    # Create test products
    product1 = ProductData(
        title="Test Product 1",
        price=ProductPrice(amount=19.99, currency="USD"),
        source_url="https://example.com/product1",
        metadata={"sku": "TEST-001", "store": "Example Store"}
    )
    
    product2 = ProductData(
        title="Test Product 2",
        price=ProductPrice(amount=29.99, currency="USD"),
        source_url="https://example.com/product2",
        metadata={"sku": "TEST-002", "store": "Example Store"}
    )

    # Start a transaction
    async with Transaction(storage) as transaction:
        # Add products
        await transaction.add_product(product1)
        await transaction.add_product(product2)
        
        # Transaction is automatically committed when exiting the context manager
        logger.info("Added 2 products in a transaction")
    
    # Verify products were added
    all_products = await storage.list_products()
    logger.info(f"Total products in storage: {len(all_products)}")
    for product in all_products:
        logger.info(f"Product: {product.title} (ID: {product.metadata.get('id')})")
    
    # Clean up for the next example
    for product in all_products:
        await storage.delete_product(product.metadata.get("id"))


async def rollback_transaction_example():
    """
    Demonstrates transaction rollback when an error occurs.

    Shows how:
    1. The transaction rolls back automatically if an exception occurs
    2. No products are added if the transaction fails
    """
    logger.info("\nRunning rollback transaction example")

    # Create a temporary storage for this example
    storage_path = os.path.join(os.path.dirname(__file__), "temp_transaction_storage")
    os.makedirs(storage_path, exist_ok=True)
    storage = get_storage("json", base_path=storage_path)

    # Create test products
    product1 = ProductData(
        title="Test Product 3",
        price=ProductPrice(amount=19.99, currency="USD"),
        source_url="https://example.com/product3",
        metadata={"sku": "TEST-003", "store": "Example Store"}
    )
    
    # Get initial product count
    initial_products = await storage.list_products()
    initial_count = len(initial_products)
    logger.info(f"Initial product count: {initial_count}")

    try:
        # Start a transaction
        async with Transaction(storage) as transaction:
            # Add a product
            await transaction.add_product(product1)
            logger.info("Added first product")
            
            # Simulate an error
            if True:  # Always trigger the error for demonstration
                logger.info("Simulating an error...")
                raise ValueError("Simulated error in transaction")
                
            # This code will not be executed
            logger.info("This should not be printed")
    except ValueError as e:
        logger.info(f"Caught error: {e}")
        logger.info("Transaction should be rolled back")
    
    # Verify no products were added
    current_products = await storage.list_products()
    current_count = len(current_products)
    logger.info(f"Final product count: {current_count}")
    
    if current_count == initial_count:
        logger.info("Success: Transaction was rolled back correctly")
    else:
        logger.error("Error: Transaction rollback failed")


async def extract_and_store_with_transaction():
    """
    Demonstrates extracting products and storing them in a transaction.

    Shows how to:
    1. Extract products using the ProductExtractor
    2. Store them atomically using a transaction
    """
    logger.info("\nRunning extraction with transaction example")

    # Create a temporary storage for this example
    storage_path = os.path.join(os.path.dirname(__file__), "temp_transaction_storage")
    os.makedirs(storage_path, exist_ok=True)
    storage = get_storage("json", base_path=storage_path)

    # Create an extractor
    extractor = ProductExtractor()
    
    # Sample URLs to extract from
    urls = [
        "https://www.amazon.com/dp/B08N5KWB9H",  # Example URL, may need to be updated
        "https://www.bestbuy.com/site/apple-airpods-pro-2nd-generation-white/4900964.p",
    ]
    
    try:
        # Start a transaction
        async with Transaction(storage) as transaction:
            logger.info(f"Extracting and storing {len(urls)} products")
            
            # Extract and store each product
            for url in urls:
                try:
                    logger.info(f"Extracting from: {url}")
                    # Extract product data
                    product = await extractor.extract(url)
                    
                    if product:
                        # Add timestamp to metadata
                        if product.metadata is None:
                            product.metadata = {}
                        product.metadata["extracted_at"] = datetime.now().isoformat()
                        
                        # Store in transaction
                        await transaction.add_product(product)
                        logger.info(f"Added product: {product.title}")
                    else:
                        logger.warning(f"Failed to extract product from {url}")
                
                except Exception as e:
                    logger.error(f"Error extracting from {url}: {e}")
                    # You can decide whether to raise the exception (which would
                    # rollback the entire transaction) or just log and continue
                    # For this example, we'll just log and continue
            
            logger.info("Committing transaction with extracted products")
            # Transaction is automatically committed when exiting the context manager
    
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        logger.info("All extracted products were rolled back")
    
    # Show the final products in storage
    all_products = await storage.list_products()
    logger.info(f"Total products in storage: {len(all_products)}")
    for product in all_products:
        logger.info(f"Product: {product.title} (ID: {product.metadata.get('id')})")


async def update_products_with_transaction():
    """
    Demonstrates updating products within a transaction.

    Shows how to:
    1. Get products from storage
    2. Modify them
    3. Update them within a transaction
    """
    logger.info("\nRunning update products with transaction example")

    # Create a temporary storage for this example
    storage_path = os.path.join(os.path.dirname(__file__), "temp_transaction_storage")
    os.makedirs(storage_path, exist_ok=True)
    storage = get_storage("json", base_path=storage_path)

    # First, add some products to update
    test_products = [
        ProductData(
            title="Update Test Product 1",
            price=ProductPrice(amount=19.99, currency="USD"),
            source_url="https://example.com/update1",
            metadata={"sku": "UPDATE-001", "store": "Example Store"}
        ),
        ProductData(
            title="Update Test Product 2",
            price=ProductPrice(amount=29.99, currency="USD"),
            source_url="https://example.com/update2",
            metadata={"sku": "UPDATE-002", "store": "Example Store"}
        ),
    ]
    
    # Add products individually
    product_ids = []
    for product in test_products:
        result = await storage.save_product(product)
        product_ids.append(result)
    
    logger.info(f"Added {len(product_ids)} products for update test")
    
    try:
        # Start a transaction
        async with Transaction(storage) as transaction:
            # Get products from transaction
            for product_id in product_ids:
                product = await transaction.get_product(product_id)
                
                if product:
                    # Update price
                    if product.price:
                        new_amount = product.price.amount * 1.1  # 10% price increase
                        product.price.amount = round(new_amount, 2)
                    
                    # Add update timestamp
                    if product.metadata is None:
                        product.metadata = {}
                    product.metadata["updated_at"] = datetime.now().isoformat()
                    
                    # Update in transaction
                    await transaction.update_product(product)
                    logger.info(f"Updated product: {product.title} - New price: {product.price.amount if product.price else 'N/A'}")
            
            logger.info("Committing transaction with updated products")
            # Transaction is automatically committed when exiting the context manager
    
    except Exception as e:
        logger.error(f"Update transaction failed: {e}")
    
    # Show the updated products
    for product_id in product_ids:
        product = await storage.get_product(product_id)
        logger.info(f"Updated product: {product.title} - Price: {product.price.amount if product.price else 'N/A'} - Updated at: {product.metadata.get('updated_at')}")
    
    # Clean up all products at the end of the example
    all_products = await storage.list_products()
    for product in all_products:
        await storage.delete_product(product.metadata.get("id"))
    logger.info("Cleaned up all products")


async def main():
    """Run all transaction examples."""
    logger.info("Starting transaction SDK examples")
    
    await basic_transaction_example()
    await rollback_transaction_example()
    
    # These examples require actual product extraction and may fail
    # depending on the URLs and extractor configuration
    # Comment them out if they cause issues
    try:
        await extract_and_store_with_transaction()
    except Exception as e:
        logger.error(f"Extract and store example failed: {e}")
    
    await update_products_with_transaction()
    
    # Clean up temporary storage directory
    storage_path = os.path.join(os.path.dirname(__file__), "temp_transaction_storage")
    if os.path.exists(storage_path):
        import shutil
        shutil.rmtree(storage_path)
        logger.info(f"Cleaned up storage directory: {storage_path}")
    
    logger.info("All transaction examples completed")


if __name__ == "__main__":
    asyncio.run(main()) 