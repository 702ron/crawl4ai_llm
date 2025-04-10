"""
Unit tests for the storage module in crawl4ai_llm package.
"""

import asyncio
import json
import os
import shutil
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import mkdtemp

import pytest

from crawl4ai_llm.config import StorageConfig
from crawl4ai_llm.models import ProductData, ProductImage, ProductPrice
from crawl4ai_llm.storage.base import ProductNotFoundError, StorageException
from crawl4ai_llm.storage.factory import get_storage
from crawl4ai_llm.storage.json_storage import JSONStorage


class TestJSONStorage(unittest.TestCase):
    """Test cases for JSONStorage class."""

    def setUp(self):
        """Set up test case with a temporary directory."""
        self.temp_dir = Path(mkdtemp())
        self.config = StorageConfig(
            type="json", path=str(self.temp_dir), use_uuid=False
        )
        self.storage = get_storage(self.config)

        # Create test product
        self.test_product = ProductData(
            url="https://example.com/product1",
            title="Test Product",
            price=ProductPrice(current=99.99, currency="USD"),
            description="This is a test product",
            images=[
                ProductImage(
                    url="https://example.com/image1.jpg", alt_text="Product Image 1"
                )
            ],
            brand="Test Brand",
            available=True,
            extracted_at=datetime.now(),
            source_html="<html>Test</html>",
            metadata={"sku": "TST123", "category": "Test Category"},
        )

    def tearDown(self):
        """Clean up temporary directory after test."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test storage initialization."""
        self.assertIsInstance(self.storage, JSONStorage)
        self.assertEqual(self.storage.storage_path, self.temp_dir)

        # Test directory creation
        non_existent_dir = self.temp_dir / "subdir"
        config = StorageConfig(type="json", path=str(non_existent_dir), use_uuid=False)
        storage = get_storage(config)
        self.assertTrue(non_existent_dir.exists())
        self.assertTrue(non_existent_dir.is_dir())

    def test_save_and_get_product(self):
        """Test saving and retrieving a product."""
        # Save product
        product_id = self.storage.save_product(self.test_product)
        self.assertIsNotNone(product_id)

        # Check that file exists
        product_file = self.temp_dir / f"{product_id}.json"
        self.assertTrue(product_file.exists())

        # Get product
        retrieved_product = self.storage.get_product(product_id)
        self.assertEqual(retrieved_product.url, self.test_product.url)
        self.assertEqual(retrieved_product.title, self.test_product.title)
        self.assertEqual(
            retrieved_product.price.current, self.test_product.price.current
        )
        self.assertEqual(
            retrieved_product.price.currency, self.test_product.price.currency
        )

    def test_get_nonexistent_product(self):
        """Test retrieving a non-existent product."""
        with self.assertRaises(StorageException):
            self.storage.get_product("nonexistent_id")

    def test_update_product(self):
        """Test updating a product."""
        # Save product
        product_id = self.storage.save_product(self.test_product)

        # Update product
        updated_product = self.test_product.copy()
        updated_product.title = "Updated Title"
        updated_product.price.current = 89.99
        updated_product.available = False

        self.storage.update_product(product_id, updated_product)

        # Get updated product
        retrieved_product = self.storage.get_product(product_id)
        self.assertEqual(retrieved_product.title, "Updated Title")
        self.assertEqual(retrieved_product.price.current, 89.99)
        self.assertFalse(retrieved_product.available)

    def test_delete_product(self):
        """Test deleting a product."""
        # Save product
        product_id = self.storage.save_product(self.test_product)
        product_file = self.temp_dir / f"{product_id}.json"
        self.assertTrue(product_file.exists())

        # Delete product
        self.storage.delete_product(product_id)
        self.assertFalse(product_file.exists())

        # Check that getting the deleted product raises an exception
        with self.assertRaises(StorageException):
            self.storage.get_product(product_id)

    def test_list_products(self):
        """Test listing products."""
        # Save multiple products
        product1 = self.test_product.copy()
        product1.url = "https://example.com/product1"
        product1.title = "Product 1"
        product1_id = self.storage.save_product(product1)

        product2 = self.test_product.copy()
        product2.url = "https://example.com/product2"
        product2.title = "Product 2"
        product2.price.current = 199.99
        product2_id = self.storage.save_product(product2)

        product3 = self.test_product.copy()
        product3.url = "https://example.com/product3"
        product3.title = "Product 3"
        product3.brand = "Another Brand"
        product3.available = False
        product3_id = self.storage.save_product(product3)

        # List all products
        products = self.storage.list_products()
        self.assertEqual(len(products), 3)

        # Test filtering by availability
        available_products = self.storage.list_products(available_only=True)
        self.assertEqual(len(available_products), 2)

        # Test filtering by brand
        test_brand_products = self.storage.list_products(filter_query="Test Brand")
        self.assertEqual(len(test_brand_products), 2)

        other_brand_products = self.storage.list_products(filter_query="Another Brand")
        self.assertEqual(len(other_brand_products), 1)

        # Test sorting by price
        products_by_price = self.storage.list_products(sort_by="price.current")
        self.assertEqual(products_by_price[0].price.current, 99.99)
        self.assertEqual(products_by_price[-1].price.current, 199.99)

        # Test sorting by title
        products_by_title = self.storage.list_products(sort_by="title")
        self.assertEqual(products_by_title[0].title, "Product 1")
        self.assertEqual(products_by_title[1].title, "Product 2")
        self.assertEqual(products_by_title[2].title, "Product 3")

    def test_uuid_based_storage(self):
        """Test storage with UUID-based filenames."""
        # Create storage with UUID filenames
        uuid_config = StorageConfig(
            type="json", path=str(self.temp_dir / "uuid_storage"), use_uuid=True
        )
        uuid_storage = get_storage(uuid_config)

        # Save product
        product_id = uuid_storage.save_product(self.test_product)

        # Check ID format (should be a UUID)
        self.assertRegex(
            product_id,
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        )

        # Check that file exists
        product_file = uuid_storage.storage_path / f"{product_id}.json"
        self.assertTrue(product_file.exists())

        # Get product
        retrieved_product = uuid_storage.get_product(product_id)
        self.assertEqual(retrieved_product.url, self.test_product.url)


