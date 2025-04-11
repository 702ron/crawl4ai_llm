#!/usr/bin/env python
"""
Example demonstrating JavaScript rendering capabilities for e-commerce sites.

This example shows:
1. Basic usage of BaseCrawler with JavaScript rendering enabled
2. Direct usage of JavaScriptRenderer for specific JS-heavy pages
3. Comparison between regular and JavaScript-enabled crawling
4. Handling dynamic content with selectors and custom wait logic
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from bs4 import BeautifulSoup

# Add the parent directory to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl4ai_llm.crawler import BaseCrawler, ContentFilter, JavaScriptRenderer
from crawl4ai_llm.crawler.content_filter import CSSFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Example URLs with JavaScript-rendered content
JS_HEAVY_URLS = [
    "https://www.bestbuy.com/site/apple-iphone-14-pro-128gb-deep-purple-verizon/6504735.p",
    "https://www.target.com/p/apple-airpods-pro-2nd-generation/-/A-85978612",
    "https://www.walmart.com/ip/PlayStation-5-Console-Marvel-s-Spider-Man-2-Bundle/3000817400",
]

# CSS selectors to demonstrate wait_for_selector functionality
SELECTORS = {
    "bestbuy.com": ".shop-product-title h1",
    "target.com": "[data-test='product-title']",
    "walmart.com": "[data-testid='product-title']",
}


async def crawl_with_and_without_js(url: str) -> None:
    """
    Crawl a URL with and without JavaScript rendering for comparison.
    
    Args:
        url: URL to crawl
    """
    print(f"\n{'='*80}\nComparing crawl results for: {url}\n{'='*80}")
    
    # Extract domain for selector lookup
    domain = url.split("/")[2].replace("www.", "")
    selector = SELECTORS.get(domain)
    
    # Create a content filter to extract product title for comparison
    title_filter = ContentFilter(
        name="Title",
        filter_type=CSSFilter(selector) if selector else None
    )
    
    # Create crawlers
    regular_crawler = BaseCrawler(
        content_filters=[title_filter],
        js_enabled=False
    )
    
    js_crawler = BaseCrawler(
        content_filters=[title_filter],
        js_enabled=True,
        wait_for_selector=selector,  # Wait for product title to appear
        wait_for_load=2000,  # Wait additional 2 seconds after load
    )
    
    # Crawl with regular crawler
    print("Crawling without JavaScript...")
    regular_result = await regular_crawler.crawl(url)
    
    # Crawl with JavaScript-enabled crawler
    print("Crawling with JavaScript...")
    js_result = await js_crawler.crawl(url)
    
    # Close the crawler resources
    await regular_crawler.close()
    await js_crawler.close()
    
    # Compare results
    compare_results(regular_result, js_result)


def compare_results(regular: Dict[str, Any], js: Dict[str, Any]) -> None:
    """
    Compare and display the differences between regular and JS-enabled crawl results.
    
    Args:
        regular: Result from regular crawler
        js: Result from JS-enabled crawler
    """
    print("\nCOMPARISON RESULTS:")
    print(f"Regular crawl success: {regular['success']}")
    print(f"JS crawl success: {js['success']}")
    
    # Compare HTML length
    if regular['html'] and js['html']:
        reg_len = len(regular['html'])
        js_len = len(js['html'])
        print(f"Regular HTML length: {reg_len:,} characters")
        print(f"JS-rendered HTML length: {js_len:,} characters")
        print(f"Difference: {js_len - reg_len:+,} characters ({(js_len/reg_len - 1)*100:.1f}%)")
    
    # Compare extracted content
    print("\nExtracted content comparison:")
    print("Regular crawl extracted:")
    display_extracted_content(regular.get('extracted_content', []))
    
    print("\nJS crawl extracted:")
    display_extracted_content(js.get('extracted_content', []))


def display_extracted_content(content: List[str]) -> None:
    """
    Display extracted content in a readable format.
    
    Args:
        content: List of extracted content strings
    """
    if not content:
        print("  No content extracted")
        return
        
    for i, item in enumerate(content):
        # Truncate long content for display
        if len(item) > 100:
            item = item[:97] + "..."
        print(f"  {i+1}. {item}")


async def demonstrate_js_renderer_directly() -> None:
    """
    Demonstrate direct usage of the JavaScriptRenderer class.
    """
    print(f"\n{'='*80}\nDirect JavaScriptRenderer usage example\n{'='*80}")
    
    # Create the renderer with custom settings
    async with JavaScriptRenderer(
        headless=True,
        wait_for_load=5000,  # 5 seconds
        wait_for_selector="#productTitle",  # Amazon product title selector
        content_filters=[
            ContentFilter(
                name="Product Title",
                filter_type=CSSFilter("#productTitle")
            )
        ]
    ) as renderer:
        # Render an Amazon product page
        url = "https://www.amazon.com/Apple-MacBook-16-inch-10%E2%80%91core-16%E2%80%91core/dp/B0BSHF7LLL/"
        print(f"Rendering {url} with JavaScript...")
        result = await renderer.render(url)
        
        # Display results
        print(f"Rendering successful: {result['success']}")
        if result['success']:
            print("\nExtracted content:")
            display_extracted_content(result.get('extracted_content', []))


async def run_example_with_custom_wait_function() -> None:
    """
    Example showing how to use a custom JavaScript function to determine when a page is fully loaded.
    """
    print(f"\n{'='*80}\nCustom wait function example\n{'='*80}")
    
    # Newegg product page URL
    url = "https://www.newegg.com/p/N82E16824012044"
    
    # Product title selector
    title_selector = ".product-title"
    
    # Custom wait function that checks for product title
    wait_function = """
    () => {
      const title = document.querySelector('.product-title');
      return title !== null && title.textContent.trim() !== '';
    }
    """
    
    # Create a crawler with the custom wait function
    crawler = BaseCrawler(
        js_enabled=True,
        wait_for_load=2000,
        wait_for_function=wait_function,
        content_filters=[
            ContentFilter(
                name="Product Title",
                filter_type=CSSFilter(title_selector)
            )
        ]
    )
    
    print(f"Crawling {url} with custom wait function...")
    
    result = await crawler.crawl(url)
    await crawler.close()
    
    # Display results
    print(f"Crawling successful: {result['success']}")
    if result['success']:
        print("\nExtracted content:")
        display_extracted_content(result.get('extracted_content', []))


async def main():
    """
    Run all example demonstrations.
    """
    # Demonstrate crawling with and without JavaScript
    for url in JS_HEAVY_URLS[:1]:  # Just use the first URL for brevity
        await crawl_with_and_without_js(url)
    
    # Demonstrate direct JavaScriptRenderer usage
    await demonstrate_js_renderer_directly()
    
    # Demonstrate custom wait function
    await run_example_with_custom_wait_function()


if __name__ == "__main__":
    asyncio.run(main()) 