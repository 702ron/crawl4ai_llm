"""
Tests for the JSONStorage class.
"""

import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from crawl4ai_llm.storage.base import (DuplicateProductError,
                                       ProductNotFoundError,
                                       StorageConnectionError, StorageError)
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
        },
    }


class TestJSONStorage:
    """Test suite for the JSONStorage class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a JSONStorage instance for testing."""
        return JSONStorage(temp_dir)

    @pytest.fixture
    def sample_product(self):
        """Create a sample product for testing."""
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
            },
        }

    @pytest.mark.asyncio
    async def test_save_product(self, storage, sample_product):
        """Test saving a product to storage."""
        # Save the product
        product_id = await storage.save_product(sample_product)

        # Verify the product ID is returned
        assert product_id is not None
        assert isinstance(product_id, str)

        # Verify the file was created
        file_path = storage._get_file_path(product_id)
        assert os.path.exists(file_path)

        # Verify the content of the file
        with open(file_path, "r") as f:
            content = json.load(f)
            assert content["title"] == sample_product["title"]
            assert content["price"]["current"] == sample_product["price"]["current"]
            assert content["price"]["currency"] == sample_product["price"]["currency"]
            assert content["sku"] == sample_product["sku"]
            assert content["url"] == sample_product["url"]
            assert content["store_name"] == sample_product["store_name"]
            assert content["images"][0]["url"] == sample_product["images"][0]["url"]
            assert content["images"][0]["alt"] == sample_product["images"][0]["alt"]
            assert (
                content["attributes"]["color"] == sample_product["attributes"]["color"]
            )
            assert content["attributes"]["size"] == sample_product["attributes"]["size"]
            assert content["metadata"]["product_id"] == product_id

    @pytest.mark.asyncio
    async def test_get_product(self, storage, sample_product):
        """Test retrieving a product from storage."""
        # Save the product
        product_id = await storage.save_product(sample_product)

        # Retrieve the product
        product = await storage.get_product(product_id)

        # Verify the product data
        assert product["title"] == sample_product["title"]
        assert product["price"]["current"] == sample_product["price"]["current"]
        assert product["price"]["currency"] == sample_product["price"]["currency"]
        assert product["sku"] == sample_product["sku"]
        assert product["url"] == sample_product["url"]
        assert product["store_name"] == sample_product["store_name"]
        assert product["images"][0]["url"] == sample_product["images"][0]["url"]
        assert product["images"][0]["alt"] == sample_product["images"][0]["alt"]
        assert product["attributes"]["color"] == sample_product["attributes"]["color"]
        assert product["attributes"]["size"] == sample_product["attributes"]["size"]
        assert product["metadata"]["product_id"] == product_id

    @pytest.mark.asyncio
    async def test_update_product(self, storage, sample_product):
        """Test updating a product in storage."""
        # Save the product
        product_id = await storage.save_product(sample_product)

        # Create an updated product
        updated_product = {
            "title": "Updated Test Product",
            "description": "This is an updated test product",
            "price": {
                "current": 15.99,
                "currency": "USD",
            },
            "sku": sample_product["sku"],
            "url": sample_product["url"],
            "store_name": sample_product["store_name"],
            "images": sample_product["images"],
            "attributes": sample_product["attributes"],
        }

        # Update the product
        success = await storage.update_product(product_id, updated_product)

        # Verify the update was successful
        assert success is True

        # Retrieve the updated product
        product = await storage.get_product(product_id)

        # Verify the product data was updated
        assert product["title"] == updated_product["title"]
        assert product["description"] == updated_product["description"]
        assert product["price"]["current"] == updated_product["price"]["current"]
        assert product["price"]["currency"] == updated_product["price"]["currency"]
        assert product["sku"] == updated_product["sku"]
        assert product["url"] == updated_product["url"]
        assert product["store_name"] == updated_product["store_name"]
        assert product["images"][0]["url"] == updated_product["images"][0]["url"]
        assert product["images"][0]["alt"] == updated_product["images"][0]["alt"]
        assert product["attributes"]["color"] == updated_product["attributes"]["color"]
        assert product["attributes"]["size"] == updated_product["attributes"]["size"]
        assert "updated_at" in product["metadata"]

    @pytest.mark.asyncio
    async def test_delete_product(self, storage, sample_product):
        """Test deleting a product from storage."""
        # Save the product
        product_id = await storage.save_product(sample_product)

        # Delete the product
        success = await storage.delete_product(product_id)

        # Verify the deletion was successful
        assert success is True

        # Verify the file was deleted
        file_path = storage._get_file_path(product_id)
        assert not os.path.exists(file_path)

        # Verify the product is not in the index
        index = await storage._load_index()
        assert product_id not in index

        # Verify getting the product raises an error
        with pytest.raises(ProductNotFoundError):
            await storage.get_product(product_id)

    @pytest.mark.asyncio
    async def test_list_products(self, storage):
        """Test listing products from storage."""
        # Create multiple products
        products = [
            {
                "title": f"Test Product {i}",
                "price": {"current": 10 + i, "currency": "USD"},
            }
            for i in range(10)
        ]

        # Save the products
        product_ids = []
        for product in products:
            product_id = await storage.save_product(product)
            product_ids.append(product_id)

        # List all products
        all_products, total = await storage.list_products()

        # Verify all products were returned
        assert len(all_products) == 10
        assert total == 10

        # Test pagination
        paginated, total = await storage.list_products(limit=5, offset=0)
        assert len(paginated) == 5
        assert total == 10

        # Test filtering by brand
        filtered, total = await storage.list_products(filters={"store_name": "Test"})
        assert len(filtered) == 10

        # Test sorting
        sorted_asc, _ = await storage.list_products(sort_by="title", sort_order="asc")
        sorted_desc, _ = await storage.list_products(sort_by="title", sort_order="desc")

        # Verify sorting order
        assert sorted_asc[0]["title"] < sorted_asc[-1]["title"]
        assert sorted_desc[0]["title"] > sorted_desc[-1]["title"]

    @pytest.mark.asyncio
    async def test_product_not_found(self, storage):
        """Test error handling when a product is not found."""
        # Try to get a non-existent product
        with pytest.raises(ProductNotFoundError):
            await storage.get_product("non-existent-id")

        # Try to update a non-existent product
        with pytest.raises(ProductNotFoundError):
            await storage.update_product(
                "non-existent-id", {"title": "Test", "url": "https://example.com"}
            )

        # Try to delete a non-existent product
        with pytest.raises(ProductNotFoundError):
            await storage.delete_product("non-existent-id")

    @pytest.mark.asyncio
    async def test_duplicate_product(self, storage, sample_product):
        """Test error handling when trying to save a duplicate product with the same ID."""
        # Create a storage instance that doesn't use UUIDs
        non_uuid_storage = JSONStorage(storage.storage_dir, use_uuid=False)

        # Save the product once
        product_id = await non_uuid_storage.save_product(sample_product)

        # Try to save the same product again
        with pytest.raises(DuplicateProductError):
            await non_uuid_storage.save_product(sample_product)

    @pytest.mark.asyncio
    async def test_storage_connection_error(self, temp_dir):
        """Test error handling when storage directory has permission issues."""
        # Try to create storage with a read-only directory
        readonly_dir = Path(temp_dir) / "readonly"
        readonly_dir.mkdir()

        # Make the directory read-only (this may not work on all systems)
        try:
            # Try to change permissions
            os.chmod(readonly_dir, 0o444)  # Read-only

            # Attempt to create storage in a read-only directory
            with pytest.raises(StorageConnectionError):
                JSONStorage(readonly_dir, create_if_missing=True)

        except PermissionError:
            # Skip the test if we can't set permissions
            pytest.skip("Cannot set directory permissions for this test")

    @pytest.mark.asyncio
    async def test_multiple_storage_instances(self, temp_dir):
        """Test using multiple storage instances with the same directory."""
        # Create two storage instances pointing to the same directory
        storage1 = JSONStorage(temp_dir)
        storage2 = JSONStorage(temp_dir)

        # Create a sample product
        product = {
            "title": "Shared Product",
            "url": "https://example.com/shared",
            "store_name": "Test",
        }

        # Save with the first instance
        product_id = await storage1.save_product(product)

        # Verify we can read it with the second instance
        retrieved_product = await storage2.get_product(product_id)
        assert retrieved_product["title"] == product["title"]

        # Update with the second instance
        updated_product = {
            "title": "Updated Shared Product",
            "url": product["url"],
            "store_name": product["store_name"],
        }
        await storage2.update_product(product_id, updated_product)

        # Verify the update is visible to the first instance
        updated_retrieved = await storage1.get_product(product_id)
        assert updated_retrieved["title"] == "Updated Shared Product"

    @pytest.mark.asyncio
    async def test_index_file_corruption(self, temp_dir):
        """Test resilience when the index file is corrupted."""
        # Create a storage instance
        storage = JSONStorage(temp_dir)

        # Save a product
        product = {
            "title": "Test Product",
            "url": "https://example.com/test",
            "store_name": "Test",
        }
        product_id = await storage.save_product(product)

        # Corrupt the index file
        with open(storage.index_path, "w") as f:
            f.write("This is not valid JSON")

        # Verify that operations still work with a corrupt index
        # get_product should still work as it doesn't rely on the index
        retrieved_product = await storage.get_product(product_id)
        assert retrieved_product["title"] == product["title"]

        # list_products should return empty results with a corrupted index
        products, count = await storage.list_products()
        assert count == 0
        assert len(products) == 0

        # Try saving another product (should still work by creating a new index)
        product2 = {
            "title": "Another Product",
            "url": "https://example.com/another",
            "store_name": "Test",
        }
        product2_id = await storage.save_product(product2)
        assert product2_id is not None

    @pytest.mark.asyncio
    async def test_custom_id_generation(self, temp_dir):
        """Test custom ID generation logic."""
        # Create a storage that doesn't use UUIDs
        storage = JSONStorage(temp_dir, use_uuid=False)

        # Test with different product configurations

        # Product with SKU
        product_with_sku = {
            "title": "SKU Product",
            "url": "https://example.com/sku",
            "store_name": "Test",
            "sku": "SKU123",
        }
        sku_id = await storage.save_product(product_with_sku)
        assert sku_id.startswith("sku_")

        # Product with UPC
        product_with_upc = {
            "title": "UPC Product",
            "url": "https://example.com/upc",
            "store_name": "Test",
            "sku": "123456789012",
        }
        upc_id = await storage.save_product(product_with_upc)
        assert upc_id.startswith("upc_")

        # Product with EAN
        product_with_ean = {
            "title": "EAN Product",
            "url": "https://example.com/ean",
            "store_name": "Test",
            "sku": "9781234567897",
        }
        ean_id = await storage.save_product(product_with_ean)
        assert ean_id.startswith("ean_")

        # Product with no identifiers (should use hash)
        product_no_id = {
            "title": "No ID Product",
            "url": "https://example.com/noid",
            "store_name": "Test",
        }
        hash_id = await storage.save_product(product_no_id)
        assert hash_id.startswith("hash_")

    @pytest.mark.asyncio
    async def test_complex_filters(self, storage):
        """Test more complex filtering scenarios."""
        # Create products with various attributes
        products = [
            {
                "title": "Premium Headphones",
                "store_name": "AudioMax",
                "url": "https://example.com/headphones1",
                "price": {"current": 199.99, "currency": "USD"},
                "sku": "AUD001",
                "attributes": {"color": "black", "wireless": True, "type": "over-ear"},
            },
            {
                "title": "Budget Headphones",
                "store_name": "AudioMax",
                "url": "https://example.com/headphones2",
                "price": {"current": 49.99, "currency": "USD"},
                "sku": "AUD002",
                "attributes": {"color": "white", "wireless": False, "type": "on-ear"},
            },
            {
                "title": "Gaming Keyboard",
                "store_name": "TechGear",
                "url": "https://example.com/keyboard1",
                "price": {"current": 129.99, "currency": "USD"},
                "sku": "TG001",
                "attributes": {"color": "black", "backlit": True, "mechanical": True},
            },
        ]

        # Save all products
        for product in products:
            await storage.save_product(product)

        # Test filtering by brand
        audioproducts, count = await storage.list_products(
            filters={"store_name": "AudioMax"}
        )
        assert count == 2
        assert all(p["store_name"] == "AudioMax" for p in audioproducts)

        # Test filtering by title substring
        headphones, count = await storage.list_products(filters={"title": "Headphones"})
        assert count == 2
        assert all("Headphones" in p["title"] for p in headphones)

        # Test filtering by multiple criteria
        budget_headphones, count = await storage.list_products(
            filters={"store_name": "AudioMax", "title": "Budget"}
        )
        assert count == 1
        assert budget_headphones[0]["title"] == "Budget Headphones"

        # Test sorting by price
        # This won't work with the current implementation as prices aren't in the index
        # This highlights a potential enhancement for the storage class

    @pytest.mark.asyncio
    async def test_file_corruption(self, storage, sample_product):
        """Test handling of corrupted product files."""
        # Save the product
        product_id = await storage.save_product(sample_product)
        file_path = storage._get_file_path(product_id)

        # Corrupt the file
        with open(file_path, "w") as f:
            f.write("This is not valid JSON")

        # Attempting to get the product should raise a StorageError
        with pytest.raises(StorageError):
            await storage.get_product(product_id)

    @pytest.mark.asyncio
    async def test_large_product_count(self, storage):
        """Test storage with a large number of products."""
        # Create a larger number of products
        product_count = 50
        product_ids = []

        for i in range(product_count):
            product = {
                "title": f"Product {i}",
                "store_name": f"Brand {i % 5}",  # Create 5 brands
                "url": f"https://example.com/product-{i}",
                "price": {"current": 10 + i, "currency": "USD"},
            }
            product_id = await storage.save_product(product)
            product_ids.append(product_id)

        # Test retrieving all products
        all_products, total = await storage.list_products(limit=product_count)
        assert total == product_count
        assert len(all_products) == product_count

        # Test pagination with smaller page size
        page_size = 10
        all_retrieved = []

        for page in range(0, product_count, page_size):
            products, _ = await storage.list_products(limit=page_size, offset=page)
            all_retrieved.extend(products)
            assert len(products) <= page_size

        assert len(all_retrieved) == product_count

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, storage):
        """Test concurrent operations on the storage."""
        # Create a set of products
        products = [
            {
                "title": f"Concurrent Product {i}",
                "store_name": "Test",
                "url": f"https://example.com/concurrent-{i}",
            }
            for i in range(10)
        ]

        # Define concurrent save operations
        async def save_product(product):
            return await storage.save_product(product)

        # Run concurrent save operations
        tasks = [save_product(product) for product in products]
        product_ids = await asyncio.gather(*tasks)

        # Verify all products were saved
        assert len(product_ids) == 10
        assert len(set(product_ids)) == 10  # All IDs should be unique

        # Test concurrent reads
        async def get_product(product_id):
            return await storage.get_product(product_id)

        # Run concurrent get operations
        get_tasks = [get_product(product_id) for product_id in product_ids]
        retrieved_products = await asyncio.gather(*get_tasks)

        # Verify all products were retrieved
        assert len(retrieved_products) == 10
        assert all(
            p["title"].startswith("Concurrent Product") for p in retrieved_products
        )

        # Test concurrent updates
        async def update_product(product_id):
            product = await storage.get_product(product_id)
            updated = {
                "title": f"Updated {product['title']}",
                "store_name": product["store_name"],
                "url": product["url"],
            }
            return await storage.update_product(product_id, updated)

        # Run concurrent update operations
        update_tasks = [update_product(product_id) for product_id in product_ids]
        update_results = await asyncio.gather(*update_tasks)

        # Verify all updates were successful
        assert all(update_results)

        # Verify the updates
        for product_id in product_ids:
            product = await storage.get_product(product_id)
            assert product["title"].startswith("Updated")

    @pytest.mark.asyncio
    async def test_edge_case_empty_products(self, storage):
        """Test listing products when there are no products in storage."""
        # List products from empty storage
        products, count = await storage.list_products()

        # Verify empty results
        assert count == 0
        assert len(products) == 0

    @pytest.mark.asyncio
    async def test_edge_case_invalid_sort(self, storage, sample_product):
        """Test sorting by an invalid field."""
        # Save a product first
        await storage.save_product(sample_product)

        # Try sorting by a nonexistent field
        products, count = await storage.list_products(sort_by="nonexistent_field")

        # Should still return results without error
        assert count > 0
        assert len(products) > 0

    @pytest.mark.asyncio
    async def test_advanced_filters(self, storage):
        """Test the improved filtering capabilities."""
        # Create products with nested attributes and various data types
        products = [
            {
                "title": "Gaming Laptop",
                "store_name": "TechPro",
                "url": "https://example.com/laptop1",
                "price": {"current": 1299.99, "currency": "USD"},
                "sku": "TP001",
                "attributes": {
                    "specs": {
                        "cpu": "Intel i7",
                        "ram": 16,
                        "storage": "512GB SSD",
                        "gpu": "NVIDIA RTX 3060",
                    },
                    "colors": ["black", "silver"],
                    "wireless": True,
                    "weight_kg": 2.1,
                },
            },
            {
                "title": "Business Laptop",
                "store_name": "TechPro",
                "url": "https://example.com/laptop2",
                "price": {"current": 999.99, "currency": "USD"},
                "sku": "TP002",
                "attributes": {
                    "specs": {
                        "cpu": "Intel i5",
                        "ram": 8,
                        "storage": "256GB SSD",
                        "gpu": "Integrated",
                    },
                    "colors": ["silver", "gray"],
                    "wireless": True,
                    "weight_kg": 1.8,
                },
            },
            {
                "title": "Tablet Pro",
                "store_name": "GadgetCo",
                "url": "https://example.com/tablet1",
                "price": {"current": 499.99, "currency": "USD"},
                "sku": "GC001",
                "attributes": {
                    "specs": {
                        "cpu": "ARM A12",
                        "ram": 4,
                        "storage": "128GB",
                        "gpu": "Integrated",
                    },
                    "colors": ["black", "white", "gold"],
                    "wireless": True,
                    "weight_kg": 0.5,
                },
            },
        ]

        # Save all products
        for product in products:
            await storage.save_product(product)

        # The improved _matches_filters method allows nested attribute filtering,
        # but we'd need to store these attributes in the index to make use of this.
        # For now, we can test the basic filtering that should still work

        # Test filtering by brand
        techpro_products, count = await storage.list_products(
            filters={"store_name": "TechPro"}
        )
        assert count == 2
        assert all(p["store_name"] == "TechPro" for p in techpro_products)

        # Test filtering with partial string match
        laptop_products, count = await storage.list_products(
            filters={"title": "Laptop"}
        )
        assert count == 2
        assert all("Laptop" in p["title"] for p in laptop_products)

        # Test case-insensitive filtering
        tablet_products, count = await storage.list_products(
            filters={"title": "tablet"}
        )
        assert count == 1
        assert "Tablet" in tablet_products[0]["title"]

    @pytest.mark.asyncio
    async def test_safe_file_paths(self, temp_dir):
        """Test that file paths are sanitized to be safe for the file system."""
        storage = JSONStorage(temp_dir, use_uuid=False)

        # Mock the _get_product_id method to return an unsafe ID
        original_get_product_id = storage._get_product_id

        def unsafe_id(*args, **kwargs):
            return "unsafe/path\\with:invalid*chars"

        storage._get_product_id = unsafe_id

        # Save a product - this should sanitize the unsafe ID
        product_id = await storage.save_product(
            {
                "title": "Test Product",
                "url": "https://example.com/test",
                "store_name": "Test Store",
            }
        )

        assert product_id == "unsafe/path\\with:invalid*chars"

        # Check that the file was saved with a sanitized path
        file_path = storage._get_file_path(product_id)
        assert "_" in str(file_path)
        assert "/" not in str(file_path.name)
        assert "\\" not in str(file_path.name)
        assert os.path.exists(file_path)

        # Restore the original method
        storage._get_product_id = original_get_product_id

    @pytest.mark.asyncio
    async def test_batch_save_products(self, storage):
        """Test batch saving multiple products."""
        # Create a list of sample products
        products = []
        for i in range(10):
            products.append(
                {
                    "title": f"Product {i}",
                    "description": f"Description for product {i}",
                    "price": {
                        "current": 10.0 + i,
                        "currency": "USD",
                    },
                    "sku": f"SKU-{i}",
                    "url": f"https://example.com/products/{i}",
                    "store_name": "Test Store",
                    "images": [
                        {
                            "url": f"https://example.com/images/{i}.jpg",
                            "alt": f"Product {i} Image",
                        }
                    ],
                    "attributes": {
                        "color": ["Red", "Blue", "Green"][i % 3],
                        "size": ["Small", "Medium", "Large"][i % 3],
                    },
                }
            )

        # Save products in batch
        product_ids = await storage.save_products(products)

        # Verify IDs were returned
        assert len(product_ids) == 10
        assert all(isinstance(pid, str) for pid in product_ids)

        # Verify products were saved correctly
        for i, product_id in enumerate(product_ids):
            product = await storage.get_product(product_id)
            assert product["title"] == f"Product {i}"
            assert product["price"]["current"] == 10.0 + i
            assert product["sku"] == f"SKU-{i}"
            assert "saved_at" in product["metadata"]
            assert product["metadata"]["product_id"] == product_id

    @pytest.mark.asyncio
    async def test_batch_get_products(self, storage):
        """Test batch retrieval of multiple products."""
        # Create and save sample products
        product_ids = []
        for i in range(5):
            product = {
                "title": f"Product {i}",
                "description": f"Description for product {i}",
                "price": {
                    "current": 10.0 + i,
                    "currency": "USD",
                },
                "url": f"https://example.com/products/{i}",
                "store_name": "Test Store",
            }
            product_id = await storage.save_product(product)
            product_ids.append(product_id)

        # Add a non-existent ID
        product_ids.append("non-existent-id")

        # Batch retrieve products
        products = await storage.get_products(product_ids)

        # Verify only existing products were retrieved
        assert len(products) == 5
        assert "non-existent-id" not in products

        # Verify product data
        for i, (product_id, product) in enumerate(products.items()):
            assert product["title"] == f"Product {i}"
            assert product["price"]["current"] == 10.0 + i

    @pytest.mark.asyncio
    async def test_batch_update_products(self, storage):
        """Test batch updating of multiple products."""
        # Create and save sample products
        product_ids = []
        for i in range(5):
            product = {
                "title": f"Product {i}",
                "description": f"Description for product {i}",
                "price": {
                    "current": 10.0 + i,
                    "currency": "USD",
                },
                "url": f"https://example.com/products/{i}",
                "store_name": "Test Store",
            }
            product_id = await storage.save_product(product)
            product_ids.append(product_id)

        # Create updates dict
        updates = {}
        for i, product_id in enumerate(product_ids):
            updates[product_id] = {
                "title": f"Updated Product {i}",
                "description": f"Updated description for product {i}",
                "price": {
                    "current": 20.0 + i,
                    "currency": "USD",
                },
                "url": f"https://example.com/products/{i}",
                "store_name": "Test Store",
            }

        # Add a non-existent ID
        updates["non-existent-id"] = {
            "title": "Non-existent Product",
            "url": "https://example.com/non-existent",
            "store_name": "Test Store",
        }

        # Batch update products
        results = await storage.update_products(updates)

        # Verify results
        assert len(results) == 6
        assert all(results[pid] for pid in product_ids)
        assert not results["non-existent-id"]

        # Verify product data was updated
        for i, product_id in enumerate(product_ids):
            product = await storage.get_product(product_id)
            assert product["title"] == f"Updated Product {i}"
            assert product["price"]["current"] == 20.0 + i
            assert "updated_at" in product["metadata"]

    @pytest.mark.asyncio
    async def test_batch_delete_products(self, storage):
        """Test batch deletion of multiple products."""
        # Create and save sample products
        product_ids = []
        for i in range(5):
            product = {
                "title": f"Product {i}",
                "description": f"Description for product {i}",
                "price": {
                    "current": 10.0 + i,
                    "currency": "USD",
                },
                "url": f"https://example.com/products/{i}",
                "store_name": "Test Store",
            }
            product_id = await storage.save_product(product)
            product_ids.append(product_id)

        # Add a non-existent ID
        delete_ids = product_ids + ["non-existent-id"]

        # Batch delete products
        results = await storage.delete_products(delete_ids)

        # Verify results
        assert len(results) == 6
        assert all(results[pid] for pid in product_ids)
        assert not results["non-existent-id"]

        # Verify products were deleted
        for product_id in product_ids:
            with pytest.raises(ProductNotFoundError):
                await storage.get_product(product_id)

        # Verify index was updated
        index = await storage._load_index()
        for product_id in product_ids:
            assert product_id not in index

    @pytest.mark.asyncio
    async def test_batch_operations_empty_input(self, storage):
        """Test batch operations with empty input."""
        # Test save_products with empty list
        result = await storage.save_products([])
        assert result == []

        # Test get_products with empty list
        result = await storage.get_products([])
        assert result == {}

        # Test update_products with empty dict
        result = await storage.update_products({})
        assert result == {}

        # Test delete_products with empty list
        result = await storage.delete_products([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_operations_concurrent(self, storage):
        """Test concurrent batch operations."""
        # Create product lists
        products1 = []
        products2 = []

        for i in range(5):
            products1.append(
                {
                    "title": f"Product A{i}",
                    "url": f"https://example.com/products/a{i}",
                    "store_name": "Store A",
                }
            )
            products2.append(
                {
                    "title": f"Product B{i}",
                    "url": f"https://example.com/products/b{i}",
                    "store_name": "Store B",
                }
            )

        # Run concurrent batch save operations
        ids1, ids2 = await asyncio.gather(
            storage.save_products(products1), storage.save_products(products2)
        )

        # Verify all products were saved
        assert len(ids1) == 5
        assert len(ids2) == 5

        # Run concurrent batch get operations
        results1, results2 = await asyncio.gather(
            storage.get_products(ids1), storage.get_products(ids2)
        )

        # Verify results
        assert len(results1) == 5
        assert len(results2) == 5

        # Prepare updates
        updates1 = {
            pid: {
                "title": f"Updated A{i}",
                "url": products1[i]["url"],
                "store_name": "Store A",
            }
            for i, pid in enumerate(ids1)
        }
        updates2 = {
            pid: {
                "title": f"Updated B{i}",
                "url": products2[i]["url"],
                "store_name": "Store B",
            }
            for i, pid in enumerate(ids2)
        }

        # Run concurrent batch update operations
        update_results1, update_results2 = await asyncio.gather(
            storage.update_products(updates1), storage.update_products(updates2)
        )

        # Verify updates
        assert all(update_results1.values())
        assert all(update_results2.values())

        # Run concurrent batch delete operations
        delete_results1, delete_results2 = await asyncio.gather(
            storage.delete_products(ids1), storage.delete_products(ids2)
        )

        # Verify deletions
        assert all(delete_results1.values())
        assert all(delete_results2.values())

        # Verify all products are gone
        index = await storage._load_index()
        assert len(index) == 0

    @pytest.mark.asyncio
    async def test_storage_directory_recreation(self, temp_dir):
        """Test storage resilience when the storage directory is recreated during operation."""
        # Create the initial storage
        storage = JSONStorage(temp_dir)

        # Save a few products
        products = [
            {
                "title": f"Resilience Test Product {i}",
                "url": f"https://example.com/resilience-test-{i}",
                "store_name": "Test Brand",
            }
            for i in range(3)
        ]

        saved_ids = []
        for product in products:
            product_id = await storage.save_product(product)
            saved_ids.append(product_id)

        # Verify products were saved
        for product_id in saved_ids:
            product = await storage.get_product(product_id)
            assert "Resilience Test Product" in product["title"]

        # Simulate a storage directory recreation scenario
        # First, store the index and products in memory
        old_index = await storage._load_index()
        old_products = {}
        for product_id in saved_ids:
            old_products[product_id] = await storage.get_product(product_id)

        # Now recreate the directory (simulating a reset/recreation)
        shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        # The storage instance should handle this gracefully on next operations

        # Try to add a new product
        new_product = {
            "title": "New Product After Reset",
            "url": "https://example.com/new-after-reset",
            "store_name": "Test Brand",
        }

        # This should succeed by recreating the index
        new_id = await storage.save_product(new_product)
        assert new_id is not None

        # Pre-existing products should not be accessible anymore
        for product_id in saved_ids:
            with pytest.raises(ProductNotFoundError):
                await storage.get_product(product_id)

        # The new product should be available
        retrieved_new = await storage.get_product(new_id)
        assert retrieved_new["title"] == "New Product After Reset"
