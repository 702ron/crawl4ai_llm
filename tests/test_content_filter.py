"""
Tests for the ContentFilter functionality.
"""

import asyncio
import re
from unittest.mock import MagicMock, patch

import pytest

from crawl4ai_llm.crawler.base import BaseCrawler
from crawl4ai_llm.crawler.content_filter import ContentFilter
from crawl4ai_llm.extraction.product_extractor import ProductExtractor


class TestContentFilter:
    """Test suite for ContentFilter class."""

    def test_init_css_filter(self):
        """Test initializing a CSS selector filter."""
        css_filter = ContentFilter(
            filter_type="css", selector=".product-details", extract_text=True
        )

        assert css_filter.filter_type == "css"
        assert css_filter.selector == ".product-details"
        assert css_filter.extract_text is True
        assert css_filter.pattern is None
        assert css_filter.replacement is None

    def test_init_xpath_filter(self):
        """Test initializing an XPath filter."""
        xpath_filter = ContentFilter(
            filter_type="xpath",
            selector="//div[@class='product-details']",
            extract_text=False,
        )

        assert xpath_filter.filter_type == "xpath"
        assert xpath_filter.selector == "//div[@class='product-details']"
        assert xpath_filter.extract_text is False
        assert xpath_filter.pattern is None
        assert xpath_filter.replacement is None

    def test_init_regex_filter(self):
        """Test initializing a regex filter."""
        regex_filter = ContentFilter(
            filter_type="regex",
            pattern=r"Price: \$(\d+\.\d+)",
            replacement=r"Product Price: $\1",
        )

        assert regex_filter.filter_type == "regex"
        assert regex_filter.pattern == r"Price: \$(\d+\.\d+)"
        assert regex_filter.replacement == r"Product Price: $\1"
        assert regex_filter.selector is None
        assert regex_filter.extract_text is None

    def test_invalid_filter_type(self):
        """Test that an invalid filter type raises a ValueError."""
        with pytest.raises(ValueError, match="Invalid filter_type: invalid_type"):
            ContentFilter(filter_type="invalid_type")

    def test_missing_parameters_css(self):
        """Test that missing required parameters for CSS filters raises a ValueError."""
        with pytest.raises(ValueError, match="selector is required for css filter"):
            ContentFilter(filter_type="css")

    def test_missing_parameters_xpath(self):
        """Test that missing required parameters for XPath filters raises a ValueError."""
        with pytest.raises(ValueError, match="selector is required for xpath filter"):
            ContentFilter(filter_type="xpath")

    def test_missing_parameters_regex(self):
        """Test that missing required parameters for regex filters raises a ValueError."""
        with pytest.raises(ValueError, match="pattern is required for regex filter"):
            ContentFilter(filter_type="regex")

    def test_str_representation(self):
        """Test the string representation of ContentFilter."""
        css_filter = ContentFilter(
            filter_type="css", selector=".product-details", extract_text=True
        )

        assert str(css_filter) == "ContentFilter(type=css, selector=.product-details)"

        regex_filter = ContentFilter(
            filter_type="regex",
            pattern=r"Price: \$(\d+\.\d+)",
            replacement=r"Product Price: $\1",
        )

        assert (
            str(regex_filter)
            == "ContentFilter(type=regex, pattern=Price: \\$(\\d+\\.\\d+))"
        )


