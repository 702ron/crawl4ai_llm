"""
Unit tests for the Deduplicator class.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest

from crawl4ai_llm.models import ProductData
from crawl4ai_llm.processing import Deduplicator, get_duplicate_groups


class TestDeduplicator(unittest.TestCase):
    """
    Test case for the Deduplicator class.
    """

    def setUp(self):
        """
        Set up test fixtures.
        """
        # Create sample products for testing
        self.product1 = ProductData(
            url="https://example.com/product1",
            title="iPhone 13 Pro Max 256GB - Graphite",
            brand="Apple",
            price=1099.99,
            currency="USD",
            description="Experience the latest iPhone with amazing camera system.",
            sku="IPHPR256GR",
            model_number="A2484"
        )
        
        self.product2 = ProductData(
            url="https://example.com/product2",
            title="Apple iPhone 13 Pro Max (256GB, Graphite)",
            brand="Apple",
            price=1099.99,
            currency="USD", 
            description="The iPhone 13 Pro Max features a 6.7-inch Super Retina XDR display with ProMotion.",
            sku="IPHPR256GR",
            model_number="A2484"
        )
        
        self.product3 = ProductData(
            url="https://example.com/product3",
            title="Samsung Galaxy S21 Ultra - 128GB",
            brand="Samsung",
            price=999.99,
            currency="USD",
            description="Samsung's flagship phone with 108MP camera.",
            sku="SM-G998U",
            model_number="SM-G998U" 
        )
        
        # Create test products with different creation times
        self.older_product = ProductData(
            url="https://example.com/older",
            title="Older Product",
            brand="Brand",
            price=100,
            currency="USD",
            created_at=datetime(2022, 1, 1)
        )
        
        self.newer_product = ProductData(
            url="https://example.com/newer",
            title="Newer Product",
            brand="Brand",
            price=100,
            currency="USD",
            created_at=datetime(2022, 2, 1)
        )
        
        # Create test products with varying completeness
        self.incomplete_product = ProductData(
            url="https://example.com/incomplete",
            title="Incomplete",
            brand="Brand"
        )
        
        self.complete_product = ProductData(
            url="https://example.com/complete",
            title="Complete",
            brand="Brand",
            price=100,
            currency="USD",
            description="Description",
            sku="SKU123",
            model_number="MODEL123",
            availability="In Stock",
            metadata={"key": "value"}
        )
        
        # Initialize deduplicator
        self.deduplicator = Deduplicator(similarity_threshold=0.7)
        
    def test_initialization(self):
        """
        Test that Deduplicator initializes with the correct parameters.
        """
        # Default threshold
        deduplicator = Deduplicator()
        self.assertEqual(deduplicator.similarity_threshold, 0.7)
        
        # Custom threshold
        deduplicator = Deduplicator(similarity_threshold=0.9)
        self.assertEqual(deduplicator.similarity_threshold, 0.9)
        
        # Invalid threshold (too low)
        with self.assertRaises(ValueError):
            Deduplicator(similarity_threshold=-0.1)
        
        # Invalid threshold (too high)
        with self.assertRaises(ValueError):
            Deduplicator(similarity_threshold=1.1)
    
    def test_product_signature(self):
        """
        Test the product signature generation.
        """
        signature = self.deduplicator.product_signature(self.product1)
        
        # Signature should include normalized brand and title
        self.assertIn("apple", signature.lower())
        self.assertIn("iphone", signature.lower())
        
        # Different products should have different signatures
        sig1 = self.deduplicator.product_signature(self.product1)
        sig2 = self.deduplicator.product_signature(self.product3)
        self.assertNotEqual(sig1, sig2)
        
        # Similar products should have similar signatures
        sig1 = self.deduplicator.product_signature(self.product1)
        sig2 = self.deduplicator.product_signature(self.product2)
        self.assertNotEqual(sig1, sig2)  # Not identical, but will be similar
    
    def test_is_duplicate_by_id(self):
        """
        Test duplicate detection by ID.
        """
        # Set up products with same SKU or model
        product_with_sku = ProductData(
            url="https://example.com/sku",
            title="Product with SKU",
            sku="SAME123"
        )
        
        product_with_same_sku = ProductData(
            url="https://example.com/same-sku",
            title="Another Product with SKU",
            sku="SAME123"
        )
        
        product_with_model = ProductData(
            url="https://example.com/model",
            title="Product with Model",
            model_number="MODEL456"
        )
        
        product_with_same_model = ProductData(
            url="https://example.com/same-model",
            title="Another Product with Model",
            model_number="MODEL456"
        )
        
        # Test SKU matching
        self.assertTrue(
            self.deduplicator.is_duplicate_by_id(product_with_sku, product_with_same_sku)
        )
        
        # Test model number matching
        self.assertTrue(
            self.deduplicator.is_duplicate_by_id(product_with_model, product_with_same_model)
        )
        
        # Test no matching IDs
        self.assertFalse(
            self.deduplicator.is_duplicate_by_id(product_with_sku, product_with_model)
        )
    
    def test_text_similarity(self):
        """
        Test text similarity calculation.
        """
        # Identical texts
        text1 = "Apple iPhone 13 Pro"
        text2 = "Apple iPhone 13 Pro"
        similarity = self.deduplicator.text_similarity(text1, text2)
        self.assertEqual(similarity, 1.0)
        
        # Similar texts
        text1 = "Apple iPhone 13 Pro Max 256GB"
        text2 = "iPhone 13 Pro Max (256GB) by Apple"
        similarity = self.deduplicator.text_similarity(text1, text2)
        self.assertGreaterEqual(similarity, 0.7)
        
        # Different texts
        text1 = "Apple iPhone 13 Pro"
        text2 = "Samsung Galaxy S21 Ultra"
        similarity = self.deduplicator.text_similarity(text1, text2)
        self.assertLessEqual(similarity, 0.5)
        
        # Empty text
        text1 = "Apple iPhone"
        text2 = ""
        similarity = self.deduplicator.text_similarity(text1, text2)
        self.assertEqual(similarity, 0.0)
        
        # Both empty
        text1 = ""
        text2 = ""
        similarity = self.deduplicator.text_similarity(text1, text2)
        self.assertEqual(similarity, 1.0)  # Empty strings are identical
    
    def test_calculate_similarity(self):
        """
        Test product similarity calculation.
        """
        # Similar products should have high similarity
        similarity = self.deduplicator.calculate_similarity(self.product1, self.product2)
        self.assertGreaterEqual(similarity, 0.7)
        
        # Different products should have low similarity
        similarity = self.deduplicator.calculate_similarity(self.product1, self.product3)
        self.assertLessEqual(similarity, 0.5)
        
        # Same product should have perfect similarity
        similarity = self.deduplicator.calculate_similarity(self.product1, self.product1)
        self.assertEqual(similarity, 1.0)
    
    def test_is_duplicate_by_similarity(self):
        """
        Test duplicate detection by similarity.
        """
        # Similar products should be detected as duplicates
        self.assertTrue(
            self.deduplicator.is_duplicate_by_similarity(self.product1, self.product2)
        )
        
        # Different products should not be detected as duplicates
        self.assertFalse(
            self.deduplicator.is_duplicate_by_similarity(self.product1, self.product3)
        )
        
        # Test with high threshold
        high_threshold_deduplicator = Deduplicator(similarity_threshold=0.9)
        
        # Products may not be considered duplicates with higher threshold
        result = high_threshold_deduplicator.is_duplicate_by_similarity(self.product1, self.product2)
        # This could be true or false depending on the exact implementation
        
        # Test with low threshold
        low_threshold_deduplicator = Deduplicator(similarity_threshold=0.5)
        
        # Products that are somewhat similar would be considered duplicates
        self.assertTrue(
            low_threshold_deduplicator.is_duplicate_by_similarity(self.product1, self.product2)
        )
    
    def test_find_duplicates(self):
        """
        Test finding duplicate groups in a list of products.
        """
        # Create a list with some duplicates
        products = [self.product1, self.product2, self.product3]
        
        # Find duplicate groups
        duplicate_groups = self.deduplicator.find_duplicates(products)
        
        # Should be one group with product1 and product2
        self.assertEqual(len(duplicate_groups), 1)
        self.assertEqual(len(duplicate_groups[0]), 2)
        
        # Check that the group contains the expected products
        group_product_urls = [p.url for p in duplicate_groups[0]]
        self.assertIn(self.product1.url, group_product_urls)
        self.assertIn(self.product2.url, group_product_urls)
        
        # Test with empty list
        self.assertEqual(len(self.deduplicator.find_duplicates([])), 0)
        
        # Test with no duplicates
        no_dupes = [self.product1, self.product3]
        self.assertEqual(len(self.deduplicator.find_duplicates(no_dupes)), 0)
    
    def test_merge_products_latest_strategy(self):
        """
        Test merging products with the 'latest' strategy.
        """
        # Create products to merge
        merged = self.deduplicator.merge_products(
            [self.older_product, self.newer_product],
            strategy="latest"
        )
        
        # Should keep the newer product's values
        self.assertEqual(merged.title, self.newer_product.title)
        self.assertEqual(merged.url, self.newer_product.url)
        
        # Creation date should be preserved
        self.assertEqual(merged.created_at, self.newer_product.created_at)
    
    def test_merge_products_most_complete_strategy(self):
        """
        Test merging products with the 'most_complete' strategy.
        """
        # Create products to merge
        merged = self.deduplicator.merge_products(
            [self.incomplete_product, self.complete_product],
            strategy="most_complete"
        )
        
        # Should keep the more complete product's values
        self.assertEqual(merged.title, self.complete_product.title)
        self.assertEqual(merged.price, self.complete_product.price)
        self.assertEqual(merged.description, self.complete_product.description)
        self.assertEqual(merged.sku, self.complete_product.sku)
        self.assertEqual(merged.metadata, self.complete_product.metadata)
    
    def test_merge_products_combine_strategy(self):
        """
        Test merging products with the 'combine' strategy.
        """
        # Create products with different fields set
        product_a = ProductData(
            url="https://example.com/a",
            title="Product A",
            brand="Brand A",
            price=100,
            currency="USD"
        )
        
        product_b = ProductData(
            url="https://example.com/b",
            title="Product B",
            brand="Brand B",
            description="Description B",
            sku="SKU-B"
        )
        
        # Merge with combine strategy
        merged = self.deduplicator.merge_products(
            [product_a, product_b],
            strategy="combine"
        )
        
        # Should combine fields from both products
        self.assertIn(merged.url, [product_a.url, product_b.url])  # One of the URLs
        self.assertEqual(merged.price, product_a.price)  # From product_a
        self.assertEqual(merged.currency, product_a.currency)  # From product_a
        self.assertEqual(merged.description, product_b.description)  # From product_b
        self.assertEqual(merged.sku, product_b.sku)  # From product_b
    
    def test_merge_products_invalid_strategy(self):
        """
        Test merging products with an invalid strategy.
        """
        with self.assertRaises(ValueError):
            self.deduplicator.merge_products(
                [self.product1, self.product2],
                strategy="invalid_strategy"
            )
    
    def test_helper_function(self):
        """
        Test the get_duplicate_groups helper function.
        """
        products = [self.product1, self.product2, self.product3]
        
        # Use the helper function
        duplicate_groups = get_duplicate_groups(products, similarity_threshold=0.7)
        
        # Should give the same result as deduplicator.find_duplicates
        deduplicator_groups = self.deduplicator.find_duplicates(products)
        
        self.assertEqual(len(duplicate_groups), len(deduplicator_groups))
        
        # Check each group has the same products
        if duplicate_groups:
            group_urls = sorted([p.url for p in duplicate_groups[0]])
            dedup_urls = sorted([p.url for p in deduplicator_groups[0]])
            self.assertEqual(group_urls, dedup_urls)


if __name__ == "__main__":
    unittest.main() 