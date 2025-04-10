"""
Tests for metadata extraction functionality.
"""

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from crawl4ai_llm.extraction.product_extractor import ProductExtractor
from crawl4ai_llm.models import ProductData, ProductReview


@pytest.fixture
def mock_crawl_result():
    """Fixture that provides a mock crawl result with metadata."""
    return {
        "success": True,
        "html": "<html><body>Product page with metadata</body></html>",
        "extracted_content": {
            "title": "Premium Test Product",
            "description": "This is a test product with full metadata",
            "price": {
                "current_price": 99.99,
                "currency": "USD",
                "original_price": 129.99,
                "discount_percentage": 23.0
            },
            "brand": "Test Brand",
            "sku": "TEST123",
            "availability": "In Stock",
            "rating": 4.7,
            "review_count": 125,
            "reviews": [
                {
                    "reviewer_name": "John Doe",
                    "rating": 5.0,
                    "title": "Great product!",
                    "content": "I've been using this for a week and it's amazing!",
                    "date": "2023-05-10",
                    "verified_purchase": True
                },
                {
                    "reviewer_name": "Jane Smith",
                    "rating": 4.0,
                    "title": "Good but not perfect",
                    "content": "It works well but has some minor issues.",
                    "date": "2023-04-22",
                    "verified_purchase": True
                }
            ],
            "images": [
                {"url": "https://example.com/image1.jpg", "alt_text": "Product front view"}
            ],
            "attributes": [
                {"name": "Color", "value": "Black"},
                {"name": "Size", "value": "Medium"}
            ],
            "variants": [
                {
                    "id": "VAR-BLACK",
                    "name": "Black",
                    "price": {"current_price": 99.99, "currency": "USD"},
                    "attributes": [{"name": "Color", "value": "Black"}]
                },
                {
                    "id": "VAR-RED",
                    "name": "Red",
                    "price": {"current_price": 99.99, "currency": "USD"},
                    "attributes": [{"name": "Color", "value": "Red"}]
                }
            ],
            # Additional metadata fields
            "shipping_info": "Free shipping on orders over $50",
            "warranty": "2-year limited warranty",
            "dimensions": "10 x 5 x 2 inches",
            "weight": "2 lbs",
            "material": "Aluminum",
            "seller": "Test Manufacturer Inc.",
            "release_date": "2023-01-15"
        }
    }


@pytest.mark.asyncio
async def test_metadata_extraction(mock_crawl_result):
    """Test that additional metadata fields are properly extracted."""
    # Arrange
    test_url = "https://example.com/product"
    product_extractor = ProductExtractor()
    
    # Mock the crawler to return our test data
    product_extractor.crawler = MagicMock()
    product_extractor.crawler.crawl.return_value = mock_crawl_result
    
    # Act
    result = await product_extractor.extract(url=test_url)
    
    # Assert - Basic product information
    assert isinstance(result, ProductData)
    assert result.title == "Premium Test Product"
    assert result.price.current_price == 99.99
    assert result.brand == "Test Brand"
    
    # Assert - Additional metadata
    assert result.shipping_info == "Free shipping on orders over $50"
    assert result.warranty == "2-year limited warranty"
    assert result.dimensions == "10 x 5 x 2 inches"
    assert result.weight == "2 lbs"
    assert result.material == "Aluminum"
    assert result.seller == "Test Manufacturer Inc."
    assert result.release_date == "2023-01-15"
    
    # Assert - Reviews
    assert len(result.reviews) == 2
    assert isinstance(result.reviews[0], ProductReview)
    assert result.reviews[0].reviewer_name == "John Doe"
    assert result.reviews[0].rating == 5.0
    assert result.reviews[0].verified_purchase is True
    
    # Assert - Variants and attributes
    assert len(result.variants) == 2
    assert result.variants[0].id == "VAR-BLACK"
    assert len(result.attributes) == 2
    assert result.attributes[0].name == "Color"
    assert result.attributes[0].value == "Black"


@pytest.mark.asyncio
async def test_metadata_extraction_with_llm_strategy(mock_crawl_result):
    """Test metadata extraction using the LLM strategy."""
    # Arrange
    test_url = "https://example.com/product"
    product_extractor = ProductExtractor()
    
    # Mock the crawler to return our test data
    product_extractor.crawler = MagicMock()
    product_extractor.crawler.crawl.return_value = mock_crawl_result
    
    # Act - Use LLM strategy
    result = await product_extractor.extract(url=test_url, strategy="llm")
    
    # Assert - Basic product information
    assert isinstance(result, ProductData)
    assert result.title == "Premium Test Product"
    
    # Assert - Additional metadata
    assert result.shipping_info == "Free shipping on orders over $50"
    assert result.warranty == "2-year limited warranty"
    assert result.dimensions == "10 x 5 x 2 inches"
    assert result.weight == "2 lbs"
    assert result.material == "Aluminum"
    assert result.seller == "Test Manufacturer Inc."
    assert result.release_date == "2023-01-15"


@pytest.mark.asyncio
async def test_metadata_extraction_with_missing_fields():
    """Test metadata extraction when fields are missing."""
    # Arrange
    test_url = "https://example.com/product"
    product_extractor = ProductExtractor()
    
    # Create a minimal crawl result with limited metadata
    limited_crawl_result = {
        "success": True,
        "html": "<html><body>Product page with minimal metadata</body></html>",
        "extracted_content": {
            "title": "Basic Test Product",
            "price": {
                "current_price": 49.99,
                "currency": "USD"
            },
            # Only include a few metadata fields
            "dimensions": "5 x 3 x 1 inches",
            "warranty": "1-year warranty"
        }
    }
    
    # Mock the crawler to return our limited test data
    product_extractor.crawler = MagicMock()
    product_extractor.crawler.crawl.return_value = limited_crawl_result
    
    # Act
    result = await product_extractor.extract(url=test_url)
    
    # Assert - Basic product information
    assert isinstance(result, ProductData)
    assert result.title == "Basic Test Product"
    assert result.price.current_price == 49.99
    
    # Assert - Should have the included metadata
    assert result.dimensions == "5 x 3 x 1 inches"
    assert result.warranty == "1-year warranty"
    
    # Assert - Missing metadata fields should be None
    assert result.shipping_info is None
    assert result.weight is None
    assert result.material is None
    assert result.seller is None
    assert result.release_date is None
    
    # Assert - These collections should be empty but initialized
    assert result.reviews == []
    assert result.variants == []
    assert result.attributes == [] 