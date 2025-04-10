"""
Unit tests for the product data models.
"""

import pytest
from pydantic import ValidationError

from crawl4ai_llm.models import ProductData, ProductImage, ProductPrice


def test_product_price_model():
    """Test the ProductPrice model validation."""
    # Valid price
    price = ProductPrice(current_price=99.99, currency="USD")
    assert price.current_price == 99.99
    assert price.currency == "USD"
    assert price.original_price is None

    # Valid price with all fields
    price = ProductPrice(
        current_price=79.99,
        currency="EUR",
        original_price=99.99,
        discount_percentage=20.0,
        discount_amount=20.0,
        price_per_unit="€79.99/kg",
    )
    assert price.current_price == 79.99
    assert price.currency == "EUR"
    assert price.original_price == 99.99
    assert price.discount_percentage == 20.0

    # Invalid price (missing required field)
    with pytest.raises(ValidationError):
        ProductPrice(currency="USD")

    # Invalid price (wrong type)
    with pytest.raises(ValidationError):
        ProductPrice(current_price="not-a-number", currency="USD")


def test_product_image_model():
    """Test the ProductImage model validation."""
    # Valid image
    image = ProductImage(url="https://example.com/image.jpg")
    assert image.url == "https://example.com/image.jpg"
    assert image.alt_text is None

    # Valid image with all fields
    image = ProductImage(
        url="https://example.com/image.jpg", alt_text="Product Image", position=1
    )
    assert image.url == "https://example.com/image.jpg"
    assert image.alt_text == "Product Image"
    assert image.position == 1

    # Invalid image (missing required field)
    with pytest.raises(ValidationError):
        ProductImage(alt_text="Product Image")

    # Invalid image (invalid URL)
    with pytest.raises(ValidationError):
        ProductImage(url="not-a-url")


def test_product_data_model():
    """Test the ProductData model validation."""
    # Valid minimal product
    product = ProductData(
        title="Test Product", price={"current_price": 99.99, "currency": "USD"}
    )
    assert product.title == "Test Product"
    assert product.price.current_price == 99.99
    assert product.extraction_success is True

    # Valid complete product
    product = ProductData(
        title="Complete Test Product",
        description="This is a test product with complete data",
        short_description="Test product",
        brand="Test Brand",
        price={
            "current_price": 79.99,
            "currency": "USD",
            "original_price": 99.99,
            "discount_percentage": 20.0,
        },
        images=[
            {"url": "https://example.com/image1.jpg", "alt_text": "Image 1"},
            {"url": "https://example.com/image2.jpg", "alt_text": "Image 2"},
        ],
        sku="TEST-123",
        upc="123456789012",
        category=["Electronics", "Computers"],
        availability="In Stock",
        url="https://example.com/products/test-123",
        rating=4.5,
        review_count=100,
    )
    assert product.title == "Complete Test Product"
    assert product.brand == "Test Brand"
    assert product.price.current_price == 79.99
    assert product.price.discount_percentage == 20.0
    assert len(product.images) == 2
    assert product.images[0].url == "https://example.com/image1.jpg"
    assert product.sku == "TEST-123"
    assert product.upc == "123456789012"
    assert product.rating == 4.5
    assert product.review_count == 100

    # Invalid product (missing required field)
    with pytest.raises(ValidationError):
        ProductData(price={"current_price": 99.99, "currency": "USD"})

    # Invalid product (invalid price)
    with pytest.raises(ValidationError):
        ProductData(title="Test Product", price={"currency": "USD"})
