"""End-to-end integration tests for the crawl4ai_llm package.

These tests validate the complete pipeline from URL crawling to storage,
ensuring all components work together correctly.
"""

import os
import asyncio
import tempfile
import time
import unittest
from typing import Dict, List, Optional, Tuple
from unittest.mock import patch

from crawl4ai_llm.models import ProductData
from crawl4ai_llm.extraction.product_extractor import ProductExtractor
from crawl4ai_llm.processing.data_processor import DataProcessor
from crawl4ai_llm.storage.json_storage import JSONStorage
from crawl4ai_llm.client.client import Crawl4AIClient


class TestEndToEndFlow(unittest.TestCase):
    """Test end-to-end flow from URL extraction to storage."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test storage
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = self.temp_dir.name
        
        # Initialize storage
        self.storage = JSONStorage(storage_dir=self.storage_path)
        
        # Initialize extractor with default settings
        self.extractor = ProductExtractor()
        
        # Initialize data processor
        self.processor = DataProcessor()
        
        # Sample product URLs for testing
        self.test_urls = [
            # Add URLs here that are stable and can be used for testing
            # These should point to real product pages that won't change frequently
            "https://www.example.com/product1",  # Replace with actual test URL
            "https://www.example.com/product2",  # Replace with actual test URL
        ]
        
        # For tests that need an API key (if using remote services)
        self.api_key = os.environ.get("CRAWL4AI_API_KEY", "test_key")

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()

    async def _extract_and_store_product(self, url: str) -> Tuple[Optional[ProductData], str]:
        """Extract product data from URL and store it.
        
        Returns:
            Tuple containing the extracted ProductData and its storage ID
        """
        start_time = time.time()
        
        # Extract product data
        product_data = await self.extractor.extract(url)
        
        # Process the data (validation, enrichment, etc.)
        if product_data:
            processed_data = self.processor.process(product_data)
            
            # Store the processed data
            product_id = self.storage.save_product(processed_data)
            
            end_time = time.time()
            print(f"Processed {url} in {end_time - start_time:.2f} seconds")
            
            return processed_data, product_id
        
        return None, ""

    def test_extraction_to_storage_flow(self):
        """Test the complete flow from extraction to storage."""
        results = []
        
        for url in self.test_urls:
            product_data, product_id = asyncio.run(self._extract_and_store_product(url))
            
            if product_data:
                # Verify the data was properly stored
                stored_product = self.storage.get_product(product_id)
                self.assertEqual(stored_product.title, product_data.title)
                self.assertEqual(stored_product.price.amount, product_data.price.amount)
                
                # Verify required fields are present
                self.assertIsNotNone(stored_product.title)
                self.assertIsNotNone(stored_product.price)
                
                results.append((url, True))
            else:
                results.append((url, False))
        
        # Check overall success rate
        success_count = sum(1 for _, success in results if success)
        total_count = len(results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        print(f"End-to-end test success rate: {success_rate * 100:.1f}% ({success_count}/{total_count})")
        
        # Assert minimum success rate (adjust threshold as needed)
        self.assertGreaterEqual(success_rate, 0.5, "End-to-end success rate below acceptable threshold")

    @patch("crawl4ai_llm.extraction.product_extractor.ProductExtractor.extract")
    async def test_with_mock_data(self, mock_extract):
        """Test the pipeline with mock extraction data."""
        # Create mock product data
        mock_product = ProductData(
            title="Test Product",
            description="This is a test product for integration testing",
            price={"amount": 99.99, "currency": "USD"},
            images=[{"url": "https://example.com/image.jpg"}],
            url="https://www.example.com/test-product",
            brand="Test Brand",
            sku="TEST123",
            availability="In Stock"
        )
        
        # Configure mock to return our test product
        mock_extract.return_value = mock_product
        
        # Run extraction and storage
        product_data, product_id = await self._extract_and_store_product("https://www.example.com/test-product")
        
        # Verify mock was called
        mock_extract.assert_called_once()
        
        # Verify storage worked correctly
        self.assertIsNotNone(product_id)
        stored_product = self.storage.get_product(product_id)
        
        # Verify data integrity
        self.assertEqual(stored_product.title, mock_product.title)
        self.assertEqual(stored_product.price.amount, mock_product.price.amount)
        self.assertEqual(stored_product.brand, mock_product.brand)

    def test_client_integration(self):
        """Test that the client SDK integrates correctly with the backend."""
        # Initialize client with direct mode (no actual API calls)
        client = Crawl4AIClient(
            api_key=self.api_key,
            direct_mode=True  # Use direct calls to the library instead of API
        )
        
        # Test a basic extraction
        product = client.extract_product(self.test_urls[0] if self.test_urls else "https://www.example.com/product")
        
        # Basic validation of returned data
        if product:
            self.assertIsInstance(product, dict)
            self.assertIn("title", product)
            self.assertIn("price", product)
        
        # Test batch extraction
        batch_results = client.batch_extract(
            urls=self.test_urls or ["https://www.example.com/product"],
            concurrency=2
        )
        
        # Validate batch results
        self.assertIsInstance(batch_results, list)
        
        # Test search functionality with filters
        products = client.search_products(
            filters={"brand": "Test"}
        )
        
        # Validate search results
        self.assertIsInstance(products, dict)
        self.assertIn("items", products)
        self.assertIn("count", products)


if __name__ == "__main__":
    unittest.main() 