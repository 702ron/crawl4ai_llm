"""
Tests for ContentFilter integration with ProductExtractor.
"""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from bs4 import BeautifulSoup

from crawl4ai_llm.extraction.product_extractor import ProductExtractor
from crawl4ai_llm.crawler.content_filter import ContentFilter
from crawl4ai_llm.models.product_data import ProductData


@pytest.fixture
def sample_html():
    return """
    <html>
        <head>
            <title>Test Product</title>
            <meta name="description" content="This is a test product description">
        </head>
        <body>
            <div class="navigation">
                <ul>
                    <li><a href="/">Home</a></li>
                    <li><a href="/products">Products</a></li>
                </ul>
            </div>
            
            <div class="product">
                <h1>Test Product Title</h1>
                <div class="price">$99.99</div>
                <div class="description">
                    <p>This is a detailed product description.</p>
                    <p>It has multiple paragraphs.</p>
                </div>
                <div class="specifications">
                    <ul>
                        <li>Weight: 2kg</li>
                        <li>Color: Blue</li>
                    </ul>
                </div>
                <div class="images">
                    <img src="/img/product1.jpg" alt="Product image 1">
                    <img src="/img/product2.jpg" alt="Product image 2">
                </div>
            </div>
            
            <div class="footer">
                <p>Copyright 2023</p>
                <ul>
                    <li><a href="/about">About</a></li>
                    <li><a href="/contact">Contact</a></li>
                </ul>
            </div>
        </body>
    </html>
    """


class MockFetcher:
    def __init__(self, html_content):
        self.html_content = html_content
    
    async def fetch(self, url):
        return self.html_content


@pytest.fixture
def mock_schema_generator():
    with patch('crawl4ai_llm.extraction.schema_generator.SchemaGenerator') as mock:
        generator_instance = MagicMock()
        generator_instance.generate_schema = AsyncMock(return_value={
            "title": {"selector": "h1", "type": "text"},
            "price": {"selector": ".price", "type": "text"},
            "description": {"selector": ".description", "type": "text"},
            "specs": {"selector": ".specifications ul li", "type": "list"},
            "images": {"selector": ".images img", "attribute": "src", "type": "list"}
        })
        mock.return_value = generator_instance
        yield mock


@pytest.mark.asyncio
async def test_extraction_with_bm25_filter(sample_html, mock_schema_generator):
    # Create BM25 filter
    content_filter = ContentFilter(
        filter_type="bm25",
        query="product price description specifications",
        threshold=0.3
    )
    
    # Setup product extractor with mock fetcher and content filter
    extractor = ProductExtractor(
        content_filters=[content_filter],
        fetcher=MockFetcher(sample_html)
    )
    
    # Extract product data
    result = await extractor.extract("https://example.com/test-product")
    
    # Verify successful extraction
    assert result.extraction_success is True
    assert result.product.title == "Test Product Title"
    assert result.product.price.value == "$99.99"
    assert "detailed product description" in result.product.description
    assert len(result.product.images) == 2
    assert result.product.images[0].url == "/img/product1.jpg"
    
    # Verify metadata related to filtering
    assert result.metadata.get("filtered_content_applied") is True
    assert "bm25" in str(result.metadata.get("filters_used", []))


@pytest.mark.asyncio
async def test_extraction_with_llm_filter(sample_html, mock_schema_generator):
    # Create mock LLM filter
    async def mock_filter_content(html_content, *args, **kwargs):
        # Simulate LLM filtering by keeping only product section
        soup = BeautifulSoup(html_content, 'html.parser')
        product_div = soup.find('div', class_='product')
        filtered_html = str(product_div)
        return filtered_html
    
    with patch('crawl4ai_llm.crawler.content_filter.ContentFilter._filter_with_llm', 
               new_callable=AsyncMock) as mock_llm_filter:
        mock_llm_filter.side_effect = mock_filter_content
        
        # Create LLM filter
        content_filter = ContentFilter(
            filter_type="llm",
            instruction="Extract only product information",
            threshold=0.5
        )
        
        # Setup product extractor with mock fetcher and content filter
        extractor = ProductExtractor(
            content_filters=[content_filter],
            fetcher=MockFetcher(sample_html)
        )
        
        # Extract product data
        result = await extractor.extract("https://example.com/test-product")
        
        # Verify successful extraction
        assert result.extraction_success is True
        assert result.product.title == "Test Product Title"
        assert result.product.price.value == "$99.99"
        
        # Verify filtering was applied
        mock_llm_filter.assert_called_once()
        assert result.metadata.get("filtered_content_applied") is True
        assert "llm" in str(result.metadata.get("filters_used", []))


@pytest.mark.asyncio
async def test_extraction_with_multiple_filters(sample_html, mock_schema_generator):
    # Create BM25 filter
    bm25_filter = ContentFilter(
        filter_type="bm25",
        query="product price description specifications",
        threshold=0.3
    )
    
    # Create mock LLM filter
    async def mock_filter_content(html_content, *args, **kwargs):
        # Simulate LLM filtering by keeping only product section
        soup = BeautifulSoup(html_content, 'html.parser')
        product_div = soup.find('div', class_='product')
        filtered_html = str(product_div)
        return filtered_html
    
    with patch('crawl4ai_llm.crawler.content_filter.ContentFilter._filter_with_llm', 
               new_callable=AsyncMock) as mock_llm_filter:
        mock_llm_filter.side_effect = mock_filter_content
        
        # Create LLM filter
        llm_filter = ContentFilter(
            filter_type="llm",
            instruction="Extract only product information",
            threshold=0.5
        )
        
        # Setup product extractor with mock fetcher and both filters
        extractor = ProductExtractor(
            content_filters=[bm25_filter, llm_filter],
            fetcher=MockFetcher(sample_html)
        )
        
        # Extract product data
        result = await extractor.extract("https://example.com/test-product")
        
        # Verify successful extraction
        assert result.extraction_success is True
        assert result.product.title == "Test Product Title"
        assert result.product.price.value == "$99.99"
        
        # Verify both filters were applied
        mock_llm_filter.assert_called_once()
        assert result.metadata.get("filtered_content_applied") is True
        filters_used = result.metadata.get("filters_used", [])
        assert "bm25" in str(filters_used) and "llm" in str(filters_used)


@pytest.mark.asyncio
async def test_extraction_with_per_request_filters(sample_html, mock_schema_generator):
    # Create base extractor without filters
    extractor = ProductExtractor(
        fetcher=MockFetcher(sample_html)
    )
    
    # Create filter for this specific extraction
    content_filter = ContentFilter(
        filter_type="bm25",
        query="product price description specifications",
        threshold=0.3
    )
    
    # Extract product data with filter provided at extraction time
    result = await extractor.extract(
        "https://example.com/test-product",
        content_filters=[content_filter]
    )
    
    # Verify successful extraction
    assert result.extraction_success is True
    assert result.metadata.get("filtered_content_applied") is True
    assert "bm25" in str(result.metadata.get("filters_used", [])) 