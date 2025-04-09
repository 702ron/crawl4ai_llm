"""
Integration tests that demonstrate the full product extraction flow.
"""
import pytest
import asyncio
import os
import tempfile
from unittest.mock import patch, MagicMock

from crawl4ai_llm.config import Config, CrawlerConfig, DatabaseConfig, LLMConfig, StorageConfig
from crawl4ai_llm.crawler.base import BaseCrawler
from crawl4ai_llm.extraction.product_extractor import ProductExtractor
from crawl4ai_llm.storage.factory import get_storage
from crawl4ai_llm.models import ProductData


@pytest.fixture
def mock_html_content():
    """Return sample HTML content for testing."""
    return """
    <html>
        <head>
            <title>Test Product - E-commerce Store</title>
            <meta property="og:title" content="Test Product">
            <meta property="og:price:amount" content="99.99">
            <meta property="og:price:currency" content="USD">
            <meta property="og:image" content="https://example.com/image1.jpg">
        </head>
        <body>
            <div class="product-container">
                <h1 class="product-title">Test Product</h1>
                <div class="product-price">$99.99</div>
                <div class="product-brand">Brand X</div>
                <div class="product-description">
                    This is a test product description. It has some features and specifications.
                </div>
                <div class="product-images">
                    <img src="https://example.com/image1.jpg" alt="Test Product Image 1">
                    <img src="https://example.com/image2.jpg" alt="Test Product Image 2">
                </div>
                <div class="product-sku">SKU: TEST123</div>
                <div class="product-availability">In Stock</div>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_llm_response():
    """Return a mock LLM extraction response."""
    return {
        "product": {
            "title": "Test Product",
            "brand": "Brand X",
            "description": "This is a test product description. It has some features and specifications.",
            "price": {
                "amount": 99.99,
                "currency": "USD"
            },
            "images": [
                {"url": "https://example.com/image1.jpg", "alt": "Test Product Image 1"},
                {"url": "https://example.com/image2.jpg", "alt": "Test Product Image 2"}
            ],
            "sku": "TEST123",
            "availability": "In Stock",
            "url": "https://example.com/product"
        }
    }


@pytest.fixture
def test_config():
    """Create a configuration for testing."""
    return Config(
        crawler=CrawlerConfig(
            user_agent="Test Crawler",
            request_timeout=10,
            max_retries=2,
            retry_delay=1,
            rate_limit=5,
            rate_limit_period=1
        ),
        database=DatabaseConfig(
            url="sqlite:///:memory:",
            echo=False
        ),
        llm=LLMConfig(
            provider="dummy",
            api_key="test-key",
            model_name="test-model",
            temperature=0.0,
            max_tokens=1000,
            timeout=30
        ),
        storage=StorageConfig(
            type="json",
            path=tempfile.mkdtemp(),
            use_uuid=True
        )
    )


class MockLLMClient:
    """Mock LLM client for testing."""
    
    async def generate(self, instruction, context=None):
        """Return mock LLM response."""
        if "schema" in instruction.lower():
            return {
                "properties": {
                    "product": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "brand": {"type": "string"},
                            "description": {"type": "string"},
                            "price": {
                                "type": "object",
                                "properties": {
                                    "amount": {"type": "number"},
                                    "currency": {"type": "string"}
                                }
                            },
                            "images": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "url": {"type": "string"},
                                        "alt": {"type": "string"}
                                    }
                                }
                            },
                            "sku": {"type": "string"},
                            "availability": {"type": "string"},
                            "url": {"type": "string"}
                        }
                    }
                }
            }
        else:
            return {
                "product": {
                    "title": "Test Product",
                    "brand": "Brand X",
                    "description": "This is a test product description. It has some features and specifications.",
                    "price": {
                        "amount": 99.99,
                        "currency": "USD"
                    },
                    "images": [
                        {"url": "https://example.com/image1.jpg", "alt": "Test Product Image 1"},
                        {"url": "https://example.com/image2.jpg", "alt": "Test Product Image 2"}
                    ],
                    "sku": "TEST123",
                    "availability": "In Stock",
                    "url": "https://example.com/product"
                }
            }


@pytest.mark.asyncio
async def test_full_extraction_flow(test_config, mock_html_content):
    """Test the complete extraction flow from crawling to storage."""
    # Create a temp directory for storage
    storage_dir = tempfile.mkdtemp()
    test_config.storage.path = storage_dir
    
    # Setup mocks
    with patch('crawl4ai_llm.llm.factory.get_llm_client', return_value=MockLLMClient()), \
         patch.object(BaseCrawler, 'get_page', return_value=(mock_html_content, "https://example.com/product")):
        
        # Initialize components
        crawler = BaseCrawler(config=test_config.crawler)
        extractor = ProductExtractor(
            config=test_config.llm,
            schema_generator_config=test_config.llm
        )
        storage = get_storage(test_config.storage)
        
        # 1. Crawl the page
        async with crawler:
            html, url = await crawler.get_page("https://example.com/product")
            
            # 2. Extract product data
            product_data = await extractor.extract(html, url, strategy="auto")
            
            # Verify extracted data
            assert isinstance(product_data, ProductData)
            assert product_data.title == "Test Product"
            assert product_data.price.amount == 99.99
            assert product_data.price.currency == "USD"
            assert len(product_data.images) == 2
            assert product_data.sku == "TEST123"
            
            # 3. Store the product data
            product_id = storage.save_product(product_data)
            
            # 4. Verify storage
            retrieved_product = storage.get_product(product_id)
            assert retrieved_product.title == product_data.title
            assert retrieved_product.price.amount == product_data.price.amount
            
            # 5. List products with filter
            products = storage.list_products(
                filters={"title": "Test Product"}
            )
            assert len(products) == 1
            assert products[0].title == "Test Product"


@pytest.mark.asyncio
async def test_extraction_strategies(test_config, mock_html_content):
    """Test different extraction strategies."""
    # Setup mocks
    with patch('crawl4ai_llm.llm.factory.get_llm_client', return_value=MockLLMClient()), \
         patch.object(BaseCrawler, 'get_page', return_value=(mock_html_content, "https://example.com/product")):
        
        # Initialize components
        crawler = BaseCrawler(config=test_config.crawler)
        extractor = ProductExtractor(
            config=test_config.llm,
            schema_generator_config=test_config.llm
        )
        
        async with crawler:
            html, url = await crawler.get_page("https://example.com/product")
            
            # Test auto strategy
            auto_product = await extractor.extract(html, url, strategy="auto")
            assert auto_product.title == "Test Product"
            
            # Test schema strategy
            schema_product = await extractor.extract(html, url, strategy="schema")
            assert schema_product.title == "Test Product"
            
            # Test llm strategy
            llm_product = await extractor.extract(html, url, strategy="llm")
            assert llm_product.title == "Test Product"
            
            # Test fallback behavior
            with patch.object(extractor, 'extract_with_schema', side_effect=Exception("Schema extraction failed")):
                fallback_product = await extractor.extract(html, url, strategy="auto")
                assert fallback_product.title == "Test Product"


@pytest.mark.asyncio
async def test_error_handling(test_config, mock_html_content):
    """Test error handling in the extraction process."""
    # Setup mocks
    with patch('crawl4ai_llm.llm.factory.get_llm_client', return_value=MockLLMClient()):
        
        # Initialize components
        crawler = BaseCrawler(config=test_config.crawler)
        extractor = ProductExtractor(
            config=test_config.llm,
            schema_generator_config=test_config.llm
        )
        
        # Test with failing crawler
        with patch.object(BaseCrawler, 'get_page', side_effect=Exception("Connection error")):
            async with crawler:
                with pytest.raises(Exception) as excinfo:
                    await crawler.get_page("https://example.com/product")
                assert "Connection error" in str(excinfo.value)
        
        # Test with failing extractor
        with patch.object(BaseCrawler, 'get_page', return_value=(mock_html_content, "https://example.com/product")), \
             patch.object(extractor, 'extract_with_schema', side_effect=Exception("Schema error")), \
             patch.object(extractor, 'extract_with_llm', side_effect=Exception("LLM error")):
            
            async with crawler:
                html, url = await crawler.get_page("https://example.com/product")
                
                with pytest.raises(Exception) as excinfo:
                    await extractor.extract(html, url, strategy="auto")
                assert "extraction failed" in str(excinfo.value)
        
        # Test with invalid strategy
        with patch.object(BaseCrawler, 'get_page', return_value=(mock_html_content, "https://example.com/product")):
            async with crawler:
                html, url = await crawler.get_page("https://example.com/product")
                
                with pytest.raises(ValueError) as excinfo:
                    await extractor.extract(html, url, strategy="invalid")
                assert "Unknown extraction strategy" in str(excinfo.value) 