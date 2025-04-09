"""
Tests for JSON file-based storage implementation.
"""

import os
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
import pytest
from pydantic import HttpUrl

from crawl4ai_llm.config import StorageConfig
from crawl4ai_llm.models import ProductData, ProductPrice, ProductImage
from crawl4ai_llm.storage.json_storage import JSONStorage
from crawl4ai_llm.storage.base import ProductNotFoundError, DuplicateProductError, StorageConnectionError

# Test fixtures

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def storage_config(temp_dir):
    """Create a storage configuration for testing."""
    return StorageConfig(
        type="json",
        path=temp_dir,
        use_uuid=False,
        create_if_missing=True,
        lock_timeout=10,
        filename_template="{id}.json"
    )

@pytest.fixture
def storage(storage_config):
    """Create a JSON storage instance for testing."""
    return JSONStorage(storage_config)

@pytest.fixture
def sample_product():
    """Create a sample product for testing."""
    return ProductData(
        url=HttpUrl("https://example.com/product1"),
        title="Test Product 1",
        description="This is a test product",
        brand="Test Brand",
        available=True,
        extracted_at=datetime.now(),
        prices=[
            ProductPrice(amount=19.99, currency="USD", type="regular")
        ],
        images=[
            ProductImage(url=HttpUrl("https://example.com/image1.jpg"), alt="Test Image 1")
        ],
        attributes={
            "color": "red",
            "size": "medium"
        },
        identifiers={
            "sku": "SKU123456",
            "upc": "123456789012"
        }
    )

@pytest.fixture
def sample_products():
    """Create multiple sample products for testing."""
    return [
        ProductData(
            url=HttpUrl("https://example.com/product1"),
            title="Test Product 1",
            description="This is test product 1",
            brand="Brand A",
            available=True,
            extracted_at=datetime.now(),
            prices=[
                ProductPrice(amount=19.99, currency="USD", type="regular")
            ],
            identifiers={"sku": "SKU1"}
        ),
        ProductData(
            url=HttpUrl("https://example.com/product2"),
            title="Test Product 2",
            description="This is test product 2",
            brand="Brand B",
            available=False,
            extracted_at=datetime.now(),
            prices=[
                ProductPrice(amount=29.99, currency="USD", type="regular")
            ],
            identifiers={"sku": "SKU2"}
        ),
        ProductData(
            url=HttpUrl("https://example.com/product3"),
            title="Test Product 3",
            description="This is test product 3",
            brand="Brand A",
            available=True,
            extracted_at=datetime.now(),
            prices=[
                ProductPrice(amount=9.99, currency="USD", type="regular")
            ],
            identifiers={"sku": "SKU3"}
        )
    ]

# Test cases

@pytest.mark.asyncio
async def test_init_storage(temp_dir):
    """Test storage initialization."""
    config = StorageConfig(
        type="json",
        path=temp_dir,
        use_uuid=False,
        create_if_missing=True
    )
    
    storage = JSONStorage(config)
    assert storage.storage_path == Path(temp_dir)
    assert storage.index_path == Path(temp_dir) / "index.json"

@pytest.mark.asyncio
async def test_init_storage_create_dir(temp_dir):
    """Test storage initialization with directory creation."""
    new_path = os.path.join(temp_dir, "storage")
    config = StorageConfig(
        type="json",
        path=new_path,
        use_uuid=False,
        create_if_missing=True
    )
    
    storage = JSONStorage(config)
    assert storage.storage_path == Path(new_path)
    assert os.path.exists(new_path)

@pytest.mark.asyncio
async def test_save_product(storage, sample_product):
    """Test saving a product."""
    product_id = await storage.save_product(sample_product)
    assert product_id == "sku_SKU123456"
    
    # Check that the product file exists
    file_path = storage._get_file_path(product_id)
    assert file_path.exists()
    
    # Check that the index was updated
    index = await storage._load_index()
    assert product_id in index
    assert index[product_id]["title"] == sample_product.title

@pytest.mark.asyncio
async def test_save_products_batch(storage, sample_products):
    """Test saving multiple products in a batch."""
    product_ids = await storage.save_products(sample_products)
    assert len(product_ids) == 3
    
    # Check that all product files exist
    for product_id in product_ids:
        file_path = storage._get_file_path(product_id)
        assert file_path.exists()
    
    # Check that the index was updated with all products
    index = await storage._load_index()
    assert len(index) == 3
    
    # Verify specific product in index
    assert "sku_SKU1" in index
    assert index["sku_SKU1"]["title"] == "Test Product 1"
    assert "sku_SKU2" in index
    assert index["sku_SKU2"]["title"] == "Test Product 2"

@pytest.mark.asyncio
async def test_get_product(storage, sample_product):
    """Test retrieving a product."""
    product_id = await storage.save_product(sample_product)
    
    retrieved = await storage.get_product(product_id)
    assert retrieved.title == sample_product.title
    assert retrieved.description == sample_product.description
    assert retrieved.brand == sample_product.brand
    assert retrieved.url == sample_product.url