@pytest.fixture
def temp_storage_dir():
    """Fixture that creates a temporary directory for storage testing."""
    with mkdtemp() as temp_dir:
        yield temp_dir


@pytest.fixture
def json_storage(temp_storage_dir):
    """Fixture that creates a JSON storage instance with a temporary directory."""
    config = StorageConfig(
        type="json", path=temp_storage_dir, filename_template="{product_id}.json"
    )
    return JSONStorage(config)


@pytest.fixture
def sample_product():
    """Fixture that creates a sample product for testing."""
    return ProductData(
        url="https://example.com/product/123",
        product_id="123",
        title="Test Product",
        description="This is a test product",
        price=ProductPrice(amount=99.99, currency="USD"),
        images=[
            ProductImage(
                url="https://example.com/images/123-1.jpg",
                alt_text="Test Product Image 1",
            )
        ],
        brand="Test Brand",
        availability="In Stock",
        extracted_at=datetime.now(),
    )


def test_storage_factory(temp_storage_dir):
    """Test that the storage factory creates the correct storage instance."""
    config = StorageConfig(
        type="json", path=temp_storage_dir, filename_template="{product_id}.json"
    )
    storage = get_storage(config)
    assert isinstance(storage, JSONStorage)
    assert storage.config.path == temp_storage_dir

    # Test with invalid storage type
    with pytest.raises(ValueError):
        get_storage(StorageConfig(type="invalid"))


def test_save_product(json_storage, sample_product):
    """Test saving a product to storage."""
    product_id = json_storage.save(sample_product)
    assert product_id == sample_product.product_id

    # Check that file exists
    expected_path = os.path.join(
        json_storage.config.path,
        json_storage.config.filename_template.format(
            product_id=sample_product.product_id
        ),
    )
    assert os.path.exists(expected_path)


def test_get_product(json_storage, sample_product):
    """Test retrieving a product from storage."""
    json_storage.save(sample_product)

    retrieved_product = json_storage.get(sample_product.product_id)
    assert retrieved_product.product_id == sample_product.product_id
    assert retrieved_product.title == sample_product.title
    assert retrieved_product.price.amount == sample_product.price.amount
    assert retrieved_product.price.currency == sample_product.price.currency

    # Test getting non-existent product
    with pytest.raises(FileNotFoundError):
        json_storage.get("non-existent-id")


