"""
Unit tests for the ProductExtractor class.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from crawl4ai.extraction_strategy import (JsonCssExtractionStrategy,
                                          LLMExtractionStrategy)

from crawl4ai_llm.crawler import ContentFilter
from crawl4ai_llm.extraction import ProductExtractor
from crawl4ai_llm.models import ProductData


class TestProductExtractor(unittest.TestCase):
    """Tests for the ProductExtractor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_url = "https://example.com/product/123"
        self.sample_product_data = {
            "title": "Test Product",
            "price": {"current_price": 99.99, "currency": "USD"},
            "source": self.test_url,
            "extraction_success": True,
            "extracted_at": "2023-01-01T00:00:00",
        }

        self.sample_crawl_result = {
            "html": "<html><body><h1>Test Product</h1><p>$99.99</p></body></html>",
            "extracted_content": ["<h1>Test Product</h1><p>$99.99</p>"],
            "success": True,
            "url": self.test_url,
        }

        self.sample_extract_result = {
            "html": "<html><body><h1>Test Product</h1><p>$99.99</p></body></html>",
            "extracted_content": {
                "title": "Test Product",
                "price": {"current_price": 99.99, "currency": "USD"},
            },
            "success": True,
            "url": self.test_url,
        }

    @patch("crawl4ai_llm.crawler.base.BaseCrawler.crawl")
    @patch("crawl4ai_llm.extraction.schema_generator.SchemaGenerator.generate_schema")
    async def test_extract_with_auto_schema(self, mock_generate_schema, mock_crawl):
        """Test extract_with_auto_schema method."""
        # Setup mocks
        mock_crawl.side_effect = [
            self.sample_crawl_result,  # First call to get HTML
            self.sample_extract_result,  # Second call to extract with schema
        ]
        mock_generate_schema.return_value = {"selectors": {"title": "h1", "price": "p"}}

        # Test extraction
        extractor = ProductExtractor()
        result = await extractor.extract_with_auto_schema(self.test_url)

        # Verify results
        self.assertEqual(result.title, "Test Product")
        self.assertEqual(result.price.current_price, 99.99)
        self.assertEqual(result.price.currency, "USD")
        self.assertTrue(result.extraction_success)

        # Verify mock calls
        mock_crawl.assert_called()
        mock_generate_schema.assert_called_once()

    @patch("crawl4ai_llm.crawler.base.BaseCrawler.crawl")
    async def test_extract_with_llm(self, mock_crawl):
        """Test extract_with_llm method."""
        # Setup mocks
        mock_crawl.side_effect = [
            self.sample_crawl_result,  # Initial crawl
            {  # LLM extraction result
                "success": True,
                "extracted_content": {
                    "title": "Test Product",
                    "price": {"current_price": 99.99, "currency": "USD"},
                },
                "url": self.test_url,
            },
        ]

        # Test extraction
        extractor = ProductExtractor()
        result = await extractor.extract_with_llm(self.test_url)

        # Verify results
        self.assertEqual(result.title, "Test Product")
        self.assertEqual(result.price.current_price, 99.99)
        self.assertEqual(result.price.currency, "USD")
        self.assertTrue(result.extraction_success)

        # Verify mock calls
        self.assertEqual(mock_crawl.call_count, 2)

    @patch(
        "crawl4ai_llm.extraction.product_extractor.ProductExtractor.extract_with_auto_schema"
    )
    async def test_extract_with_auto_schema_strategy(
        self, mock_extract_with_auto_schema
    ):
        """Test extract method with auto_schema strategy."""
        # Setup mocks
        mock_product = ProductData(
            title="Test Product",
            price={"current_price": 99.99, "currency": "USD"},
            source=self.test_url,
            extraction_success=True,
        )
        mock_extract_with_auto_schema.return_value = mock_product

        # Test extraction
        extractor = ProductExtractor()
        result = await extractor.extract(self.test_url, strategy="auto_schema")

        # Verify results
        self.assertEqual(result.title, "Test Product")
        self.assertEqual(result.price.current_price, 99.99)

        # Verify mock calls
        mock_extract_with_auto_schema.assert_called_once_with(self.test_url)

    @patch(
        "crawl4ai_llm.extraction.product_extractor.ProductExtractor.extract_with_llm"
    )
    async def test_extract_with_llm_strategy(self, mock_extract_with_llm):
        """Test extract method with llm strategy."""
        # Setup mocks
        mock_product = ProductData(
            title="Test Product",
            price={"current_price": 99.99, "currency": "USD"},
            source=self.test_url,
            extraction_success=True,
        )
        mock_extract_with_llm.return_value = mock_product

        # Test extraction
        extractor = ProductExtractor()
        result = await extractor.extract(self.test_url, strategy="llm")

        # Verify results
        self.assertEqual(result.title, "Test Product")
        self.assertEqual(result.price.current_price, 99.99)

        # Verify mock calls
        mock_extract_with_llm.assert_called_once_with(self.test_url, fallback=False)

    @patch(
        "crawl4ai_llm.extraction.product_extractor.ProductExtractor.extract_with_auto_schema"
    )
    @patch(
        "crawl4ai_llm.extraction.product_extractor.ProductExtractor.extract_with_llm"
    )
    async def test_extract_with_fallback(
        self, mock_extract_with_llm, mock_extract_with_auto_schema
    ):
        """Test extract method with fallback to LLM."""
        # Setup mocks
        failed_product = ProductData(
            title="Extraction Failed",
            price={"current_price": 0.0, "currency": "USD"},
            source=self.test_url,
            extraction_success=False,
        )
        success_product = ProductData(
            title="Test Product",
            price={"current_price": 99.99, "currency": "USD"},
            source=self.test_url,
            extraction_success=True,
        )

        mock_extract_with_auto_schema.return_value = failed_product
        mock_extract_with_llm.return_value = success_product

        # Test extraction
        extractor = ProductExtractor()
        result = await extractor.extract(
            self.test_url, strategy="auto_schema", fallback=True
        )

        # Verify results
        self.assertEqual(result.title, "Test Product")
        self.assertEqual(result.price.current_price, 99.99)
        self.assertTrue(result.extraction_success)

        # Verify mock calls
        mock_extract_with_auto_schema.assert_called_once_with(self.test_url)
        mock_extract_with_llm.assert_called_once_with(self.test_url, fallback=True)

    @patch("crawl4ai_llm.crawler.base.BaseCrawler")
    @patch(
        "crawl4ai_llm.extraction.product_extractor.ProductExtractor.extract_with_auto_schema"
    )
    async def test_extract_with_content_filters(
        self, mock_extract_with_auto_schema, mock_crawler_class
    ):
        """Test extract method with content filters."""
        # Setup mocks
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler

        mock_product = ProductData(
            title="Test Product",
            price={"current_price": 99.99, "currency": "USD"},
            source=self.test_url,
            extraction_success=True,
        )
        mock_extract_with_auto_schema.return_value = mock_product

        # Create content filter
        content_filter = ContentFilter(filter_type="bm25", query="test")

        # Test extraction with filter in constructor
        extractor = ProductExtractor(content_filters=[content_filter])
        result = await extractor.extract(self.test_url, strategy="auto_schema")

        # Verify results
        self.assertEqual(result.title, "Test Product")
        self.assertEqual(result.price.current_price, 99.99)

        # Verify BaseCrawler was initialized with content filters
        mock_crawler_class.assert_called_with(content_filters=[content_filter])

    @patch("crawl4ai_llm.crawler.base.BaseCrawler")
    @patch(
        "crawl4ai_llm.extraction.product_extractor.ProductExtractor.extract_with_auto_schema"
    )
    async def test_extract_with_one_time_content_filters(
        self, mock_extract_with_auto_schema, mock_crawler_class
    ):
        """Test extract method with one-time content filters."""
        # Setup mocks
        mock_crawler = MagicMock()
        mock_crawler_class.side_effect = lambda **kwargs: mock_crawler

        mock_product = ProductData(
            title="Test Product",
            price={"current_price": 99.99, "currency": "USD"},
            source=self.test_url,
            extraction_success=True,
        )
        mock_extract_with_auto_schema.return_value = mock_product

        # Create content filter for one-time use
        one_time_filter = ContentFilter(filter_type="pruning", threshold=0.4)

        # Test extraction with one-time filter
        extractor = ProductExtractor()
        result = await extractor.extract(
            self.test_url, strategy="auto_schema", content_filters=[one_time_filter]
        )

        # Verify results
        self.assertEqual(result.title, "Test Product")
        self.assertEqual(result.price.current_price, 99.99)

        # Verify BaseCrawler was initialized with content filters
        mock_crawler_class.assert_called_with(content_filters=[one_time_filter])


# Use a custom test runner that supports async tests
def run_async_test(test_case):
    """Helper function to run async test cases."""
    loop = asyncio.get_event_loop()
    task = asyncio.ensure_future(test_case)
    return loop.run_until_complete(task)


if __name__ == "__main__":
    unittest.main()