@pytest.mark.asyncio
async def test_get_products_batch(storage, sample_products):
    """Test retrieving multiple products in a batch."""
    product_ids = await storage.save_products(sample_products)
    
    retrieved = await storage.get_products(product_ids)
    assert len(retrieved) == 3
    
    # Verify products are retrieved correctly
    titles = [p.title for p in retrieved]
    assert "Test Product 1" in titles
    assert "Test Product 2" in titles
    assert "Test Product 3" in titles

@pytest.mark.asyncio
async def test_get_products_partial_success(storage, sample_products):
    """Test retrieving multiple products with some not found."""
    product_ids = await storage.save_products(sample_products[:2])
    
    # Try to get 3 products, but only 2 exist
    retrieved = await storage.get_products(["sku_SKU1", "sku_SKU2", "sku_SKU3"])
    assert len(retrieved) == 2
    
    titles = [p.title for p in retrieved]
    assert "Test Product 1" in titles
    assert "Test Product 2" in titles

@pytest.mark.asyncio
async def test_update_product(storage, sample_product):
    """Test updating a product."""
    product_id = await storage.save_product(sample_product)
    
    # Update the product
    updated_product = sample_product.model_copy(deep=True)
    updated_product.title = "Updated Product Title"
    updated_product.available = False
    
    result = await storage.update_product(product_id, updated_product)
    assert result is True
    
    # Retrieve the updated product
    retrieved = await storage.get_product(product_id)
    assert retrieved.title == "Updated Product Title"
    assert retrieved.available is False
    
    # Check index was updated
    index = await storage._load_index()
    assert index[product_id]["title"] == "Updated Product Title"
    assert index[product_id]["available"] is False

@pytest.mark.asyncio
async def test_update_products_batch(storage, sample_products):
    """Test updating multiple products in a batch."""
    product_ids = await storage.save_products(sample_products)
    
    # Create updates
    updates = {}
    for i, pid in enumerate(product_ids):
        product = await storage.get_product(pid)
        updated = product.model_copy(deep=True)
        updated.title = f"Updated Product {i+1}"
        updated.available = not product.available
        updates[pid] = updated
    
    # Update all products
    results = await storage.update_products(updates)
    
    # Verify all updates succeeded
    assert all(results.values())
    assert len(results) == 3
    
    # Check products were actually updated
    for pid in product_ids:
        retrieved = await storage.get_product(pid)
        assert retrieved.title.startswith("Updated Product")
    
    # Check index was updated
    index = await storage._load_index()
    for pid in product_ids:
        assert index[pid]["title"].startswith("Updated Product")

@pytest.mark.asyncio
async def test_delete_product(storage, sample_product):
    """Test deleting a product."""
    product_id = await storage.save_product(sample_product)
    file_path = storage._get_file_path(product_id)
    
    # Delete the product
    result = await storage.delete_product(product_id)
    assert result is True
    
    # Check file was removed
    assert not file_path.exists()
    
    # Check index was updated
    index = await storage._load_index()
    assert product_id not in index
    
    # Check product is not retrievable
    with pytest.raises(ProductNotFoundError):
        await storage.get_product(product_id)

@pytest.mark.asyncio
async def test_delete_products_batch(storage, sample_products):
    """Test deleting multiple products in a batch."""
    product_ids = await storage.save_products(sample_products)
    
    # Delete products
    results = await storage.delete_products(product_ids)
    
    # Verify all deletions succeeded
    assert all(results.values())
    assert len(results) == 3
    
    # Check files were removed
    for pid in product_ids:
        file_path = storage._get_file_path(pid)
        assert not file_path.exists()
    
    # Check index was updated
    index = await storage._load_index()
    assert len(index) == 0
    
    # Check products are not retrievable
    for pid in product_ids:
        with pytest.raises(ProductNotFoundError):
            await storage.get_product(pid)

@pytest.mark.asyncio
async def test_list_products(storage, sample_products):
    """Test listing products."""
    await storage.save_products(sample_products)
    
    products, count = await storage.list_products()
    assert count == 3
    assert len(products) == 3

@pytest.mark.asyncio
async def test_list_products_with_filters(storage, sample_products):
    """Test listing products with filters."""
    await storage.save_products(sample_products)
    
    # Filter by brand
    products, count = await storage.list_products({"brand": "Brand A"})
    assert count == 2
    assert len(products) == 2
    assert all(p.brand == "Brand A" for p in products)
    
    # Filter by availability
    products, count = await storage.list_products({"available": True})
    assert count == 2
    assert len(products) == 2
    assert all(p.available for p in products)
    
    # Filter by brand and availability
    products, count = await storage.list_products({
        "brand": "Brand A",
        "available": True
    })
    assert count == 2
    assert len(products) == 2
    assert all(p.brand == "Brand A" and p.available for p in products)

