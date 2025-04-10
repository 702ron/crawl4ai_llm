#!/usr/bin/env python3
"""
Example script demonstrating the new filter types in ContentFilter.

This example shows how to use CSS, XPath, and Regex filters with the BaseCrawler.
"""

import asyncio
import json
from pprint import pprint

from crawl4ai_llm.crawler import BaseCrawler, ContentFilter


async def main():
    """Run the example."""
    # URL with a product page
    url = "https://www.amazon.com/dp/B01NBKTPTS"

    print(f"Crawling {url} with different filter types...\n")

    # Example 1: CSS Selector Filter
    print("=== CSS Selector Filter ===")
    css_filter = ContentFilter(
        filter_type="css",
        selector="#productTitle",  # Amazon product title
        extract_text=True,  # Extract text only
    )

    crawler_css = BaseCrawler(content_filters=[css_filter], headless=True)

    result_css = await crawler_css.crawl(url)
    print("Product title extracted with CSS selector:")
    if result_css["success"] and result_css.get("extracted_content"):
        pprint(result_css["extracted_content"])
    else:
        print("Extraction failed or no content matched")
    print()

    # Example 2: XPath Filter
    print("=== XPath Filter ===")
    xpath_filter = ContentFilter(
        filter_type="xpath",
        selector="//span[@id='productTitle']",  # Same target using XPath
        extract_text=True,
    )

    crawler_xpath = BaseCrawler(content_filters=[xpath_filter], headless=True)

    result_xpath = await crawler_xpath.crawl(url)
    print("Product title extracted with XPath:")
    if result_xpath["success"] and result_xpath.get("extracted_content"):
        pprint(result_xpath["extracted_content"])
    else:
        print("Extraction failed or no content matched")
    print()

    # Example 3: Regex Filter
    print("=== Regex Filter ===")
    regex_filter = ContentFilter(
        filter_type="regex",
        pattern=r'<span id="productTitle"[^>]*>(.*?)</span>',
    )

    crawler_regex = BaseCrawler(content_filters=[regex_filter], headless=True)

    result_regex = await crawler_regex.crawl(url)
    print("Product title extracted with Regex:")
    if result_regex["success"] and result_regex.get("extracted_content"):
        pprint(result_regex["extracted_content"])
    else:
        print("Extraction failed or no content matched")
    print()

    # Example 4: Regex with replacement
    print("=== Regex Filter with Replacement ===")
    regex_replace_filter = ContentFilter(
        filter_type="regex",
        pattern=r'<span id="productTitle"[^>]*>([^<]+)</span>',
        replacement=r"Title: \1",
    )

    crawler_regex_replace = BaseCrawler(
        content_filters=[regex_replace_filter], headless=True
    )

    result_regex_replace = await crawler_regex_replace.crawl(url)
    print("Product title with replacement:")
    if result_regex_replace["success"] and result_regex_replace.get(
        "extracted_content"
    ):
        pprint(result_regex_replace["extracted_content"])
    else:
        print("Extraction failed or no content matched")
    print()

    # Example 5: Combining Multiple Filters
    print("=== Combining Multiple Filters ===")

    # Filter for the product title using CSS
    title_filter = ContentFilter(
        filter_type="css", selector="#productTitle", extract_text=True
    )

    # Filter for the price using CSS
    price_filter = ContentFilter(
        filter_type="css", selector=".a-price .a-offscreen", extract_text=True
    )

    # Filter for images using XPath
    image_filter = ContentFilter(
        filter_type="xpath",
        selector="//img[@id='landingImage']/@src",
        extract_text=False,
    )

    # Combine all filters
    combined_crawler = BaseCrawler(
        content_filters=[title_filter, price_filter, image_filter], headless=True
    )

    result_combined = await combined_crawler.crawl(url)
    print("Multiple pieces of data extracted with different filters:")
    if result_combined["success"] and result_combined.get("extracted_content"):
        extracted = result_combined["extracted_content"]
        if len(extracted) >= 3:
            print("Title:", extracted[0])
            print("Price:", extracted[1])
            print("Image URL:", extracted[2])
        else:
            pprint(extracted)
    else:
        print("Extraction failed or no content matched")


if __name__ == "__main__":
    asyncio.run(main())
