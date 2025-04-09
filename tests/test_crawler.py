"""
Unit tests for the crawler module, focusing on BaseCrawler.
"""
import pytest
import asyncio
import aiohttp
from unittest.mock import patch, MagicMock

from crawl4ai_llm.crawler.base import BaseCrawler
from crawl4ai_llm.config import CrawlerConfig


@pytest.fixture
def mock_response():
    """Return a mock HTTP response object."""
    mock = MagicMock()
    mock.status = 200
    mock.text = MagicMock(return_value=asyncio.Future())
    mock.text.return_value.set_result("<html><body>Test page content</body></html>")
    mock.headers = {"content-type": "text/html"}
    mock.url = MagicMock(return_value=asyncio.Future())
    mock.url.return_value.set_result("https://example.com/product")
    return mock


@pytest.fixture
def crawler_config():
    """Return a test crawler configuration."""
    return CrawlerConfig(
        user_agent="Test User Agent",
        request_timeout=10,
        max_retries=3,
        retry_delay=1,
        rate_limit=5,
        rate_limit_period=1,
        headers={
            "Accept-Language": "en-US,en;q=0.9",
        },
        proxies=None
    )


class TestBaseCrawler:
    """Test suite for BaseCrawler class."""
    
    @pytest.mark.asyncio
    async def test_init(self, crawler_config):
        """Test crawler initialization."""
        crawler = BaseCrawler(config=crawler_config)
        
        assert crawler.config == crawler_config
        assert crawler._session is None
        assert crawler._rate_limiter is not None
        
        # Test with default config
        default_crawler = BaseCrawler()
        assert default_crawler.config is not None
        assert default_crawler.config.user_agent is not None
        
    @pytest.mark.asyncio
    async def test_setup_session(self, crawler_config):
        """Test session setup."""
        crawler = BaseCrawler(config=crawler_config)
        await crawler.setup()
        
        assert crawler._session is not None
        assert isinstance(crawler._session, aiohttp.ClientSession)
        
        # Check session headers
        assert crawler._session._default_headers.get("User-Agent") == crawler_config.user_agent
        assert crawler._session._default_headers.get("Accept-Language") == crawler_config.headers.get("Accept-Language")
        
    @pytest.mark.asyncio
    async def test_cleanup(self, crawler_config):
        """Test session cleanup."""
        crawler = BaseCrawler(config=crawler_config)
        await crawler.setup()
        assert crawler._session is not None
        
        await crawler.cleanup()
        assert crawler._session.closed
        
    @pytest.mark.asyncio
    async def test_get_page_successful(self, crawler_config, mock_response):
        """Test successful page retrieval."""
        crawler = BaseCrawler(config=crawler_config)
        
        # Mock the session and response
        with patch.object(crawler, "_session", MagicMock()) as mock_session:
            mock_session.get = MagicMock(return_value=asyncio.Future())
            mock_session.get.return_value.set_result(mock_response)
            
            html, url = await crawler.get_page("https://example.com/product")
            
            # Verify correct URL was requested
            mock_session.get.assert_called_once()
            assert "https://example.com/product" in str(mock_session.get.call_args)
            
            # Verify response processing
            assert "<html>" in html
            assert "Test page content" in html
    
    @pytest.mark.asyncio
    async def test_get_page_retry_on_error(self, crawler_config):
        """Test retry behavior on HTTP errors."""
        crawler = BaseCrawler(config=crawler_config)
        
        # Create a response that fails first, then succeeds
        error_response = MagicMock()
        error_response.status = 503
        error_response.text = MagicMock(return_value=asyncio.Future())
        error_response.text.return_value.set_result("Service Unavailable")
        
        success_response = MagicMock()
        success_response.status = 200
        success_response.text = MagicMock(return_value=asyncio.Future())
        success_response.text.return_value.set_result("<html>Success</html>")
        success_response.headers = {"content-type": "text/html"}
        success_response.url = MagicMock(return_value=asyncio.Future())
        success_response.url.return_value.set_result("https://example.com/product")
        
        # Mock the session to return error first, then success
        with patch.object(crawler, "_session", MagicMock()) as mock_session:
            mock_session.get = MagicMock(side_effect=[
                asyncio.Future(),
                asyncio.Future()
            ])
            mock_session.get.side_effect[0].set_result(error_response)
            mock_session.get.side_effect[1].set_result(success_response)
            
            # Mock sleep to speed up test
            with patch("asyncio.sleep", MagicMock()):
                html, url = await crawler.get_page("https://example.com/product")
                
                # Verify retry happened
                assert mock_session.get.call_count == 2
                assert "Success" in html
    
    @pytest.mark.asyncio
    async def test_get_page_max_retries_exceeded(self, crawler_config):
        """Test behavior when max retries are exceeded."""
        crawler = BaseCrawler(config=crawler_config)
        
        # Create an error response
        error_response = MagicMock()
        error_response.status = 404
        error_response.text = MagicMock(return_value=asyncio.Future())
        error_response.text.return_value.set_result("Not Found")
        
        # Mock the session to always return error
        with patch.object(crawler, "_session", MagicMock()) as mock_session:
            futures = [asyncio.Future() for _ in range(crawler_config.max_retries + 1)]
            mock_session.get = MagicMock(side_effect=futures)
            for future in futures:
                future.set_result(error_response)
            
            # Mock sleep to speed up test
            with patch("asyncio.sleep", MagicMock()):
                with pytest.raises(Exception) as excinfo:
                    await crawler.get_page("https://example.com/product")
                
                # Verify error message contains status code
                assert "404" in str(excinfo.value)
                
                # Verify all retries were attempted
                assert mock_session.get.call_count == crawler_config.max_retries + 1
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, crawler_config, mock_response):
        """Test rate limiting behavior."""
        # Create a crawler with strict rate limiting
        strict_config = crawler_config.model_copy()
        strict_config.rate_limit = 2
        strict_config.rate_limit_period = 1
        
        crawler = BaseCrawler(config=strict_config)
        
        # Mock the session to always return success
        with patch.object(crawler, "_session", MagicMock()) as mock_session:
            mock_session.get = MagicMock(return_value=asyncio.Future())
            mock_session.get.return_value.set_result(mock_response)
            
            # Mock time.time to control timing
            current_time = 0
            time_values = [current_time, current_time, current_time + 0.1, current_time + 0.2]
            
            with patch("time.time", side_effect=time_values):
                # Mock sleep to record calls
                with patch("asyncio.sleep") as mock_sleep:
                    # First two requests should not be delayed
                    await crawler.get_page("https://example.com/product/1")
                    await crawler.get_page("https://example.com/product/2")
                    mock_sleep.assert_not_called()
                    
                    # Third request should be delayed
                    await crawler.get_page("https://example.com/product/3")
                    mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_headers_and_cookies(self, crawler_config, mock_response):
        """Test custom headers and cookies."""
        crawler = BaseCrawler(config=crawler_config)
        
        # Mock the session
        with patch.object(crawler, "_session", MagicMock()) as mock_session:
            mock_session.get = MagicMock(return_value=asyncio.Future())
            mock_session.get.return_value.set_result(mock_response)
            
            # Add custom headers and cookies
            custom_headers = {"X-Custom": "Value"}
            cookies = {"session": "test_session"}
            
            await crawler.get_page(
                "https://example.com/product", 
                headers=custom_headers,
                cookies=cookies
            )
            
            # Verify headers and cookies were passed
            call_kwargs = mock_session.get.call_args[1]
            assert "headers" in call_kwargs
            assert call_kwargs["headers"]["X-Custom"] == "Value"
            
            assert "cookies" in call_kwargs
            assert call_kwargs["cookies"]["session"] == "test_session"
    
    @pytest.mark.asyncio
    async def test_context_manager(self, crawler_config):
        """Test using crawler as context manager."""
        crawler = BaseCrawler(config=crawler_config)
        
        # Patch setup and cleanup methods
        with patch.object(crawler, "setup") as mock_setup, \
             patch.object(crawler, "cleanup") as mock_cleanup:
            
            async with crawler:
                # Verify setup was called
                mock_setup.assert_called_once()
                mock_cleanup.assert_not_called()
            
            # Verify cleanup was called after context exit
            mock_cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_proxy_configuration(self, crawler_config):
        """Test proxy configuration."""
        # Add proxy configuration
        proxy_config = crawler_config.model_copy()
        proxy_config.proxies = {
            "http": "http://proxy.example.com:8080",
            "https": "https://proxy.example.com:8080"
        }
        
        crawler = BaseCrawler(config=proxy_config)
        
        # Create mock ClientSession to capture creation args
        client_session_mock = MagicMock()
        
        with patch("aiohttp.ClientSession", client_session_mock):
            await crawler.setup()
            
            # Check that proxy was passed to session
            _, kwargs = client_session_mock.call_args
            assert "proxy" in kwargs
            assert kwargs["proxy"] == "http://proxy.example.com:8080" 