@pytest.mark.asyncio
class TestContentFilterIntegration:
    """Test the integration of ContentFilter with other components."""

    @patch("crawl4ai_llm.crawler.base.Crawler")
    async def test_base_crawler_with_content_filters(self, mock_crawler):
        """Test that BaseCrawler correctly applies content filters during crawling."""
        # Set up mock crawler
        mock_instance = MagicMock()
        mock_instance.crawl.return_value = {
            "success": True,
            "html": "<html><body><div class='product'>Product Content</div></body></html>",
            "extracted_content": ["<div class='product'>Product Content</div>"],
        }
        mock_crawler.return_value = mock_instance

        # Create content filters
        filters = [
            ContentFilter(filter_type="css", selector=".product", extract_text=False)
        ]

        # Create BaseCrawler with filters
        crawler = BaseCrawler(content_filters=filters)

        # Perform a crawl
        result = await crawler.crawl("https://example.com/product")

        # Assert that the crawl was successful and filters were applied
        assert result["success"] is True
        assert "extracted_content" in result
        assert result["extracted_content"] == [
            "<div class='product'>Product Content</div>"
        ]

        # Verify that the content_filters were passed to the underlying crawler
        _, kwargs = mock_crawler.call_args
        assert "content_filters" in kwargs
        assert len(kwargs["content_filters"]) == 1
        assert kwargs["content_filters"][0].filter_type == "css"

    @patch("crawl4ai_llm.extraction.product_extractor.BaseCrawler")
    @patch("crawl4ai_llm.extraction.product_extractor.SchemaGenerator")
    async def test_product_extractor_with_content_filters(
        self, mock_schema_generator, mock_base_crawler
    ):
        """Test that ProductExtractor correctly uses content filters during extraction."""
        # Set up mock crawler and schema generator
        mock_crawler_instance = MagicMock()
        mock_crawler_instance.crawl.return_value = {
            "success": True,
            "html": "<html><body><div class='product'>Product Content</div></body></html>",
            "extracted_content": [
                "<div class='product'>Product Content with price $99.99</div>"
            ],
        }
        mock_base_crawler.return_value = mock_crawler_instance

        mock_schema_instance = MagicMock()
        mock_schema_instance.generate_schema.return_value = {
            "title": {"selector": ".product-title"},
            "price": {"selector": ".product-price"},
        }
        mock_schema_generator.return_value = mock_schema_instance

        # Create content filters
        filters = [
            ContentFilter(filter_type="css", selector=".product", extract_text=False),
            ContentFilter(
                filter_type="regex", pattern=r"\$(\d+\.\d+)", replacement=r"Price: $\1"
            ),
        ]

        # Create ProductExtractor with filters
        extractor = ProductExtractor(content_filters=filters)

        # Add mock response for extraction
        second_crawl_response = {
            "success": True,
            "extracted_content": {
                "title": "Test Product",
                "price": {"current_price": 99.99, "currency": "USD"},
            },
        }
        mock_crawler_instance.crawl.side_effect = [
            mock_crawler_instance.crawl.return_value,  # First call (initial crawl)
            second_crawl_response,  # Second call (extraction)
        ]

        # Perform extraction
        result = await extractor.extract("https://example.com/product")

        # Assert that extraction was successful
        assert result.extraction_success is True
        assert result.title == "Test Product"
        assert result.price.current_price == 99.99

        # Verify content_filters were passed to the crawler
        _, kwargs = mock_base_crawler.call_args
        assert "content_filters" in kwargs
        assert len(kwargs["content_filters"]) == 2

    @patch("crawl4ai_llm.extraction.product_extractor.BaseCrawler")
    async def test_additional_content_filters_in_extraction(self, mock_base_crawler):
        """Test that additional content filters can be passed to the extraction methods."""
        # Set up mock crawler
        mock_crawler_instance = MagicMock()
        mock_crawler_instance.crawl.return_value = {
            "success": True,
            "html": "<html><body><div class='product'>Product Content</div></body></html>",
            "extracted_content": {
                "title": "Test Product",
                "price": {"current_price": 99.99, "currency": "USD"},
            },
        }
        mock_base_crawler.return_value = mock_crawler_instance

        # Initial filters
        initial_filters = [
            ContentFilter(filter_type="css", selector=".product", extract_text=False)
        ]

        # Additional filters for this extraction
        additional_filters = [
            ContentFilter(
                filter_type="regex", pattern=r"\$(\d+\.\d+)", replacement=r"Price: $\1"
            )
        ]

        # Create ProductExtractor with initial filters
        extractor = ProductExtractor(content_filters=initial_filters)

        # Mock the _get_crawler_with_filters method to verify it's called with combined filters
        original_method = extractor._get_crawler_with_filters
        with patch.object(extractor, "_get_crawler_with_filters") as mock_method:
            mock_method.side_effect = original_method

            # Perform extraction with additional filters
            await extractor.extract(
                "https://example.com/product",
                strategy="llm",
                content_filters=additional_filters,
            )

            # Verify _get_crawler_with_filters was called with additional_filters
            mock_method.assert_called_with(additional_filters)


@pytest.mark.asyncio
class TestContentFilterEndToEnd:
    """End-to-end tests for content filtering functionality."""

    @pytest.mark.parametrize(
        "filter_type,filter_params,input_html,expected_output",
        [
            # CSS filter
            (
                "css",
                {"selector": ".price", "extract_text": True},
                "<html><div class='price'>$99.99</div></html>",
                "$99.99",
            ),
            # CSS filter with HTML extraction
            (
                "css",
                {"selector": ".product", "extract_text": False},
                "<html><div class='product'><span>Product</span></div></html>",
                "<div class='product'><span>Product</span></div>",
            ),
            # XPath filter
            (
                "xpath",
                {"selector": "//div[@class='description']", "extract_text": True},
                "<html><div class='description'>Great product</div></html>",
                "Great product",
            ),
            # Regex filter
            (
                "regex",
                {"pattern": r"Price: \$(\d+\.\d+)", "replacement": r"Cost: $\1"},
                "<html><div>Price: $99.99</div></html>",
                "<html><div>Cost: $99.99</div></html>",
            ),
        ],
    )
    async def test_content_filter_application(
        self, filter_type, filter_params, input_html, expected_output
    ):
        """Test that different types of content filters properly filter HTML content."""
        # This is a simplified version of how filters would be applied
        # In a real scenario, this would be done by the crawler

        content_filter = ContentFilter(filter_type=filter_type, **filter_params)

        # Apply filter manually based on type
        if filter_type == "css":
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(input_html, "html.parser")
            elements = soup.select(content_filter.selector)

            if content_filter.extract_text:
                result = elements[0].get_text() if elements else ""
            else:
                result = str(elements[0]) if elements else ""

        elif filter_type == "xpath":
            import io

            from lxml import etree

            tree = etree.parse(io.StringIO(input_html), etree.HTMLParser())
            elements = tree.xpath(content_filter.selector)

            if content_filter.extract_text:
                result = elements[0].text if elements else ""
            else:
                result = (
                    etree.tostring(elements[0], encoding="unicode") if elements else ""
                )

        else:  # regex
            result = re.sub(
                content_filter.pattern, content_filter.replacement, input_html
            )

        assert result == expected_output
