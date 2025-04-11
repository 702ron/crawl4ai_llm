"""
JavaScript renderer using Playwright for handling dynamic content on e-commerce sites.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, List, Union

from playwright.async_api import async_playwright, Browser, Page, Response

from ..config import config
from .content_filter import ContentFilter, ContentFilterChain

logger = logging.getLogger(__name__)


class JavaScriptRenderer:
    """
    Class for rendering JavaScript-heavy pages using Playwright.
    """

    def __init__(
        self,
        headless: Optional[bool] = None,
        user_agent: Optional[str] = None,
        timeout: int = 60000,
        wait_for_load: Optional[int] = None,
        wait_for_selector: Optional[str] = None,
        wait_for_function: Optional[str] = None,
        content_filters: Optional[
            List[Union[ContentFilter, ContentFilterChain]]
        ] = None,
    ):
        """
        Initialize the JavaScript renderer.

        Args:
            headless: Whether to run the browser in headless mode. If None, uses config value.
            user_agent: User agent string to use for requests. If None, uses config value.
            timeout: Page load timeout in milliseconds.
            wait_for_load: Time to wait after initial navigation (in ms). If None, uses config value.
            wait_for_selector: CSS selector to wait for before considering page loaded. If None, uses config value.
            wait_for_function: JavaScript function to evaluate to determine when page is loaded. If None, uses config value.
            content_filters: Content filters to apply after rendering.
        """
        self.headless = headless if headless is not None else config.crawler.headless
        self.user_agent = user_agent or config.crawler.user_agent
        self.timeout = timeout
        self.wait_for_load = wait_for_load if wait_for_load is not None else config.crawler.wait_for_load
        self.wait_for_selector = wait_for_selector or config.crawler.wait_for_selector
        self.wait_for_function = wait_for_function or config.crawler.wait_for_function
        self.content_filters = content_filters or []
        self._browser = None

    async def _get_browser(self) -> Browser:
        """
        Initialize and return a Playwright browser instance.

        Returns:
            Browser: Initialized browser instance.
        """
        if not self._browser:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
        return self._browser

    async def _configure_page(self, page: Page) -> None:
        """
        Configure page with user agent and other settings.

        Args:
            page: Playwright page to configure.
        """
        if self.user_agent:
            await page.set_extra_http_headers({"User-Agent": self.user_agent})
        
        # Set timeout using the page's property instead of a method if set_default_timeout is not available
        try:
            # Try to set timeout using the preferred method
            if hasattr(page, 'set_default_timeout') and callable(page.set_default_timeout):
                await page.set_default_timeout(self.timeout)
            else:
                # Fallback: Set individual timeouts if available
                if hasattr(page, 'set_default_navigation_timeout') and callable(page.set_default_navigation_timeout):
                    await page.set_default_navigation_timeout(self.timeout)
                if hasattr(page, 'set_default_timeout') and callable(page.set_default_timeout):
                    await page.set_default_timeout(self.timeout)
                logger.warning("Using fallback timeout setting methods for Playwright")
        except Exception as e:
            logger.warning(f"Could not set page timeout: {str(e)}. Continuing without timeout setting.")

    async def _wait_for_page_load(self, page: Page) -> None:
        """
        Wait for the page to be fully loaded based on configured criteria.

        Args:
            page: The Playwright page to wait for.
        """
        try:
            # First wait for initial load event
            load_states = ["networkidle", "domcontentloaded", "load"]
            success = False
            
            for state in load_states:
                try:
                    logger.debug(f"Waiting for load state: {state}")
                    await page.wait_for_load_state(state, timeout=self.timeout)
                    success = True
                    logger.debug(f"Successfully waited for {state}")
                    break
                except Exception as e:
                    logger.warning(f"Error waiting for {state}: {str(e)}")
                    continue
            
            if not success:
                logger.warning("Failed to detect page load state, using fallback delay")
                await asyncio.sleep(5)  # Fallback delay

            # Evaluate custom JavaScript function if specified
            if self.wait_for_function:
                try:
                    # Wrap the function to make it poll until true or timeout
                    poll_script = f"""
                    async function waitForCondition(timeoutMs) {{
                        const startTime = Date.now();
                        const checkCondition = () => {{
                            try {{
                                const condition = ({self.wait_for_function})();
                                return condition;
                            }} catch (error) {{
                                console.error('Error in wait function:', error);
                                return false;
                            }}
                        }};
                        
                        while (Date.now() - startTime < timeoutMs) {{
                            if (checkCondition()) {{
                                return true;
                            }}
                            await new Promise(resolve => setTimeout(resolve, 100));
                        }}
                        return false;
                    }}
                    await waitForCondition({self.timeout});
                    """
                    
                    logger.debug("Evaluating custom wait function")
                    result = await page.evaluate(poll_script)
                    if not result:
                        logger.warning("Custom wait function timed out")
                    else:
                        logger.debug("Custom wait function completed successfully")
                        
                except Exception as e:
                    logger.error(f"Error evaluating custom wait function: {str(e)}")
                    # Continue execution even if wait function fails
                    
        except Exception as e:
            logger.error(f"Error in page load wait: {str(e)}")
            # Let the error propagate up if we can't handle page load

    async def _apply_filters(self, html: str) -> List[str]:
        """
        Apply content filters to the rendered HTML.

        Args:
            html: HTML content to filter.

        Returns:
            List of extracted content from filters.
        """
        if not self.content_filters:
            return []

        extracted_content = []
        
        for cf in self.content_filters:
            if isinstance(cf, ContentFilter):
                content = cf.filter_content(html)
                if content:
                    extracted_content.append(content)
            elif isinstance(cf, ContentFilterChain):
                chain_results = cf.filter_content(html)
                if chain_results:
                    # Add a label for this chain's results if it has a name
                    if cf.name:
                        extracted_content.append(f"--- {cf.name} ---")
                    extracted_content.extend(chain_results)

        return extracted_content

    async def render(self, url: str) -> Dict[str, Any]:
        """
        Render a URL using Playwright and return the rendered HTML content.

        Args:
            url: The URL to render.

        Returns:
            Dict containing:
                - success (bool): Whether rendering was successful
                - html (str): The rendered HTML content if successful
                - error (str): Error message if unsuccessful
                - extracted_content (List[str]): Any content extracted via filters
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                # Set up error handling
                page.on("pageerror", lambda err: logger.error(f"Page error: {err}"))
                page.on("console", lambda msg: logger.debug(f"Console {msg.type}: {msg.text}"))

                try:
                    logger.debug(f"Navigating to {url}")
                    response = await page.goto(url, wait_until="commit", timeout=self.timeout)
                    
                    if not response:
                        logger.error("Failed to get response from page")
                        return {
                            "success": False,
                            "html": None,
                            "error": "Failed to get response from page",
                            "extracted_content": []
                        }
                        
                    if not response.ok:
                        error_msg = f"HTTP error {response.status}: {response.status_text}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "html": None,
                            "error": error_msg,
                            "extracted_content": []
                        }

                    await self._wait_for_page_load(page)
                    
                    # Get the final HTML content
                    content = await page.content()
                    logger.debug("Successfully retrieved rendered content")
                    
                    # Apply content filters if available
                    extracted_content = await self._apply_filters(content)
                    
                    return {
                        "success": True,
                        "html": content,
                        "error": None,
                        "extracted_content": extracted_content
                    }

                except Exception as e:
                    error_msg = f"Error during page rendering: {str(e)}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "html": None,
                        "error": error_msg,
                        "extracted_content": []
                    }
                    
                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            error_msg = f"Error setting up browser: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "html": None,
                "error": error_msg,
                "extracted_content": []
            }

    async def close(self) -> None:
        """
        Close the browser and playwright instances.
        """
        if self._browser:
            await self._browser.close()
            self._browser = None
            
        if hasattr(self, '_playwright'):
            await self._playwright.stop()
            delattr(self, '_playwright')

    async def __aenter__(self):
        """
        Async context manager entry.
        """
        await self._get_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.
        """
        await self.close() 