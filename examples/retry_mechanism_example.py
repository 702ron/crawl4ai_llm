#!/usr/bin/env python
"""
Example demonstrating retry mechanism for handling failed requests.

This example shows:
1. Automatic retries for failed requests
2. Exponential backoff with jitter
3. Custom retry conditions
4. Handling of transient failures
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl4ai_llm.crawler import BaseCrawler, ContentFilter
from crawl4ai_llm.crawler.content_filter import CSSFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Sample URLs for testing retry behavior
# These include intentionally problematic URLs to demonstrate retry behavior
RETRY_TEST_URLS = [
    # Valid URL - should succeed without retries
    "https://www.amazon.com/dp/B079L9Z1T6",
    
    # Invalid URL - will cause an error and trigger retries
    "https://this-website-does-not-exist-12345.com/product",
    
    # URL with rate limiting - might require retries
    "https://api.github.com/rate_limit",
    
    # URL that sometimes times out - might trigger retries
    "https://httpbin.org/delay/10",
]


async def demonstrate_standard_retry() -> None:
    """
    Demonstrate the standard retry mechanism with default settings.
    """
    print(f"\n{'='*80}\nStandard Retry Mechanism\n{'='*80}")
    
    # Create a crawler with default retry settings
    crawler = BaseCrawler(
        max_retries=3,  # Retry up to 3 times
        retry_delay=1.0,  # Start with 1 second delay
        retry_backoff_factor=2.0,  # Double the delay each time
        retry_jitter=0.3,  # Add up to 30% random jitter
        timeout=5000,  # Short timeout to trigger retries faster (5 seconds)
    )
    
    print("Testing with standard retry settings:")
    print(f"  Max retries: {crawler.max_retries}")
    print(f"  Initial delay: {crawler.retry_delay}s")
    print(f"  Backoff factor: {crawler.retry_backoff_factor}x")
    print(f"  Jitter: {crawler.retry_jitter * 100}%")
    
    # Try the invalid URL to see retry behavior
    print("\nCrawling invalid URL (expect failures and retries):")
    start_time = time.time()
    result = await crawler.crawl(RETRY_TEST_URLS[1])
    end_time = time.time()
    
    # Display results
    print(f"\nResult after {result.get('retries', 0)} retries:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Error: {result.get('error', 'None')}")
    print(f"  Time taken: {end_time - start_time:.2f} seconds")
    
    await crawler.close()


async def demonstrate_custom_retry_condition() -> None:
    """
    Demonstrate using a custom retry condition.
    """
    print(f"\n{'='*80}\nCustom Retry Condition\n{'='*80}")
    
    # Define a custom retry condition function
    def custom_retry_condition(result: Dict[str, Any]) -> bool:
        """
        Custom retry condition that checks for specific content.
        
        Args:
            result: The result dictionary from a crawl attempt.
            
        Returns:
            True if the request should be retried, False otherwise.
        """
        # Always retry if the request failed
        if not result.get("success", False):
            return True
            
        # Get the HTML content
        html = result.get("html", "")
        
        # Retry if we don't have HTML or it's very small
        if not html or len(html) < 1000:
            return True
            
        # Retry if we don't see a product title (specific to our target)
        if "product-title" not in html and "productTitle" not in html:
            print("  -> Retrying: Couldn't find product title in content")
            return True
            
        # Look for rate limit messages
        rate_limit_indicators = [
            "rate limit exceeded",
            "too many requests",
            "429 Too Many Requests"
        ]
        for indicator in rate_limit_indicators:
            if indicator.lower() in html.lower():
                print(f"  -> Retrying: Found rate limit indicator: '{indicator}'")
                return True
                
        # No need to retry if we got here
        return False
    
    # Create a crawler with custom retry condition
    crawler = BaseCrawler(
        max_retries=4,
        retry_delay=2.0,
        retry_condition=custom_retry_condition,
        content_filters=[
            ContentFilter(
                name="Product Title",
                filter_type=CSSFilter("#productTitle, .product-title, h1.title")
            )
        ]
    )
    
    # Test with a URL that should contain product title
    print("Testing custom retry condition with valid URL:")
    print("(This should succeed once it finds a product title)")
    result = await crawler.crawl(RETRY_TEST_URLS[0])
    
    # Display results
    print(f"\nResult after {result.get('retries', 0)} retries:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Found title: {'Yes' if result.get('extracted_content') else 'No'}")
    
    if result.get('extracted_content'):
        print(f"  Title: {result.get('extracted_content')[0]}")
    
    await crawler.close()


async def demonstrate_timeout_retry() -> None:
    """
    Demonstrate handling timeout errors with retries.
    """
    print(f"\n{'='*80}\nTimeout Retry Handling\n{'='*80}")
    
    # Create a crawler with very short timeout to demonstrate timeout retries
    crawler = BaseCrawler(
        timeout=1000,  # Very short 1 second timeout
        max_retries=2,
        retry_delay=1.0,
    )
    
    print("Testing with intentionally short timeout (1s) on slow URL:")
    print("URL: https://httpbin.org/delay/10 (takes 10s to respond)")
    
    # Try fetching a URL that takes longer than our timeout
    start_time = time.time()
    result = await crawler.crawl(RETRY_TEST_URLS[3])
    end_time = time.time()
    
    # Display results
    print(f"\nResult after {result.get('retries', 0)} retries:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Error: {result.get('error', 'None')}")
    print(f"  Time taken: {end_time - start_time:.2f} seconds")
    
    await crawler.close()
    
    print("\nNow trying with longer timeout (15s):")
    crawler2 = BaseCrawler(
        timeout=15000,  # 15 seconds timeout
        max_retries=2,
        retry_delay=1.0,
    )
    
    start_time = time.time()
    result = await crawler2.crawl(RETRY_TEST_URLS[3])
    end_time = time.time()
    
    # Display results
    print(f"\nResult after {result.get('retries', 0)} retries:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Time taken: {end_time - start_time:.2f} seconds")
    
    await crawler2.close()


async def main():
    """
    Run all example demonstrations.
    """
    print("Retry Mechanism Examples")
    
    # Standard retry behavior
    await demonstrate_standard_retry()
    
    # Custom retry condition
    await demonstrate_custom_retry_condition()
    
    # Timeout handling
    await demonstrate_timeout_retry()
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main()) 