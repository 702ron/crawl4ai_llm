"""
Tests for the JSONStorage class.
"""

import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from typing import Dict, Any, List

import pytest

from crawl4ai_llm.storage.base import (
    StorageConnectionError,
    ProductNotFoundError,
    DuplicateProductError,
)
from crawl4ai_llm.storage.json_storage import JSONStorage


@pytest.fixture
def storage_dir():
    """Temporary directory for storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up after the test
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(storage_dir):
    """JSONStorage instance for testing."""
    return JSONStorage(storage_dir)


@pytest.fixture
def sample_product():
    """Sample product data for testing."""
    return {
        "title": "Test Product",
        "description": "This is a test product",
        "price": {
            "current": 99.99,
            "currency": "USD",
        },
        "sku": "TEST-123",
        "url": "https://example.com/products/test-123",
        "store_name": "Test Store",
        "images": [
            {
                "url": "https://example.com/images/test-123-1.jpg",
                "alt": "Test Product Image 1",
            }
        ],
        "attributes": {
            "color": "Red",
            "size": "Medium",
        }
    }


@pytest.fixture
def batch_products():
    """List of sample products for batch testing."""
    return [
        {
            "title": "Product 1",
            "sku": "SKU-001",
            "store_name": "Test Store",
            "url": "https://example.com/products/1",
            "price": {"current": 10.99, "currency": "USD"},
        },
        {
            "title": "Product 2",
            "sku": "SKU-002",
            "store_name": "Test Store",
            "url": "https://example.com/products/2",
            "price": {"current": 20.99, "currency": "USD"},
        },
        {
            "title": "Product 3",
            "sku": "SKU-003",
            "store_name": "Test Store",
            "url": "https://example.com/products/3",
            "price": {"current": 30.99, "currency": "USD"},
        }
    ]


async def test_storage_init(storage_dir):
    """Test storage initialization."""
    storage = JSONStorage(storage_dir)
    assert os.path.exists(storage.index_path)
    
    # Check that the index file is created and is valid JSON
    with open(storage.index_path, "r") as f:
        index = json.load(f)
        assert isinstance(index, dict)


async def test_save_product(storage, sample_product):
    """Test saving a product."""
    product_id = await storage.save_product(sample_product)
    
    # Check that the product was saved to a file
    file_path = storage._get_file_path(product_id)
    assert os.path.exists(file_path)
    
    # Check that the index was updated
    with open(storage.index_path, "r") as f:
        index = json.load(f)
        assert product_id in index
        assert index[product_id]["title"] == sample_product["title"]
    
    # Check that metadata was added
    with open(file_path, "r") as f:
        product_data = json.load(f)
        assert "metadata" in product_data
        assert "created_at" in product_data["metadata"]
        assert "updated_at" in product_data["metadata"]


async def test_get_product(storage, sample_product):
    """Test retrieving a product."""
    product_id = await storage.save_product(sample_product)
    
    # Retrieve the product
    product_data = await storage.get_product(product_id)
    
    # Check that the product data is correct
    assert product_data["title"] == sample_product["title"]
    assert product_data["description"] == sample_product["description"]
    assert product_data["id"] == product_id


async def test_update_product(storage, sample_product):
    """Test updating a product."""
    product_id = await storage.save_product(sample_product)
    
    # Get the initial update timestamp
    product_data = await storage.get_product(product_id)
    initial_updated_at = product_data["metadata"]["updated_at"]
    
    # Wait a bit to ensure the timestamp changes
    await asyncio.sleep(0.1)
    
    # Update the product
    updated_product = {
        "id": product_id,
        "title": "Updated Product",
        "price": {
            "current": 79.99,
            "currency": "USD",
        }
    }
    await storage.update_product(updated_product)
    
    # Retrieve the updated product
    updated_data = await storage.get_product(product_id)
    
    # Check that the update was applied
    assert updated_data["title"] == "Updated Product"
    assert updated_data["price"]["current"] == 79.99
    assert updated_data["description"] == sample_product["description"]  # Unchanged field
    
    # Check that the updated_at timestamp was updated
    assert updated_data["metadata"]["updated_at"] != initial_updated_at


async def test_delete_product(storage, sample_product):
    """Test deleting a product."""
    product_id = await storage.save_product(sample_product)
    
    # Check that the product exists
    assert os.path.exists(storage._get_file_path(product_id))
    
    # Delete the product
    result = await storage.delete_product(product_id)
    assert result is True
    
    # Check that the product file was deleted
    assert not os.path.exists(storage._get_file_path(product_id))
    
    # Check that the index was updated
    with open(storage.index_path, "r") as f:
        index = json.load(f)
        assert product_id not in index
    
    # Verify that trying to get the deleted product raises an error
    with pytest.raises(ProductNotFoundError):
        await storage.get_product(product_id)


async def test_list_products(storage, sample_product):
    """Test listing products."""
    # Save multiple products
    products = []
    for i in range(5):
        product = sample_product.copy()
        product["title"] = f"Product {i}"
        product["sku"] = f"TEST-{i}"
        product_id = await storage.save_product(product)
        products.append(product_id)
    
    # List all products
    result = await storage.list_products()
    assert result["total"] == 5
    assert len(result["products"]) == 5
    assert result["page"] == 1
    assert result["page_size"] == 100
    assert result["total_pages"] == 1
    
    # Test pagination
    result = await storage.list_products(page=1, page_size=2)
    assert result["total"] == 5
    assert len(result["products"]) == 2
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert result["total_pages"] == 3
    
    # Test filtering
    product = sample_product.copy()
    product["title"] = "Special Product"
    product["category"] = "Electronics"
    await storage.save_product(product)
    
    result = await storage.list_products(filters={"category": "Electronics"})
    assert result["total"] == 1
    assert result["products"][0]["title"] == "Special Product"
    
    # Test sorting
    result = await storage.list_products(sort_by="title", sort_order="asc")
    titles = [p["title"] for p in result["products"]]
    assert titles == sorted(titles)
    
    result = await storage.list_products(sort_by="title", sort_order="desc")
    titles = [p["title"] for p in result["products"]]
    assert titles == sorted(titles, reverse=True)


async def test_batch_save_products(storage, batch_products):
    """Test saving multiple products in a batch."""
    product_ids = await storage.save_products(batch_products)
    
    # Check that we got the right number of IDs
    assert len(product_ids) == 3
    
    # Check that all products were saved correctly
    for i, product_id in enumerate(product_ids):
        # Verify file exists
        file_path = storage._get_file_path(product_id)
        assert os.path.exists(file_path)
        
        # Verify data integrity
        product_data = await storage.get_product(product_id)
        assert product_data["title"] == batch_products[i]["title"]
        assert product_data["sku"] == batch_products[i]["sku"]
        
        # Verify metadata was added
        assert "metadata" in product_data
        assert "created_at" in product_data["metadata"]
        assert "updated_at" in product_data["metadata"]
    
    # Check that the index was updated with all products
    with open(storage.index_path, "r") as f:
        index = json.load(f)
        for product_id in product_ids:
            assert product_id in index


async def test_batch_get_products(storage, batch_products):
    """Test retrieving multiple products in a batch."""
    product_ids = await storage.save_products(batch_products)
    
    # Retrieve all products in a batch
    products = await storage.get_products(product_ids)
    
    # Check that we got all products
    assert len(products) == 3
    
    # Check that data is correct
    for i, product in enumerate(products):
        assert product["title"] == batch_products[i]["title"]
        assert product["sku"] == batch_products[i]["sku"]
    
    # Test retrieving a subset
    subset_ids = product_ids[:2]
    subset_products = await storage.get_products(subset_ids)
    assert len(subset_products) == 2
    
    # Test error for non-existent product
    with pytest.raises(ProductNotFoundError):
        await storage.get_products([product_ids[0], "non-existent-id"])
    
    # Test empty list case
    empty_result = await storage.get_products([])
    assert empty_result == []


async def test_batch_update_products(storage, batch_products):
    """Test updating multiple products in a batch."""
    product_ids = await storage.save_products(batch_products)
    
    # Get original update timestamps
    original_products = await storage.get_products(product_ids)
    original_timestamps = [p["metadata"]["updated_at"] for p in original_products]
    
    # Wait to ensure timestamps change
    await asyncio.sleep(0.1)
    
    # Prepare updates
    updates = [
        {"id": product_ids[0], "price": {"current": 15.99, "currency": "USD"}},
        {"id": product_ids[1], "price": {"current": 25.99, "currency": "USD"}},
        {"id": product_ids[2], "price": {"current": 35.99, "currency": "USD"}}
    ]
    
    # Perform batch update
    updated_ids = await storage.update_products(updates)
    assert len(updated_ids) == 3
    assert set(updated_ids) == set(product_ids)
    
    # Verify the updates were applied
    updated_products = await storage.get_products(product_ids)
    
    for i, product in enumerate(updated_products):
        assert product["price"]["current"] == updates[i]["price"]["current"]
        assert product["title"] == batch_products[i]["title"]  # Unchanged field
        
        # Check that the updated_at timestamp was updated
        assert product["metadata"]["updated_at"] != original_timestamps[i]
    
    # Test error for non-existent product
    bad_updates = [
        {"id": product_ids[0], "price": {"current": 16.99}},
        {"id": "non-existent-id", "price": {"current": 26.99}}
    ]
    with pytest.raises(ProductNotFoundError):
        await storage.update_products(bad_updates)
    
    # Test missing ID
    with pytest.raises(ValueError):
        await storage.update_products([{"price": {"current": 17.99}}])
    
    # Test empty list case
    empty_result = await storage.update_products([])
    assert empty_result == []


async def test_batch_delete_products(storage, batch_products):
    """Test deleting multiple products in a batch."""
    product_ids = await storage.save_products(batch_products)
    
    # Check that all products exist
    for product_id in product_ids:
        assert os.path.exists(storage._get_file_path(product_id))
    
    # Delete all products
    deleted_count = await storage.delete_products(product_ids)
    assert deleted_count == 3
    
    # Check that all files were deleted
    for product_id in product_ids:
        assert not os.path.exists(storage._get_file_path(product_id))
    
    # Check that the index was updated
    with open(storage.index_path, "r") as f:
        index = json.load(f)
        for product_id in product_ids:
            assert product_id not in index
    
    # Verify that trying to get any deleted product raises an error
    for product_id in product_ids:
        with pytest.raises(ProductNotFoundError):
            await storage.get_product(product_id)
    
    # Test error for non-existent product
    with pytest.raises(ProductNotFoundError):
        await storage.delete_products(["non-existent-id"])
    
    # Test empty list case
    empty_result = await storage.delete_products([])
    assert empty_result == 0


async def test_product_not_found(storage):
    """Test error handling for product not found."""
    with pytest.raises(ProductNotFoundError):
        await storage.get_product("non-existent-id")
    
    with pytest.raises(ProductNotFoundError):
        await storage.update_product({"id": "non-existent-id", "title": "Updated"})
    
    with pytest.raises(ProductNotFoundError):
        await storage.delete_product("non-existent-id")


async def test_duplicate_product(storage, sample_product):
    """Test error handling for duplicate products."""
    product_id = await storage.save_product(sample_product)
    
    # Try to save a product with the same ID
    duplicate_product = sample_product.copy()
    duplicate_product["id"] = product_id
    
    with pytest.raises(DuplicateProductError):
        await storage.save_product(duplicate_product)
    
    # Try to save a product with the same SKU and store name
    with pytest.raises(DuplicateProductError):
        await storage.save_product(sample_product)


async def test_storage_connection_error():
    """Test error handling for storage connection errors."""
    # Create a read-only directory
    with tempfile.TemporaryDirectory() as temp_dir:
        read_only_dir = os.path.join(temp_dir, "read_only")
        os.makedirs(read_only_dir)
        os.chmod(read_only_dir, 0o500)  # Read and execute only
        
        # Try to create storage in a read-only directory
        with pytest.raises(StorageConnectionError):
            storage = JSONStorage(read_only_dir)
            product = {"title": "Test"}
            await storage.save_product(product)


async def test_multiple_storage_instances(storage_dir, sample_product):
    """Test that multiple storage instances can interact correctly."""
    storage1 = JSONStorage(storage_dir)
    storage2 = JSONStorage(storage_dir)
    
    # Save a product using the first instance
    product_id = await storage1.save_product(sample_product)
    
    # Get the product using the second instance
    product_data = await storage2.get_product(product_id)
    assert product_data["title"] == sample_product["title"]
    
    # Update the product using the second instance
    updated_product = {"id": product_id, "title": "Updated by Instance 2"}
    await storage2.update_product(updated_product)
    
    # Verify the update using the first instance
    updated_data = await storage1.get_product(product_id)
    assert updated_data["title"] == "Updated by Instance 2"


async def test_index_file_corruption(storage_dir, sample_product):
    """Test resilience against index file corruption."""
    storage = JSONStorage(storage_dir)
    
    # Save a product
    product_id = await storage.save_product(sample_product)
    
    # Corrupt the index file
    with open(storage.index_path, "w") as f:
        f.write("This is not valid JSON")
    
    # Test that we can still get products, but listing returns empty
    product_data = await storage.get_product(product_id)
    assert product_data["title"] == sample_product["title"]
    
    result = await storage.list_products()
    assert result["total"] == 0
    assert len(result["products"]) == 0


async def test_custom_id_generation(storage):
    """Test custom ID generation logic."""
    # Test product with specific ID
    product1 = {"id": "custom-id", "title": "Product with Custom ID"}
    product_id1 = await storage.save_product(product1)
    assert product_id1 == "custom-id"
    
    # Test product with SKU and store name
    product2 = {"sku": "ABC123", "store_name": "Test Store", "title": "Product with SKU"}
    product_id2 = await storage.save_product(product2)
    assert product_id2 == "Test Store_ABC123"
    
    # Test product with URL
    product3 = {"url": "https://example.com/product/123", "title": "Product with URL"}
    product_id3 = await storage.save_product(product3)
    assert product_id3.startswith("url_")
    
    # Test product with no identifiers
    product4 = {"title": "Product with no identifiers"}
    product_id4 = await storage.save_product(product4)
    assert len(product_id4) > 0  # Should generate a random UUID


async def test_complex_filters(storage):
    """Test complex filtering scenarios."""
    # Save products with various attributes
    products = [
        {
            "title": "Laptop",
            "category": "Electronics",
            "price": {"current": 999.99, "currency": "USD"},
            "metadata": {"tags": ["computer", "work"]}
        },
        {
            "title": "Phone",
            "category": "Electronics",
            "price": {"current": 499.99, "currency": "USD"},
            "metadata": {"tags": ["mobile", "communication"]}
        },
        {
            "title": "Desk",
            "category": "Furniture",
            "price": {"current": 199.99, "currency": "USD"},
            "metadata": {"tags": ["work", "home"]}
        }
    ]
    
    for product in products:
        await storage.save_product(product)
    
    # Test filtering by category
    result = await storage.list_products(filters={"category": "Electronics"})
    assert result["total"] == 2
    assert {p["title"] for p in result["products"]} == {"Laptop", "Phone"}
    
    # Test filtering by metadata
    result = await storage.list_products(filters={"metadata.tags": ["work", "home"]})
    assert result["total"] == 1
    assert result["products"][0]["title"] == "Desk"
    
    # Test no matches
    result = await storage.list_products(filters={"category": "Clothing"})
    assert result["total"] == 0