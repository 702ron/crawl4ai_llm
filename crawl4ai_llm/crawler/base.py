"""
Base crawler class for fetching product pages from e-commerce websites.
"""

import asyncio
import logging
import time
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable

from crawl4ai import (AsyncWebCrawler, BrowserConfig, CacheMode,
                      CrawlerRunConfig)

from ..config import config
from .content_filter import ContentFilter, ContentFilterChain
from .js_renderer import JavaScriptRenderer
from .retry_handler import RetryHandler, RetryStrategy

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
        content_filters: Optional[
            List[Union[ContentFilter, ContentFilterChain]]
        ] = None,
        js_enabled: Optional[bool] = None,
        wait_for_load: Optional[int] = None,
        wait_for_selector: Optional[str] = None, 
        wait_for_function: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        retry_strategy: str = RetryStrategy.EXPONENTIAL,
        retry_backoff_factor: float = 1.5,
        retry_jitter: float = 0.5,
        retry_condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
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
            js_enabled: Whether to enable JavaScript rendering. If None, uses config value.
            wait_for_load: Time to wait after initial navigation (in ms). If None, uses config value.
            wait_for_selector: CSS selector to wait for before considering page loaded. If None, uses config value.
            wait_for_function: JavaScript function to evaluate to determine when page is loaded. If None, uses config value.
            max_retries: Maximum number of retry attempts for failed requests.
            retry_delay: Initial delay between retries in seconds.
            retry_strategy: Strategy for retry delays (fixed, linear, exponential, fibonacci).
            retry_backoff_factor: Multiplication factor for exponential backoff between retries.
            retry_jitter: Random jitter factor to add to retry delays (0-1).
            retry_condition: Custom function to determine if a result should trigger a retry.
                            Function takes a result dict and returns True if retry is needed.
        """
        self.headless = headless if headless is not None else config.crawler.headless
        self.user_agent = user_agent or config.crawler.user_agent
        self.cache_mode = cache_mode
        self.timeout = timeout
        self.content_filters = content_filters or []
        self.js_enabled = js_enabled if js_enabled is not None else config.crawler.js_rendering
        self.wait_for_load = wait_for_load
        self.wait_for_selector = wait_for_selector
        self.wait_for_function = wait_for_function
        
        # Set up retry handler
        self.retry_handler = RetryHandler(
            max_retries=max_retries,
            retry_delay=retry_delay,
            strategy=retry_strategy,
            backoff_factor=retry_backoff_factor,
            jitter=retry_jitter,
            retry_condition=retry_condition or self._default_retry_condition
        )

        # Rate limiting
        self.rate_limit = config.crawler.rate_limit
        self._last_request_time = None
        self._rate_limit_lock = asyncio.Lock()
        self._js_renderer = None

    async def _get_browser_config(self) -> BrowserConfig:
        """
        Get the browser configuration for Crawl4AI.

        Returns:
            BrowserConfig: Configured browser settings.
        """
        return BrowserConfig(headless=self.headless, user_agent=self.user_agent)

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
                    content_filters=crawl4ai_filters,
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

    async def _get_js_renderer(self) -> JavaScriptRenderer:
        """
        Get or create a JavaScript renderer instance.

        Returns:
            JavaScriptRenderer: The JavaScript renderer.
        """
        if not self._js_renderer:
            self._js_renderer = JavaScriptRenderer(
                headless=self.headless,
                user_agent=self.user_agent,
                timeout=self.timeout,
                wait_for_load=self.wait_for_load,
                wait_for_selector=self.wait_for_selector,
                wait_for_function=self.wait_for_function,
                content_filters=self.content_filters,
            )
        return self._js_renderer

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
        
    def _default_retry_condition(self, result: Dict[str, Any]) -> bool:
        """
        Default condition to determine if a request should be retried.
        
        Args:
            result: The result dictionary from a crawl attempt.
            
        Returns:
            True if the request should be retried, False otherwise.
        """
        # Retry if request was not successful
        if not result.get("success", False):
            return True
            
        # Retry if HTML is empty or very small (likely not fully loaded)
        html = result.get("html", "")
        if not html or len(html) < 500:  # Arbitrary small size threshold
            return True
            
        # Don't retry if we have a valid HTML response with content
        return False

    async def _crawl_with_js(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Crawl a URL using JavaScript rendering.
        
        Args:
            url: URL to crawl.
            **kwargs: Additional options for the renderer.
            
        Returns:
            Crawl result.
        """
        js_renderer = await self._get_js_renderer()
        result = await js_renderer.render(url, **kwargs)
        
        # Add timestamp
        result["timestamp"] = datetime.now().isoformat()
        
        return result
        
    async def _crawl_without_js(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Crawl a URL using the standard (non-JS) crawler.
        
        Args:
            url: URL to crawl.
            **kwargs: Additional crawler configuration options.
            
        Returns:
            Crawl result.
        """
        browser_config = await self._get_browser_config()
        crawler_config = await self._get_crawler_config(**kwargs)
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
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
            return await self._apply_filter_chains(result_dict)

    async def crawl(self, url: str, force_js: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Crawl a product page and return the result.

        Args:
            url: URL of the product page to crawl.
            force_js: Whether to force using JavaScript rendering even if js_enabled is False.
            **kwargs: Additional crawler configuration options.

        Returns:
            Dict[str, Any]: Crawl result containing HTML, Markdown, and any extracted content.
        """
        # Check if we should use JavaScript rendering
        use_js = self.js_enabled or force_js
        
        # Create the crawl function based on whether we're using JS
        async def do_crawl():
            # Enforce rate limiting
            await self._enforce_rate_limit()
            
            if use_js:
                # Use JavaScript rendering with Playwright
                logger.info(f"Using JavaScript rendering for URL: {url}")
                return await self._crawl_with_js(url, **kwargs)
            else:
                # Use standard Crawl4AI crawler
                logger.info(f"Crawling URL: {url}")
                return await self._crawl_without_js(url, **kwargs)
        
        try:
            # Execute the crawl with retry logic
            result = await self.retry_handler.execute(do_crawl)
            # Add retry count (will be zero if succeeded on first attempt)
            result["retries"] = self.retry_handler.max_retries - self.retry_handler.attempts_remaining
            return result
            
        except Exception as e:
            # Handle case where all retries failed
            logger.error(f"Failed to crawl {url} after {self.retry_handler.max_retries} retries: {str(e)}")
            return {
                "html": None,
                "markdown": None,
                "extracted_content": None,
                "success": False,
                "url": url,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "retries": self.retry_handler.max_retries,
            }

    async def close(self):
        """
        Close any resources used by the crawler.
        """
        if self._js_renderer:
            await self._js_renderer.close()
            self._js_renderer = None
