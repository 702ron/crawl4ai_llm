"""
Base crawler class for fetching product pages from e-commerce websites.
"""

import asyncio
from typing import Optional, Dict, Any, List, Union
import logging
from datetime import datetime

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from ..config import config
from .content_filter import ContentFilter, ContentFilterChain

# Set up logging
logger = logging.getLogger(__name__)


class BaseCrawler:
    """Base crawler class with session management and rate limiting."""
    
    def __init__(
        self,
        headless: Optional[bool] = None, 
        cache_mode: CacheMode = CacheMode.ENABLED,
        user_agent: Optional[str] = None,
        timeout: int = 60000,
        content_filters: Optional[List[Union[ContentFilter, ContentFilterChain]]] = None,
    ):
        """
        Initialize the crawler with configured settings.
        
        Args:
            headless: Whether to run the browser in headless mode. If None, uses config value.
            cache_mode: Cache mode for Crawl4AI crawler.
            user_agent: User agent string to use for requests. If None, uses config value.
            timeout: Page load timeout in milliseconds.
            content_filters: Content filters to apply during crawling. Can include both ContentFilter
                            and ContentFilterChain instances.
        """
        self.headless = headless if headless is not None else config.crawler.headless
        self.user_agent = user_agent or config.crawler.user_agent
        self.cache_mode = cache_mode
        self.timeout = timeout
        self.content_filters = content_filters or []
        
        # Rate limiting
        self.rate_limit = config.crawler.rate_limit
        self._last_request_time = None
        self._rate_limit_lock = asyncio.Lock()
        
    async def _get_browser_config(self) -> BrowserConfig:
        """
        Get the browser configuration for Crawl4AI.
        
        Returns:
            BrowserConfig: Configured browser settings.
        """
        return BrowserConfig(
            headless=self.headless,
            user_agent=self.user_agent
        )
    
    async def _get_crawler_config(self, **kwargs) -> CrawlerRunConfig:
        """
        Get the crawler configuration for Crawl4AI.
        
        Args:
            **kwargs: Additional configuration options.
            
        Returns:
            CrawlerRunConfig: Configured crawler settings.
        """
        # Convert our ContentFilter instances to crawl4ai ContentFilter instances
        # For ContentFilterChain instances, we'll handle them in our own post-processing
        crawl4ai_filters = []
        
        if self.content_filters:
            for cf in self.content_filters:
                if isinstance(cf, ContentFilter):
                    crawl4ai_filters.append(cf._filter)
        
        # Create the config with only the parameters that CrawlerRunConfig accepts
        config_dict = {
            "cache_mode": self.cache_mode,
            "page_timeout": self.timeout,
        }
        
        if crawl4ai_filters:
            # Only add the content_filters parameter if we have filters and
            # the CrawlerRunConfig class accepts it
            try:
                # Try to create a config with content_filters
                test_config = CrawlerRunConfig(
                    cache_mode=self.cache_mode,
                    page_timeout=self.timeout,
                    content_filters=crawl4ai_filters
                )
                # If successful, add content_filters to the config dictionary
                config_dict["content_filters"] = crawl4ai_filters
            except TypeError:
                # If content_filters is not a valid parameter, log a warning
                logger.warning(
                    "CrawlerRunConfig does not accept content_filters parameter. "
                    "Content filters may not be applied during crawling."
                )
        
        # Add any additional kwargs
        config_dict.update(kwargs)
        
        return CrawlerRunConfig(**config_dict)
    
    async def _enforce_rate_limit(self):
        """
        Enforce rate limiting for requests.
        Ensures requests don't exceed the configured rate limit.
        """
        async with self._rate_limit_lock:
            if self._last_request_time is not None:
                # Calculate time since last request
                now = datetime.now()
                time_diff = (now - self._last_request_time).total_seconds()
                min_interval = 60.0 / self.rate_limit  # seconds per request
                
                if time_diff < min_interval:
                    # Need to wait to respect rate limit
                    wait_time = min_interval - time_diff
                    logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
            
            self._last_request_time = datetime.now()
    
    async def _apply_filter_chains(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply any ContentFilterChain instances to the crawl result.
        
        Args:
            result: The result from crawl4ai's crawler.
            
        Returns:
            Updated result with additional extracted content from ContentFilterChain instances.
        """
        if not self.content_filters or not result.get("html"):
            return result
        
        html = result["html"]
        extracted_content = result.get("extracted_content", [])
        
        # Add extracted content from ContentFilterChain instances
        for cf in self.content_filters:
            if isinstance(cf, ContentFilterChain):
                chain_results = cf.filter_content(html)
                if chain_results:
                    # Add a label for this chain's results if it has a name
                    if cf.name:
                        extracted_content.append(f"--- {cf.name} ---")
                    extracted_content.extend(chain_results)
        
        result["extracted_content"] = extracted_content
        return result
    
    async def crawl(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Crawl a product page and return the result.
        
        Args:
            url: URL of the product page to crawl.
            **kwargs: Additional crawler configuration options.
            
        Returns:
            Dict[str, Any]: Crawl result containing HTML, Markdown, and any extracted content.
        """
        await self._enforce_rate_limit()
        
        browser_config = await self._get_browser_config()
        crawler_config = await self._get_crawler_config(**kwargs)
        
        logger.info(f"Crawling URL: {url}")
        async with AsyncWebCrawler(config=browser_config) as crawler:
            try:
                result = await crawler.arun(url=url, config=crawler_config)
                result_dict = {
                    "html": result.html,
                    "markdown": result.markdown,
                    "extracted_content": result.extracted_content,
                    "success": True,
                    "url": url,
                    "timestamp": datetime.now().isoformat(),
                }
                
                # Apply any ContentFilterChain instances
                result_dict = await self._apply_filter_chains(result_dict)
                
                return result_dict
            except Exception as e:
                logger.error(f"Error crawling {url}: {str(e)}")
                return {
                    "html": None,
                    "markdown": None,
                    "extracted_content": None,
                    "success": False,
                    "url": url,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                } 