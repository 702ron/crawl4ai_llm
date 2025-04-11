#!/usr/bin/env python
"""
Debug script for troubleshooting JavaScript rendering issues.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the parent directory to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl4ai_llm.crawler.js_renderer import JavaScriptRenderer
from crawl4ai_llm.crawler.content_filter import ContentFilter, CSSFilter

# Configure logging with more detailed information
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get the playwright logger for detailed debugging
playwright_logger = logging.getLogger("playwright")
playwright_logger.setLevel(logging.DEBUG)


async def test_js_renderer():
    """Test the JavaScript renderer directly with detailed error handling."""
    # Create a simple renderer
    print("Initializing JavaScript renderer...")
    renderer = JavaScriptRenderer(
        headless=True,
        timeout=120000,  # 2 minutes
        wait_for_load=5000,  # 5 seconds
        content_filters=[
            ContentFilter(
                name="Product Title",
                filter_type=CSSFilter("h1")
            )
        ]
    )

    try:
        # Try to initialize the browser first to check that connection
        print("Getting browser instance...")
        browser = await renderer._get_browser()
        print(f"Browser successfully initialized: {browser}")

        # Test with a simple URL first
        simple_url = "https://example.com"
        print(f"\nTesting with simple URL: {simple_url}")
        try:
            result = await renderer.render(simple_url)
            print(f"Simple URL render success: {result['success']}")
            if result['success']:
                print(f"HTML length: {len(result['html'])}")
                print(f"Extracted content: {result.get('extracted_content')}")
            else:
                print(f"Error: {result.get('error')}")
        except Exception as e:
            print(f"Error rendering simple URL: {e}")
            import traceback
            traceback.print_exc()

        # Now try with a more complex e-commerce URL
        ecommerce_url = "https://www.bestbuy.com/site/apple-iphone-14-pro-128gb-deep-purple-verizon/6504735.p"
        print(f"\nTesting with e-commerce URL: {ecommerce_url}")
        try:
            result = await renderer.render(ecommerce_url)
            print(f"E-commerce URL render success: {result['success']}")
            if result['success']:
                print(f"HTML length: {len(result['html'])}")
                print(f"Extracted content: {result.get('extracted_content')}")
            else:
                print(f"Error: {result.get('error')}")
        except Exception as e:
            print(f"Error rendering e-commerce URL: {e}")
            import traceback
            traceback.print_exc()
    finally:
        # Ensure we clean up resources
        print("Closing renderer...")
        await renderer.close()


async def test_page_navigation():
    """Test the page navigation and waiting behavior specifically."""
    print("\nTesting page navigation specifically...")
    renderer = JavaScriptRenderer(
        headless=True,
        timeout=120000
    )
    
    try:
        browser = await renderer._get_browser()
        print(f"Browser initialized: {browser}")
        
        # Create a page and navigate manually to track each step
        page = await browser.new_page()
        print("Page created")
        
        await renderer._configure_page(page)
        print("Page configured")
        
        url = "https://example.com"
        print(f"Navigating to {url}...")
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print(f"Navigation result: {response}")
            
            print("Waiting for page load...")
            await page.wait_for_load_state("networkidle", timeout=60000)
            print("Network idle reached")
            
            print("Getting page content...")
            html = await page.content()
            print(f"Got HTML content of length: {len(html)}")
            
            print("Success: All page navigation steps completed")
        except Exception as e:
            print(f"Error during page navigation: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await page.close()
            print("Page closed")
    finally:
        await renderer.close()
        print("Renderer closed")


async def main():
    """Run all tests."""
    try:
        await test_js_renderer()
        await test_page_navigation()
        print("\nAll tests completed")
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 