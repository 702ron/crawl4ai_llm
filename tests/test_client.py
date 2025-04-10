"""
Tests for the Crawl4AI LLM client library.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from unittest import mock

import pytest
from pydantic import HttpUrl

from crawl4ai_llm.client import Crawl4AIClient
from crawl4ai_llm.client.models import (ExportFormat, ExtractionMethod,
                                       ExtractionRequest, ProductFilter)
from crawl4ai_llm.models import ProductData, ProductPrice


# Sample product data for testing
SAMPLE_PRODUCT = {
    "title": "Test Product",
    "price": {
        "current_price": 99.99,
        "currency": "USD"
    },
    "images": [
        {
            "url": "https://example.com/image.jpg",
            "alt_text": "Product Image"
        }
    ],
    "description": "This is a test product",
    "brand": "Test Brand",
    "availability": "In Stock"
}


# Mock response for client requests
class MockResponse:
    def __init__(self, data: Dict[str, Any], status: int = 200):
        self.data = data
        self.status = status
    
    async def json(self) -> Dict[str, Any]:
        return self.data
    
    async def text(self) -> str:
        if isinstance(self.data, str):
            return self.data
        return json.dumps(self.data)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass


@pytest.fixture
def client():
    """Create a client instance with a mocked session."""
    client = Crawl4AIClient(api_key="test_api_key")
    # Replace the _ensure_session method to avoid creating a real session
    client._ensure_session = mock.AsyncMock()
    client._request = mock.AsyncMock()
    return client


@pytest.mark.asyncio
async def test_extract_product(client):
    """Test product extraction."""
    # Setup mock response
    client._request.return_value = {
        "url": "https://example.com/product",
        "data": SAMPLE_PRODUCT,
        "metadata": {
            "product_id": "test123",
            "extraction_time": 1.5,
            "strategy": "auto",
            "fallback_used": False,
            "timestamp": datetime.now().isoformat(),
            "messages": ["Extraction successful"]
        }
    }
    
    # Create extraction request
    request = ExtractionRequest(
        url="https://example.com/product",
        extraction_method=ExtractionMethod.AUTO
    )
    
    # Extract product
    result = await client.extract_product(request)
    
    # Check result
    assert result.success is True
    assert result.product_id == "test123"
    assert result.product is not None
    assert result.product.title == "Test Product"
    assert result.product.price.current_price == 99.99
    assert result.messages == ["Extraction successful"]
    
    # Verify client called the API correctly
    client._request.assert_called_once_with(
        "POST", 
        "/extract", 
        json_data={
            "url": "https://example.com/product",
            "strategy": "auto",
            "fallback": True,
            "cache": True
        }
    )


@pytest.mark.asyncio
async def test_get_product(client):
    """Test getting a product by ID."""
    # Setup mock response
    client._request.return_value = SAMPLE_PRODUCT
    
    # Get product
    product = await client.get_product("test123")
    
    # Check result
    assert product is not None
    assert product.title == "Test Product"
    assert product.price.current_price == 99.99
    
    # Verify client called the API correctly
    client._request.assert_called_once_with("GET", "/products/test123")


@pytest.mark.asyncio
async def test_search_products(client):
    """Test searching for products with filters."""
    # Setup mock response
    client._request.return_value = [
        {**SAMPLE_PRODUCT, "metadata": {"total_count": 1}}
    ]
    
    # Create filter
    product_filter = ProductFilter(
        brand="Test Brand",
        price_min=50,
        price_max=150
    )
    
    # Search products
    result = await client.search_products(
        filter=product_filter,
        limit=10,
        offset=0,
        sort_by="price",
        sort_order="asc"
    )
    
    # Check result
    assert result.total == 1
    assert len(result.products) == 1
    assert result.products[0].title == "Test Product"
    
    # Verify client called the API correctly
    client._request.assert_called_once_with(
        "GET", 
        "/products", 
        params={
            "limit": 10,
            "offset": 0,
            "sort_by": "price",
            "sort_order": "asc",
            "brand": "Test Brand",
            "price_min": 50,
            "price_max": 150
        }
    )


@pytest.mark.asyncio
async def test_export_json(client):
    """Test exporting products to JSON."""
    # Setup mock response
    client._request.return_value = {
        "products": [SAMPLE_PRODUCT],
        "total": 1,
        "limit": 100,
        "offset": 0
    }
    
    # Export products
    result = await client.export_products(
        product_ids=["test123"],
        format=ExportFormat.JSON,
        include_metadata=True
    )
    
    # Check result
    assert len(result) == 1
    assert result[0]["title"] == "Test Product"
    
    # Verify client called the API correctly
    client._request.assert_called_once_with(
        "GET", 
        "/export/json", 
        params={
            "ids": "test123",
            "include_metadata": "true",
            "flatten": "false"
        }
    ) 