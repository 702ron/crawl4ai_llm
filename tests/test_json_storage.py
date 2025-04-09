"""
Unit tests for the JSONStorage implementation.
"""

import os
import json
import shutil
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

import pytest
from pydantic import HttpUrl

from crawl4ai_llm.config import StorageConfig
from crawl4ai_llm.models import ProductData, ProductPrice, ProductImage
from crawl4ai_llm.storage.json_storage import JSONStorage
from crawl4ai_llm.storage.base import ProductNotFoundError, DuplicateProductError, StorageError, StorageConnectionError


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(temp_dir):
    """Create a JSONStorage instance for testing."""
    config = StorageConfig(
        type="json",
        path=temp_dir,
        use_uuid=False,
        create_if_missing=True
    )
    return JSONStorage(config)


@pytest.fixture
def sample_product():
    """Create a sample product for testing."""
    return ProductData(
        title="Test Product",
        url=HttpUrl("https://example.com/product/123"),
        description="This is a test product",
        brand="Test Brand",
        prices=[
            ProductPrice(amount="99.99", currency="USD")
        ],
        images=[
            ProductImage(url=HttpUrl("https://example.com/images/123.jpg"), alt="Product Image")
        ],
        identifiers={"sku": "TEST123"},
        available=True,
        extracted_at=datetime.now()
    )


