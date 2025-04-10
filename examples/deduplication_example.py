#!/usr/bin/env python3
"""
Example script demonstrating the usage of the Deduplicator class for
finding and merging duplicate products in the crawl4ai_llm package.
"""

import json
import logging
import os
from typing import Dict, List, Any

from crawl4ai_llm.models import ProductData
from crawl4ai_llm.processing import Deduplicator, get_duplicate_groups
from crawl4ai_llm.storage import JSONStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("deduplication_example")

# Create a temporary directory for storage
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_storage")
os.makedirs(TEMP_DIR, exist_ok=True)


def create_sample_products() -> List[ProductData]:
    """
    Create a list of sample products with some duplicates for demonstration.
    """
    products = [
        # Original product
        ProductData(
            url="https://example.com/product/1",
            title="iPhone 13 Pro Max 256GB Sierra Blue",
            brand="Apple",
            description="The latest iPhone with A15 Bionic chip and Pro camera system",
            sku="IPH13PM256BLUE",
            model_number="MLLL3LL/A",
            price=1099.99,
            currency="USD",
            availability="In Stock",
            metadata={"color": "Sierra Blue", "storage": "256GB"}
        ),
        # Similar product with different SKU but same model
        ProductData(
            url="https://example2.com/product/iphone13",
            title="Apple iPhone 13 Pro Max (256GB) - Sierra Blue",
            brand="Apple",
            description="iPhone 13 Pro Max with 256GB storage in Sierra Blue color",
            sku="AP-IPH13PM-256-BLUE",  # Different SKU
            model_number="MLLL3LL/A",  # Same model number
            price=1099.99,
            currency="USD",
            availability="In Stock",
            metadata={"color": "Sierra Blue", "memory": "256GB"}
        ),
        # Similar product with price variation
        ProductData(
            url="https://example3.com/iphone13promax",
            title="iPhone 13 Pro Max - 256GB - Blue",
            brand="Apple",
            description="Pro camera system, A15 Bionic, Sierra Blue",
            sku="IPH13PM256BLUE-E3",  # Different SKU
            model_number="MLLL3LL/A",  # Same model number
            price=1079.99,  # Slightly different price
            currency="USD",
            availability="In Stock",
            metadata={"color": "Blue"}
        ),
        # Completely different product
        ProductData(
            url="https://example.com/product/2",
            title="Samsung Galaxy S21 Ultra 5G 256GB Phantom Black",
            brand="Samsung",
            description="5G Android smartphone with 108MP camera",
            sku="SM-G998BZKDEUA",
            model_number="SM-G998B",
            price=1199.99,
            currency="USD",
            availability="In Stock",
            metadata={"color": "Phantom Black", "storage": "256GB"}
        ),
        # Similar to Samsung with variant
        ProductData(
            url="https://example2.com/samsung-s21-ultra",
            title="Samsung Galaxy S21 Ultra (256GB, Phantom Black)",
            brand="Samsung",
            description="Galaxy S21 Ultra 5G with 108MP camera and 256GB storage",
            sku="SAMS21U256BLK",
            model_number="SM-G998B",
            price=1189.99,
            currency="USD",
            availability="In Stock",
            metadata={"color": "Phantom Black", "storage": "256GB"}
        ),
        # Another product
        ProductData(
            url="https://example.com/product/3",
            title="Google Pixel 6 Pro 128GB Stormy Black",
            brand="Google",
            description="Google Pixel smartphone with Google Tensor chip",
            sku="GA03149-US",
            model_number="GR1YH",
            price=899.99,
            currency="USD",
            availability="In Stock",
            metadata={"color": "Stormy Black", "storage": "128GB"}
        )
    ]
    return products


def basic_deduplication_example():
    """
    Basic example demonstrating how to find duplicates using the Deduplicator class.
    """
    logger.info("Running basic deduplication example...")
    
    # Create sample products
    products = create_sample_products()
    logger.info(f"Created {len(products)} sample products")
    
    # Initialize the deduplicator with a similarity threshold of 0.7
    deduplicator = Deduplicator(similarity_threshold=0.7)
    logger.info(f"Initialized Deduplicator with threshold: {deduplicator.similarity_threshold}")
    
    # Find duplicates
    duplicates = deduplicator.find_duplicates(products)
    logger.info(f"Found {len(duplicates)} sets of duplicate products")
    
    # Print the duplicate sets
    for i, duplicate_set in enumerate(duplicates, 1):
        logger.info(f"Duplicate set #{i}:")
        for j, product in enumerate(duplicate_set, 1):
            logger.info(f"  {j}. {product.title} (SKU: {product.sku}, Model: {product.model_number})")
        logger.info("")


