"""
Unit tests for the ContentProcessor class.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

from crawl4ai_llm.models import ProductData
from crawl4ai_llm.processing import DataProcessingError
from crawl4ai_llm.processing.data_processor import ContentProcessor


class TestContentProcessor(unittest.TestCase):
    """
    Test case for the ContentProcessor class.
    """

    def setUp(self):
        """
        Set up test fixtures.
        """
        # Create sample products for testing
        self.product = ProductData(
            url="https://example.com/product",
            title="Sample Product Title",
            brand="Sample Brand",
            price=99.99,
            currency="USD",
            description="This is a sample product description.",
            sku="SAMPLE123",
            model_number="MODEL456",
            availability="In Stock",
            metadata={"color": "blue", "size": "medium"}
        )
        
        # Initialize processor with default settings
        self.processor = ContentProcessor()
    
    def test_initialization(self):
        """
        Test that ContentProcessor initializes properly.
        """
        # Default settings
        processor = ContentProcessor()
        self.assertEqual(processor.clean_whitespace, True)
        self.assertEqual(processor.normalize_text, True)
        self.assertEqual(processor.convert_prices, True)
        
        # Custom settings
        processor = ContentProcessor(
            clean_whitespace=False,
            normalize_text=False,
            convert_prices=False
        )
        self.assertEqual(processor.clean_whitespace, False)
        self.assertEqual(processor.normalize_text, False)
        self.assertEqual(processor.convert_prices, False)
    
    def test_clean_text(self):
        """
        Test text cleaning functionality.
        """
        # Test with extra whitespace
        text = "  This   has \t extra \n whitespace  "
        cleaned = self.processor.clean_text(text)
        self.assertEqual(cleaned, "This has extra whitespace")
        
        # Test with HTML entities
        text = "This &amp; that &lt; those &gt; these"
        cleaned = self.processor.clean_text(text)
        self.assertEqual(cleaned, "This & that < those > these")
        
        # Test with None
        self.assertIsNone(self.processor.clean_text(None))
        
        # Test with empty string
        self.assertEqual(self.processor.clean_text(""), "")
    
    def test_normalize_price(self):
        """
        Test price normalization.
        """
        # Test standard format
        self.assertEqual(self.processor.normalize_price("$99.99"), 99.99)
        
        # Test comma as thousands separator
        self.assertEqual(self.processor.normalize_price("$1,099.99"), 1099.99)
        
        # Test without currency symbol
        self.assertEqual(self.processor.normalize_price("99.99"), 99.99)
        
        # Test with different currency symbols
        self.assertEqual(self.processor.normalize_price("€99.99"), 99.99)
        self.assertEqual(self.processor.normalize_price("£99.99"), 99.99)
        
        # Test with commas as decimal separator
        self.assertEqual(self.processor.normalize_price("99,99 €"), 99.99)
        
        # Test with spaces
        self.assertEqual(self.processor.normalize_price(" $99.99 "), 99.99)
        
        # Test with non-price string
        with self.assertRaises(ValueError):
            self.processor.normalize_price("not a price")
        
        # Test with None
        with self.assertRaises(ValueError):
            self.processor.normalize_price(None)
    
    def test_standardize_unit(self):
        """
        Test unit standardization.
        """
        # Test weight conversions
        self.assertEqual(self.processor.standardize_unit("500g", "weight"), "0.5 kg")
        self.assertEqual(self.processor.standardize_unit("1kg", "weight"), "1.0 kg")
        self.assertEqual(self.processor.standardize_unit("16oz", "weight"), "0.45 kg")
        self.assertEqual(self.processor.standardize_unit("2lbs", "weight"), "0.91 kg")
        
        # Test length conversions
        self.assertEqual(self.processor.standardize_unit("100cm", "length"), "1.0 m")
        self.assertEqual(self.processor.standardize_unit("1m", "length"), "1.0 m")
        self.assertEqual(self.processor.standardize_unit("36in", "length"), "0.91 m")
        self.assertEqual(self.processor.standardize_unit("6ft", "length"), "1.83 m")
        
        # Test volume conversions
        self.assertEqual(self.processor.standardize_unit("500ml", "volume"), "0.5 L")
        self.assertEqual(self.processor.standardize_unit("1L", "volume"), "1.0 L")
        self.assertEqual(self.processor.standardize_unit("16fl oz", "volume"), "0.47 L")
        self.assertEqual(self.processor.standardize_unit("1gal", "volume"), "3.79 L")
        
        # Test unknown unit type
        with self.assertRaises(ValueError):
            self.processor.standardize_unit("500g", "unknown_type")
        
        # Test invalid unit format
        with self.assertRaises(ValueError):
            self.processor.standardize_unit("invalid", "weight")
        
        # Test with custom conversions
        custom_conversions = {
            "weight": {
                "g": 0.001,
                "kg": 1.0,
                "oz": 0.0283495,
                "lb": 0.453592
            }
        }
        processor = ContentProcessor(unit_conversions=custom_conversions)
        self.assertEqual(processor.standardize_unit("500g", "weight"), "0.5 kg")
    
    def test_extract_currency(self):
        """
        Test currency extraction.
        """
        # Test common currency symbols
        self.assertEqual(self.processor.extract_currency("$99.99"), "USD")
        self.assertEqual(self.processor.extract_currency("€99.99"), "EUR")
        self.assertEqual(self.processor.extract_currency("£99.99"), "GBP")
        self.assertEqual(self.processor.extract_currency("¥99.99"), "JPY")
        
        # Test currency codes
        self.assertEqual(self.processor.extract_currency("USD 99.99"), "USD")
        self.assertEqual(self.processor.extract_currency("EUR 99.99"), "EUR")
        
        # Test with no currency
        self.assertIsNone(self.processor.extract_currency("99.99"))
        
        # Test with None
        self.assertIsNone(self.processor.extract_currency(None))
    
    def test_process_product(self):
        """
        Test product processing.
        """
        # Create a product with fields needing processing
        product = ProductData(
            url="https://example.com/product",
            title="  Sample   Product  Title  ",
            brand="  Sample   Brand  ",
            price_str="$99.99",
            description="This is a &amp; sample product description.",
            sku="  SAMPLE123  ",
            model_number="  MODEL456  ",
            weight="500g",
            dimensions="100cm x 50cm x 25cm"
        )
        
        # Process the product
        processed = self.processor.process_product(product)
        
        # Check results
        self.assertEqual(processed.title, "Sample Product Title")
        self.assertEqual(processed.brand, "Sample Brand")
        self.assertEqual(processed.price, 99.99)
        self.assertEqual(processed.currency, "USD")
        self.assertEqual(processed.description, "This is a & sample product description.")
        self.assertEqual(processed.sku, "SAMPLE123")
        self.assertEqual(processed.model_number, "MODEL456")
        
        # Test with a product that has no fields to process
        processed = self.processor.process_product(self.product)
        self.assertEqual(processed.title, self.product.title)
        
        # Test with disabled options
        processor = ContentProcessor(
            clean_whitespace=False,
            normalize_text=False,
            convert_prices=False
        )
        product = ProductData(
            title="  Extra   Spaces  ",
            price_str="$99.99"
        )
        processed = processor.process_product(product)
        self.assertEqual(processed.title, "  Extra   Spaces  ")  # Whitespace preserved
        self.assertIsNone(processed.price)  # Price not converted
    
    def test_batch_process(self):
        """
        Test batch processing of products.
        """
        # Create multiple products
        products = [
            ProductData(
                title="Product 1",
                price_str="$99.99"
            ),
            ProductData(
                title="Product 2",
                price_str="€199.99"
            ),
            ProductData(
                title="Product 3",
                price_str="£299.99"
            )
        ]
        
        # Process in batch
        processed = self.processor.batch_process(products)
        
        # Check results
        self.assertEqual(len(processed), 3)
        self.assertEqual(processed[0].price, 99.99)
        self.assertEqual(processed[0].currency, "USD")
        self.assertEqual(processed[1].price, 199.99)
        self.assertEqual(processed[1].currency, "EUR")
        self.assertEqual(processed[2].price, 299.99)
        self.assertEqual(processed[2].currency, "GBP")
        
        # Test empty list
        self.assertEqual(self.processor.batch_process([]), [])
        
        # Test handling of errors in batch
        products = [
            ProductData(title="Good Product", price_str="$99.99"),
            ProductData(title="Bad Product", price_str="not a price")
        ]
        
        # Should skip errors and continue processing
        processed = self.processor.batch_process(products, skip_errors=True)
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0].title, "Good Product")
        
        # Should raise error when skip_errors is False
        with self.assertRaises(DataProcessingError):
            self.processor.batch_process(products, skip_errors=False)
        
        # Test with max_workers
        products = [ProductData(title=f"Product {i}", price_str=f"${i}.99") for i in range(10)]
        processed = self.processor.batch_process(products, max_workers=2)
        self.assertEqual(len(processed), 10)


if __name__ == "__main__":
    unittest.main() 