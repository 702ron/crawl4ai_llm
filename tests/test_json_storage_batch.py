"""
Tests for batch operations in JSONStorage.
"""

import asyncio
import os
import pytest
import json
import tempfile
import shutil
from typing import Dict, List, Any

from crawl4ai_llm.storage.json_storage import JSONStorage
from crawl4ai_llm.storage.base import (
    StorageConnectionError,
    ProductNotFoundError,
    DuplicateProductError,
)


@pytest.fixture
def test_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(test_dir):
    """Create a JSONStorage instance for testing."""
    return JSONStorage(test_dir)


@pytest.fixture
def sample_products() -> List[Dict[str, Any]]:
    """Create sample product data for testing."""
    return [
        {
            "name": "Test Product 1",
            "brand": "Test Brand",
            "category": "Test Category",
            "price": 99.99,
            "currency": "USD",
            "url": "https://example.com/product1",
            "sku": "TEST001",
            "seller_id": "SELLER001",
            "description": "This is a test product 1.",
        },
        {
            "name": "Test Product 2",
            "brand": "Test Brand",
            "category": "Test Category",
            "price": 149.99,
            "currency": "USD",
            "url": "https://example.com/product2",
            "sku": "TEST002",
            "seller_id": "SELLER001",
            "description": "This is a test product 2.",
        },
        {
            "name": "Test Product 3",
            "brand": "Another Brand",
            "category": "Different Category",
            "price": 199.99,
            "currency": "EUR",
            "url": "https://example.com/product3",
            "sku": "TEST003",
            "seller_id": "SELLER002",
            "description": "This is a test product 3.",
        },
    ]


@pytest.mark.asyncio
async def test_save_products_batch(storage, sample_products):
    """Test saving multiple products in a batch."""
    # Save products in batch
    product_ids = await storage.save_products(sample_products)
    
    # Verify we got 3 IDs back
    assert len(product_ids) == 3
    
    # Verify we can retrieve each product
    for i, product_id in enumerate(product_ids):
        product = await storage.get_product(product_id)
        assert product["name"] == sample_products[i]["name"]
        assert product["price"] == sample_products[i]["price"]
        assert product["id"] == product_id  # ID should be added to the product data
    
    # Check the index file
    with open(os.path.join(storage.directory, "product_index.json"), "r") as f:
        index = json.load(f)
        assert len(index) == 3
        for product_id in product_ids:
            assert product_id in index


@pytest.mark.asyncio
async def test_save_products_empty_list(storage):
    """Test saving an empty list of products."""
    product_ids = await storage.save_products([])
    assert product_ids == []


@pytest.mark.asyncio
async def test_save_products_duplicate(storage, sample_products):
    """Test saving products with duplicate IDs."""
    # Save products first time
    await storage.save_products(sample_products[:2])
    
    # Try to save one of the same products again
    with pytest.raises(DuplicateProductError):
        await storage.save_products([sample_products[0]])


@pytest.mark.asyncio
async def test_get_products_batch(storage, sample_products):
    """Test retrieving multiple products in a batch."""
    # Save products
    product_ids = await storage.save_products(sample_products)
    
    # Get products in batch
    products = await storage.get_products(product_ids)
    
    # Verify we got all products
    assert len(products) == 3
    
    # Verify product contents
    for i, product in enumerate(products):
        assert product["name"] == sample_products[i]["name"]
        assert product["price"] == sample_products[i]["price"]
        assert product["id"] == product_ids[i]


@pytest.mark.asyncio
async def test_get_products_empty_list(storage):
    """Test retrieving an empty list of products."""
    products = await storage.get_products([])
    assert products == []


@pytest.mark.asyncio
async def test_get_products_not_found(storage, sample_products):
    """Test retrieving products with non-existent IDs."""
    # Save some products
    product_ids = await storage.save_products(sample_products[:2])
    
    # Try to get existing products along with a non-existent one
    with pytest.raises(ProductNotFoundError):
        await storage.get_products([*product_ids, "non-existent-id"])


@pytest.mark.asyncio
async def test_update_products_batch(storage, sample_products):
    """Test updating multiple products in a batch."""
    # Save products
    product_ids = await storage.save_products(sample_products)
    
    # Prepare updates
    updates = [
        {
            "id": product_ids[0],
            "name": "Updated Product 1",
            "price": 89.99,
        },
        {
            "id": product_ids[1],
            "name": "Updated Product 2",
            "description": "This is an updated description.",
        },
    ]
    
    # Update products in batch
    updated_ids = await storage.update_products(updates)
    
    # Verify we got the correct IDs back
    assert len(updated_ids) == 2
    assert set(updated_ids) == {product_ids[0], product_ids[1]}
    
    # Verify the updates were applied
    product1 = await storage.get_product(product_ids[0])
    assert product1["name"] == "Updated Product 1"
    assert product1["price"] == 89.99
    assert product1["description"] == sample_products[0]["description"]  # Unchanged
    
    product2 = await storage.get_product(product_ids[1])
    assert product2["name"] == "Updated Product 2"
    assert product2["price"] == sample_products[1]["price"]  # Unchanged
    assert product2["description"] == "This is an updated description."
    
    # Third product should be unchanged
    product3 = await storage.get_product(product_ids[2])
    assert product3["name"] == sample_products[2]["name"]
    assert product3["price"] == sample_products[2]["price"]
    assert product3["description"] == sample_products[2]["description"]


@pytest.mark.asyncio
async def test_update_products_empty_list(storage):
    """Test updating an empty list of products."""
    updated_ids = await storage.update_products([])
    assert updated_ids == []