def test_update_product(json_storage, sample_product):
    """Test updating a product in storage."""
    json_storage.save(sample_product)

    # Modify product
    updated_product = sample_product.model_copy(deep=True)
    updated_product.title = "Updated Test Product"
    updated_product.price.amount = 89.99

    # Update in storage
    json_storage.update(updated_product)

    # Retrieve and verify
    retrieved_product = json_storage.get(sample_product.product_id)
    assert retrieved_product.title == "Updated Test Product"
    assert retrieved_product.price.amount == 89.99

    # Test updating non-existent product
    non_existent = sample_product.model_copy(deep=True)
    non_existent.product_id = "non-existent-id"
    with pytest.raises(FileNotFoundError):
        json_storage.update(non_existent)


def test_delete_product(json_storage, sample_product):
    """Test deleting a product from storage."""
    json_storage.save(sample_product)

    # Verify it exists
    assert json_storage.get(sample_product.product_id) is not None

    # Delete
    json_storage.delete(sample_product.product_id)

    # Verify it's gone
    with pytest.raises(FileNotFoundError):
        json_storage.get(sample_product.product_id)

    # Test deleting non-existent product
    with pytest.raises(FileNotFoundError):
        json_storage.delete("non-existent-id")


def test_list_products(json_storage):
    """Test listing products from storage with various filters."""
    # Create multiple products
    products = []
    for i in range(5):
        product = ProductData(
            url=f"https://example.com/product/{i}",
            product_id=f"{i}",
            title=f"Test Product {i}",
            description=f"This is test product {i}",
            price=ProductPrice(
                amount=10.0 * (i + 1), currency="USD" if i % 2 == 0 else "EUR"
            ),
            brand="Test Brand" if i < 3 else "Other Brand",
            availability="In Stock" if i % 2 == 0 else "Out of Stock",
            extracted_at=datetime.now(),
        )
        products.append(product)
        json_storage.save(product)

    # Test listing all products
    all_products = json_storage.list()
    assert len(all_products) == 5

    # Test with limit
    limited_products = json_storage.list(limit=3)
    assert len(limited_products) == 3

    # Test with filters
    brand_filtered = json_storage.list(filters={"brand": "Test Brand"})
    assert len(brand_filtered) == 3
    assert all(p.brand == "Test Brand" for p in brand_filtered)

    availability_filtered = json_storage.list(filters={"availability": "In Stock"})
    assert len(availability_filtered) == 3
    assert all(p.availability == "In Stock" for p in availability_filtered)

    # Test with sorting
    price_sorted = json_storage.list(sort_by="price.amount", ascending=True)
    prices = [p.price.amount for p in price_sorted]
    assert prices == sorted(prices)

    price_sorted_desc = json_storage.list(sort_by="price.amount", ascending=False)
    prices_desc = [p.price.amount for p in price_sorted_desc]
    assert prices_desc == sorted(prices_desc, reverse=True)


def test_storage_path_creation(temp_storage_dir):
    """Test that the storage path is created if it doesn't exist."""
    # Create nested path that doesn't exist
    nested_path = os.path.join(temp_storage_dir, "nested", "path")

    # Initialize storage with nested path
    config = StorageConfig(
        type="json", path=nested_path, filename_template="{product_id}.json"
    )
    storage = JSONStorage(config)

    # Save a product to trigger directory creation
    product = ProductData(
        url="https://example.com/product/test",
        product_id="test",
        title="Test Product",
        extracted_at=datetime.now(),
    )
    storage.save(product)

    # Verify directory was created
    assert os.path.exists(nested_path)


@pytest.fixture
def storage_dir():
    """Temporary directory for storage tests."""
    temp_dir = mkdtemp()
    yield temp_dir
    # Clean up after the test
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(storage_dir):
    """JSONStorage instance for testing."""
    return JSONStorage(storage_dir)


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
        },
    ]


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
        {"id": product_ids[2], "price": {"current": 35.99, "currency": "USD"}},
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
        {"id": "non-existent-id", "price": {"current": 26.99}},
    ]
    with pytest.raises(ProductNotFoundError):
        await storage.update_products(bad_updates)

    # Test missing ID
    with pytest.raises(ValueError):
        await storage.update_products([{"price": {"current": 17.99}}])

    # Test empty list case
    empty_result = await storage.update_products([])
    assert empty_result == []


@pytest.mark.asyncio
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


if __name__ == "__main__":
    unittest.main()