class TestJSONStorage:
    """Test cases for JSONStorage class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, temp_dir):
        """Test storage initialization."""
        # Test with existing directory
        config = StorageConfig(type="json", path=temp_dir)
        storage = JSONStorage(config)
        assert storage.storage_path == Path(temp_dir)
        
        # Test with non-existent directory
        non_existent = os.path.join(temp_dir, "non_existent")
        config = StorageConfig(type="json", path=non_existent, create_if_missing=True)
        storage = JSONStorage(config)
        assert os.path.exists(non_existent)
        
        # Test with non-writable directory
        read_only_dir = os.path.join(temp_dir, "read_only")
        os.makedirs(read_only_dir)
        os.chmod(read_only_dir, 0o444)  # Read-only
        
        config = StorageConfig(type="json", path=read_only_dir)
        with pytest.raises(StorageConnectionError):
            JSONStorage(config)
    
    @pytest.mark.asyncio
    async def test_save_product(self, storage, sample_product):
        """Test saving a product."""
        product_id = await storage.save_product(sample_product)
        assert product_id is not None
        
        # Check that the file exists
        file_path = storage._get_file_path(product_id)
        assert file_path.exists()
        
        # Check that the index was updated
        index = await storage._load_index()
        assert product_id in index
        assert index[product_id]["title"] == sample_product.title
        assert index[product_id]["brand"] == sample_product.brand
    
    @pytest.mark.asyncio
    async def test_get_product(self, storage, sample_product):
        """Test retrieving a product."""
        product_id = await storage.save_product(sample_product)
        
        # Retrieve the product
        retrieved = await storage.get_product(product_id)
        assert retrieved.title == sample_product.title
        assert str(retrieved.url) == str(sample_product.url)
        assert retrieved.brand == sample_product.brand
        assert len(retrieved.prices) == 1
        assert retrieved.prices[0].amount == sample_product.prices[0].amount
    
    @pytest.mark.asyncio
    async def test_update_product(self, storage, sample_product):
        """Test updating a product."""
        product_id = await storage.save_product(sample_product)
        
        # Modify the product
        updated_product = sample_product.model_copy()
        updated_product.title = "Updated Product"
        updated_product.available = False
        updated_product.prices[0].amount = "79.99"
        
        # Update the product
        result = await storage.update_product(product_id, updated_product)
        assert result is True
        
        # Retrieve the updated product
        retrieved = await storage.get_product(product_id)
        assert retrieved.title == "Updated Product"
        assert retrieved.available is False
        assert retrieved.prices[0].amount == "79.99"
        
        # Check that the index was updated
        index = await storage._load_index()
        assert index[product_id]["title"] == "Updated Product"
        assert index[product_id]["available"] is False
    
    @pytest.mark.asyncio
    async def test_delete_product(self, storage, sample_product):
        """Test deleting a product."""
        product_id = await storage.save_product(sample_product)
        
        # Delete the product
        result = await storage.delete_product(product_id)
        assert result is True
        
        # Check that the file was deleted
        file_path = storage._get_file_path(product_id)
        assert not file_path.exists()
        
        # Check that the index was updated
        index = await storage._load_index()
        assert product_id not in index
        
        # Trying to get the deleted product should raise an error
        with pytest.raises(ProductNotFoundError):
            await storage.get_product(product_id)
    
    @pytest.mark.asyncio
    async def test_list_products(self, storage):
        """Test listing products."""
        # Create several products
        products = []
        for i in range(5):
            product = ProductData(
                title=f"Product {i}",
                url=HttpUrl(f"https://example.com/product/{i}"),
                brand="Brand A" if i % 2 == 0 else "Brand B",
                prices=[
                    ProductPrice(amount=str(10 * (i + 1)), currency="USD")
                ],
                available=i % 2 == 0
            )
            product_id = await storage.save_product(product)
            products.append((product_id, product))
        
        # List all products
        all_products, count = await storage.list_products()
        assert count == 5
        assert len(all_products) == 5
        
        # Filter by brand
        brand_a, count = await storage.list_products(filters={"brand": "Brand A"})
        assert count == 3
        assert all(p.brand == "Brand A" for p in brand_a)
        
        # Filter by availability
        available, count = await storage.list_products(filters={"available": True})
        assert count == 3
        assert all(p.available for p in available)
        
        # Test pagination
        page1, count = await storage.list_products(limit=2, offset=0)
        assert count == 5
        assert len(page1) == 2
        
        page2, count = await storage.list_products(limit=2, offset=2)
        assert count == 5
        assert len(page2) == 2
        
        page3, count = await storage.list_products(limit=2, offset=4)
        assert count == 5
        assert len(page3) == 1
    
    @pytest.mark.asyncio
    async def test_sort_products(self, storage):
        """Test sorting products."""
        # Create products with different prices
        products = []
        for i in range(5):
            price = 50 - i * 10  # 50, 40, 30, 20, 10
            product = ProductData(
                title=f"Product {i}",
                url=HttpUrl(f"https://example.com/product/{i}"),
                prices=[
                    ProductPrice(amount=str(price), currency="USD")
                ]
            )
            await storage.save_product(product)
            products.append(product)
        
        # Sort by price ascending
        asc_products, _ = await storage.list_products(sort_by="price", sort_order="asc")
        prices = [float(p.prices[0].amount) for p in asc_products]
        assert prices == sorted(prices)
        
        # Sort by price descending
        desc_products, _ = await storage.list_products(sort_by="price", sort_order="desc")
        prices = [float(p.prices[0].amount) for p in desc_products]
        assert prices == sorted(prices, reverse=True)
        
        # Sort by title
        title_products, _ = await storage.list_products(sort_by="title", sort_order="asc")
        titles = [p.title for p in title_products]
        assert titles == sorted(titles)
    
    @pytest.mark.asyncio
    async def test_duplicate_product(self, storage, sample_product):
        """Test handling of duplicate products."""
        # Save the product
        product_id = await storage.save_product(sample_product)
        
        # Try to save it again
        with pytest.raises(DuplicateProductError):
            await storage.save_product(sample_product)
    
    @pytest.mark.asyncio
    async def test_product_not_found(self, storage):
        """Test handling of non-existent products."""
        non_existent_id = "non_existent"
        
        # Try to get a non-existent product
        with pytest.raises(ProductNotFoundError):
            await storage.get_product(non_existent_id)
        
        # Try to update a non-existent product
        with pytest.raises(ProductNotFoundError):
            await storage.update_product(non_existent_id, ProductData(
                title="Test",
                url=HttpUrl("https://example.com")
            ))
        
        # Try to delete a non-existent product
        with pytest.raises(ProductNotFoundError):
            await storage.delete_product(non_existent_id)
    
    @pytest.mark.asyncio
    async def test_id_generation(self, storage):
        """Test product ID generation."""
        # Test with identifiers
        product1 = ProductData(
            title="Product with SKU",
            url=HttpUrl("https://example.com/product/123"),
            identifiers={"sku": "TEST123"}
        )
        id1 = storage._get_product_id(product1)
        assert id1 == "sku_TEST123"
        
        # Test with URL
        product2 = ProductData(
            title="Product with URL only",
            url=HttpUrl("https://example.com/product/test-product")
        )
        id2 = storage._get_product_id(product2)
        assert "test-product" in id2
        
        # Test with UUID
        config = StorageConfig(type="json", path=storage.storage_path, use_uuid=True)
        uuid_storage = JSONStorage(config)
        id3 = uuid_storage._get_product_id(product1)
        # UUID format: 8-4-4-4-12 hex digits
        assert len(id3) == 36
        assert id3.count("-") == 4