@pytest.mark.asyncio
async def test_list_products_pagination(storage, sample_products):
    """Test listing products with pagination."""
    await storage.save_products(sample_products)
    
    # First page
    products, count = await storage.list_products(limit=2, offset=0)
    assert count == 3  # Total count should be 3
    assert len(products) == 2  # But only 2 returned due to limit
    
    # Second page
    products, count = await storage.list_products(limit=2, offset=2)
    assert count == 3
    assert len(products) == 1  # Only 1 remaining product

@pytest.mark.asyncio
async def test_list_products_sorting(storage, sample_products):
    """Test listing products with sorting."""
    await storage.save_products(sample_products)
    
    # Sort by title ascending
    products, _ = await storage.list_products(sort_by="title", sort_order="asc")
    titles = [p.title for p in products]
    assert titles == ["Test Product 1", "Test Product 2", "Test Product 3"]
    
    # Sort by title descending
    products, _ = await storage.list_products(sort_by="title", sort_order="desc")
    titles = [p.title for p in products]
    assert titles == ["Test Product 3", "Test Product 2", "Test Product 1"]
    
    # Sort by price ascending
    products, _ = await storage.list_products(sort_by="price", sort_order="asc")
    prices = [p.prices[0].amount for p in products]
    assert prices == [9.99, 19.99, 29.99]
    
    # Sort by price descending
    products, _ = await storage.list_products(sort_by="price", sort_order="desc")
    prices = [p.prices[0].amount for p in products]
    assert prices == [29.99, 19.99, 9.99]

@pytest.mark.asyncio
async def test_product_not_found(storage):
    """Test handling of non-existent products."""
    with pytest.raises(ProductNotFoundError):
        await storage.get_product("non_existent_id")
    
    with pytest.raises(ProductNotFoundError):
        await storage.update_product("non_existent_id", 
                                    ProductData(
                                        url=HttpUrl("https://example.com/product"),
                                        title="Test Product"
                                    ))
    
    with pytest.raises(ProductNotFoundError):
        await storage.delete_product("non_existent_id")

@pytest.mark.asyncio
async def test_duplicate_product(storage, sample_product):
    """Test handling of duplicate products."""
    product_id = await storage.save_product(sample_product)
    
    # Try to save the same product again
    with pytest.raises(DuplicateProductError):
        await storage.save_product(sample_product)

@pytest.mark.asyncio
async def test_storage_connection_error(temp_dir):
    """Test handling of storage connection errors."""
    # Create a read-only directory
    read_only_dir = os.path.join(temp_dir, "read_only")
    os.mkdir(read_only_dir)
    os.chmod(read_only_dir, 0o500)  # read and execute, but not write
    
    config = StorageConfig(
        type="json",
        path=read_only_dir,
        use_uuid=False,
        create_if_missing=False
    )
    
    storage = JSONStorage(config)
    
    # Try to save a product to a read-only directory
    with pytest.raises(StorageConnectionError):
        await storage.save_product(
            ProductData(
                url=HttpUrl("https://example.com/product"),
                title="Test Product"
            )
        )
    
    # Restore permissions
    os.chmod(read_only_dir, 0o700)

@pytest.mark.asyncio
async def test_concurrent_batch_operations(storage, sample_products, sample_product):
    """Test concurrent batch operations."""
    import asyncio
    
    # Save initial products
    await storage.save_products(sample_products)
    
    # Define some concurrent operations
    async def batch_update():
        updates = {}
        products, _ = await storage.list_products()
        for product in products:
            product_id = storage._get_product_id(product)
            updated = product.model_copy(deep=True)
            updated.title = f"{product.title} (Updated)"
            updates[product_id] = updated
        return await storage.update_products(updates)
    
    async def batch_save():
        new_products = []
        for i in range(3):
            new_product = sample_product.model_copy(deep=True)
            new_product.title = f"New Batch Product {i+1}"
            new_product.identifiers = {"sku": f"NEW{i+1}"}
            new_products.append(new_product)
        return await storage.save_products(new_products)
    
    # Run operations concurrently
    update_task = asyncio.create_task(batch_update())
    save_task = asyncio.create_task(batch_save())
    
    update_results = await update_task
    save_results = await save_task
    
    # Verify results
    assert all(update_results.values())
    assert len(save_results) == 3
    
    # Verify all products are in the index
    products, count = await storage.list_products()
    assert count == 6  # 3 original + 3 new
    
    # Check that updates were applied
    updated_titles = [p.title for p in products if "(Updated)" in p.title]
    assert len(updated_titles) == 3
    
    # Check that new products were added
    new_titles = [p.title for p in products if "New Batch Product" in p.title]
    assert len(new_titles) == 3