@pytest.mark.asyncio
async def test_update_products_not_found(storage, sample_products):
    """Test updating products with non-existent IDs."""
    # Save some products
    product_ids = await storage.save_products(sample_products[:2])
    
    # Try to update existing products along with a non-existent one
    updates = [
        {
            "id": product_ids[0],
            "name": "Updated Product 1",
        },
        {
            "id": "non-existent-id",
            "name": "Non-existent Product",
        },
    ]
    
    with pytest.raises(ProductNotFoundError):
        await storage.update_products(updates)
    
    # Verify no updates were applied (transaction should be rolled back)
    product = await storage.get_product(product_ids[0])
    assert product["name"] == sample_products[0]["name"]  # Should not be updated


@pytest.mark.asyncio
async def test_update_products_missing_id(storage, sample_products):
    """Test updating products without ID field."""
    # Save some products
    await storage.save_products(sample_products[:2])
    
    # Try to update without providing ID
    updates = [
        {
            "name": "Updated Product 1",
        },
    ]
    
    with pytest.raises(ValueError):
        await storage.update_products(updates)


@pytest.mark.asyncio
async def test_delete_products_batch(storage, sample_products):
    """Test deleting multiple products in a batch."""
    # Save products
    product_ids = await storage.save_products(sample_products)
    
    # Delete first two products
    deleted_count = await storage.delete_products(product_ids[:2])
    
    # Verify the count
    assert deleted_count == 2
    
    # Verify products were deleted
    with pytest.raises(ProductNotFoundError):
        await storage.get_product(product_ids[0])
    
    with pytest.raises(ProductNotFoundError):
        await storage.get_product(product_ids[1])
    
    # Third product should still exist
    product3 = await storage.get_product(product_ids[2])
    assert product3["name"] == sample_products[2]["name"]
    
    # Check the index file
    with open(os.path.join(storage.directory, "product_index.json"), "r") as f:
        index = json.load(f)
        assert len(index) == 1
        assert product_ids[2] in index
        assert product_ids[0] not in index
        assert product_ids[1] not in index


@pytest.mark.asyncio
async def test_delete_products_empty_list(storage):
    """Test deleting an empty list of products."""
    deleted_count = await storage.delete_products([])
    assert deleted_count == 0


@pytest.mark.asyncio
async def test_delete_products_not_found(storage, sample_products):
    """Test deleting products with non-existent IDs."""
    # Save some products
    product_ids = await storage.save_products(sample_products[:2])
    
    # Try to delete existing products along with a non-existent one
    with pytest.raises(ProductNotFoundError):
        await storage.delete_products([*product_ids, "non-existent-id"])
    
    # Verify no products were deleted (transaction should be rolled back)
    for product_id in product_ids:
        product = await storage.get_product(product_id)
        assert product is not None


@pytest.mark.asyncio
async def test_batch_operations_performance(storage):
    """Test performance of batch operations vs. individual operations."""
    # Create a large number of test products
    num_products = 50
    test_products = [
        {
            "name": f"Performance Test Product {i}",
            "brand": "Test Brand",
            "category": "Performance Category",
            "price": 99.99 + i,
            "currency": "USD",
            "url": f"https://example.com/product{i}",
            "sku": f"PERF{i:03d}",
            "seller_id": "SELLER001",
            "description": f"This is performance test product {i}.",
        }
        for i in range(num_products)
    ]
    
    # Measure time for individual operations
    individual_start = asyncio.get_event_loop().time()
    individual_ids = []
    for product in test_products:
        product_id = await storage.save_product(product)
        individual_ids.append(product_id)
    individual_time = asyncio.get_event_loop().time() - individual_start
    
    # Delete all products
    await storage.delete_products(individual_ids)
    
    # Measure time for batch operation
    batch_start = asyncio.get_event_loop().time()
    batch_ids = await storage.save_products(test_products)
    batch_time = asyncio.get_event_loop().time() - batch_start
    
    # Verify results are the same
    assert len(batch_ids) == len(individual_ids)
    
    # Batch operation should be faster, but this is hard to test deterministically
    # so we'll just check that both completed successfully
    assert individual_time > 0
    assert batch_time > 0
    
    # Clean up
    await storage.delete_products(batch_ids)


@pytest.mark.asyncio
async def test_mixed_batch_operations(storage, sample_products):
    """Test performing multiple types of batch operations in sequence."""
    # Save products
    product_ids = await storage.save_products(sample_products)
    
    # Update some products
    updates = [
        {
            "id": product_ids[0],
            "name": "Updated Product 1",
            "price": 89.99,
        },
        {
            "id": product_ids[1],
            "name": "Updated Product 2",
            "description": "This is an updated description.",
        },
    ]
    
    await storage.update_products(updates)
    
    # Delete one product
    await storage.delete_products([product_ids[2]])
    
    # Create a new product
    new_product = {
        "name": "New Test Product",
        "brand": "New Brand",
        "category": "New Category",
        "price": 299.99,
        "currency": "USD",
        "url": "https://example.com/new-product",
        "sku": "NEW001",
        "seller_id": "SELLER003",
        "description": "This is a new test product.",
    }
    
    new_ids = await storage.save_products([new_product])
    assert len(new_ids) == 1
    
    # Get all remaining products
    products = await storage.get_products([product_ids[0], product_ids[1], new_ids[0]])
    
    # Verify the final state
    assert len(products) == 3
    
    # Find products by their names
    product1 = next(p for p in products if p["name"] == "Updated Product 1")
    product2 = next(p for p in products if p["name"] == "Updated Product 2")
    product_new = next(p for p in products if p["name"] == "New Test Product")
    
    assert product1["price"] == 89.99
    assert product2["description"] == "This is an updated description."
    assert product_new["seller_id"] == "SELLER003"
    
    # Verify product 3 is gone
    with pytest.raises(ProductNotFoundError):
        await storage.get_product(product_ids[2])