def deduplication_with_merging_example():
    """
    Example demonstrating how to merge duplicate products using different strategies.
    """
    logger.info("Running deduplication with merging example...")
    
    # Create sample products
    products = create_sample_products()
    
    # Initialize the deduplicator
    deduplicator = Deduplicator(similarity_threshold=0.7)
    
    # Find duplicate groups
    duplicate_groups = get_duplicate_groups(products, threshold=0.7)
    logger.info(f"Found {len(duplicate_groups)} groups of duplicate products")
    
    # Try different merging strategies
    strategies = ["latest", "most_complete", "combine"]
    
    for strategy in strategies:
        logger.info(f"\nMerging using '{strategy}' strategy:")
        
        for i, group in enumerate(duplicate_groups):
            merged_product = deduplicator.merge_products(group, strategy=strategy)
            
            logger.info(f"Group {i+1} merged result:")
            logger.info(f"  Title: {merged_product.title}")
            logger.info(f"  Brand: {merged_product.brand}")
            logger.info(f"  Price: {merged_product.price} {merged_product.currency}")
            logger.info(f"  SKU: {merged_product.sku}")
            logger.info(f"  Model: {merged_product.model_number}")
            
            # Show metadata differences
            if strategy == "combine" and merged_product.metadata:
                logger.info(f"  Combined metadata: {json.dumps(merged_product.metadata, indent=2)}")


def deduplication_with_storage_example():
    """
    Example demonstrating how to deduplicate products in storage.
    """
    logger.info("Running deduplication with storage example...")
    
    # Create a temporary storage
    storage = JSONStorage(storage_dir="./temp_storage", create_if_missing=True)
    
    try:
        # Save sample products to storage
        products = create_sample_products()
        product_ids = []
        
        for product in products:
            product_id = storage.save_product(product)
            product_ids.append(product_id)
            logger.info(f"Saved product: {product.title} with ID: {product_id}")
        
        logger.info(f"Saved {len(product_ids)} products to storage")
        
        # Retrieve all products from storage
        stored_products = [storage.get_product(pid) for pid in product_ids]
        
        # Initialize the deduplicator
        deduplicator = Deduplicator(similarity_threshold=0.7)
        
        # Find duplicates
        duplicate_groups = get_duplicate_groups(stored_products, threshold=0.7)
        
        if duplicate_groups:
            logger.info(f"Found {len(duplicate_groups)} groups of duplicate products in storage")
            
            # Get a list of products to keep (one from each group)
            # and products to delete (the rest)
            products_to_delete = []
            
            for group in duplicate_groups:
                # Sort by completeness (most fields filled)
                sorted_group = sorted(
                    group,
                    key=lambda p: sum(1 for v in p.__dict__.values() if v is not None),
                    reverse=True
                )
                
                # Keep the most complete product
                keep_product = sorted_group[0]
                logger.info(f"Keeping product: {keep_product.title} (ID: {keep_product.id})")
                
                # Mark the rest for deletion
                for product in sorted_group[1:]:
                    logger.info(f"Marking duplicate for deletion: {product.title} (ID: {product.id})")
                    products_to_delete.append(product.id)
            
            # Delete the duplicates
            if products_to_delete:
                for product_id in products_to_delete:
                    storage.delete_product(product_id)
                logger.info(f"Deleted {len(products_to_delete)} duplicate products from storage")
        else:
            logger.info("No duplicates found in storage")
    
    finally:
        # Clean up: delete all products
        for product_id in product_ids:
            try:
                storage.delete_product(product_id)
            except Exception:
                pass
        logger.info("Cleaned up temporary storage")


def main():
    """
    Main function to run the examples.
    """
    logger.info("Starting deduplication examples")
    
    # Run the examples
    basic_deduplication_example()
    logger.info("\n" + "-" * 50 + "\n")
    
    deduplication_with_merging_example()
    logger.info("\n" + "-" * 50 + "\n")
    
    deduplication_with_storage_example()
    
    logger.info("Deduplication examples completed")


if __name__ == "__main__":
    main() 