"""
Tests for the data processing module.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from crawl4ai_llm.models import (ProductAttribute, ProductData, ProductImage,
                                 ProductPrice, ProductReview)
from crawl4ai_llm.processing.data_processor import DataProcessor


class TestDataProcessor:
    """Test suite for the DataProcessor class."""

    def setup_method(self):
        """Set up a DataProcessor instance for each test."""
        self.processor = DataProcessor()

    def test_clean_text(self):
        """Test text cleaning functionality."""
        # Test extra whitespace removal
        assert self.processor.clean_text("  Hello   World  ") == "Hello World"

        # Test HTML removal
        assert self.processor.clean_text("<p>Hello</p> <b>World</b>") == "Hello World"

        # Test HTML entity handling
        assert self.processor.clean_text("Price &amp; Value") == "Price Value"

        # Test None handling
        assert self.processor.clean_text(None) == ""

    def test_normalize_price(self):
        """Test price normalization functionality."""
        # Test USD price
        result = self.processor.normalize_price("$10.99")
        assert result["amount"] == Decimal("10.99")
        assert result["currency"] == "USD"

        # Test EUR price
        result = self.processor.normalize_price("€15,99")
        assert result["amount"] == Decimal("15.99")
        assert result["currency"] == "EUR"

        # Test price with thousand separator
        result = self.processor.normalize_price("$1,234.56")
        assert result["amount"] == Decimal("1234.56")
        assert result["currency"] == "USD"

        # Test European style price
        result = self.processor.normalize_price("€1.234,56")
        assert result["amount"] == Decimal("1234.56")
        assert result["currency"] == "EUR"

        # Test price with text
        result = self.processor.normalize_price("Price: $24.99")
        assert result["amount"] == Decimal("24.99")
        assert result["currency"] == "USD"

        # Test invalid price
        result = self.processor.normalize_price("Out of stock")
        assert result["amount"] == Decimal("0")
        assert result["currency"] == "USD"

    def test_standardize_unit(self):
        """Test unit standardization functionality."""
        # Test weight conversion
        result = self.processor.standardize_unit("500g", "weight")
        assert result["value"] == 0.5
        assert result["unit"] == "kg"
        assert result["original_value"] == 500
        assert result["original_unit"] == "g"

        # Test length conversion
        result = self.processor.standardize_unit("24in", "length")
        assert result["value"] == pytest.approx(0.6096)
        assert result["unit"] == "m"

        # Test auto unit type detection
        result = self.processor.standardize_unit("750ml")
        assert result["value"] == 0.75
        assert result["unit"] == "l"

        # Test invalid format
        result = self.processor.standardize_unit("one kilogram")
        assert result["value"] == "one kilogram"
        assert result["unit"] is None

        # Test None handling
        result = self.processor.standardize_unit(None)
        assert result["value"] is None
        assert result["unit"] is None

    def test_process_product_data(self):
        """Test full product data processing."""
        # Create a sample product with various fields to process
        product = ProductData(
            title="  <b>Test Product</b> &amp; Co.  ",
            description="<p>This is a test product</p>",
            brand="  Brand Name  ",
            prices=[
                ProductPrice(amount="$24.99", currency="USD"),
                ProductPrice(amount="€22,50", currency="EUR"),
            ],
            images=[
                ProductImage(url="//example.com/image.jpg", alt="Product Image"),
                ProductImage(
                    url="https://example.com/image2.jpg", alt="<b>Another</b> Image"
                ),
            ],
            attributes=[
                ProductAttribute(name="Weight", value="500g"),
                ProductAttribute(name="Dimensions", value="24in x 12in x 6in"),
            ],
            reviews=[
                ProductReview(
                    text="Great product!",
                    author="John Doe",
                    rating="8",
                    max_rating="10",
                )
            ],
            identifiers={"sku": "ABC123", "upc": "123456789012"},
        )

        # Process the product
        processed = self.processor.process_product_data(product)

        # Check text cleaning
        assert processed.title == "Test Product Co."
        assert processed.description == "This is a test product"
        assert processed.brand == "Brand Name"

        # Check price normalization
        assert processed.prices[0].amount == "24.99"
        assert processed.prices[0].currency == "USD"
        assert processed.prices[1].amount == "22.50"
        assert processed.prices[1].currency == "EUR"

        # Check image processing
        assert processed.images[0].url == "https://example.com/image.jpg"
        assert processed.images[0].alt == "Product Image"
        assert processed.images[1].alt == "Another Image"

        # Check attribute processing
        assert processed.attributes[0].name == "Weight"
        assert processed.attributes[0].value == "500g"
        assert processed.attributes[0].standardized_value["value"] == 0.5
        assert processed.attributes[0].standardized_value["unit"] == "kg"

        # Check review processing
        assert processed.reviews[0].text == "Great product!"
        assert processed.reviews[0].author == "John Doe"
        assert processed.reviews[0].normalized_rating == 4.0

        # Check metadata was added
        assert "processed_at" in processed.metadata
        assert "processor_version" in processed.metadata

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Minimal product
        minimal_product = ProductData(
            title="Minimal Product", prices=[ProductPrice(amount="10", currency="USD")]
        )

        processed = self.processor.process_product_data(minimal_product)
        assert processed.title == "Minimal Product"

        # Product with empty fields
        empty_fields_product = ProductData(
            title="", description=None, brand="", prices=[]
        )

        processed = self.processor.process_product_data(empty_fields_product)
        assert processed.title == ""
        assert processed.description is None
        assert processed.brand == ""
        assert processed.prices == []
